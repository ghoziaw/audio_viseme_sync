bl_info = {
    'name': 'Audio to Viseme Sync', 'author': 'GhoziAW', 'version': (0, 2, 0),
    'blender': (5, 0, 0), 'location': '3D View > Sidebar > Viseme Sync',
    'description': 'MFA/Rhubarb audio to Diffeomorphic viseme property keyframes',
    'category': 'Animation',
}

import json
import os
import subprocess
import tempfile
import shutil
import signal
from pathlib import Path
import bpy
from bpy.props import (StringProperty, PointerProperty, CollectionProperty,
                       FloatProperty, IntProperty, BoolProperty, EnumProperty)
from .core import parse_cues, build_curves
from .discovery import is_viseme, suggest
from .mfa import POSES as MFA_POSES, CODES as MFA_CODES, parse_textgrid
from .audio import needs_conversion, resolve_ffmpeg, conversion_command, validate_wav

LABELS = [('A', 'M / B / P'), ('B', 'EE / consonants'), ('C', 'EH'),
          ('D', 'AA'), ('E', 'OH'), ('F', 'OO / W'), ('G', 'F / V'), ('H', 'L')]
ALIASES = {'A': ('M', 'MBP'), 'B': ('IY', 'EE', 'I'), 'C': ('EH', 'E'),
           'D': ('AA', 'AH', 'A'), 'E': ('OW', 'OH', 'O'),
           'F': ('UW', 'OO', 'U', 'W'), 'G': ('F', 'FV'), 'H': ('L',)}
RUNNING = set()

def path_for(name):
    return '["' + bpy.utils.escape_identifier(name) + '"]'

def fcurves(obj):
    ad = obj.animation_data
    if not ad or not ad.action or not ad.action_slot:
        return []
    curves = []
    for layer in ad.action.layers:
        for strip in layer.strips:
            if strip.type == 'KEYFRAME':
                bag = strip.channelbag(ad.action_slot)
                if bag:
                    curves.extend(list(bag.fcurves))
    return curves

def morph_metadata(obj):
    tagged, facs, labels = set(), set(), {}
    if not obj:
        return tagged, facs, labels
    owners = (obj, obj.data, getattr(obj, "daz_importer", None),
              getattr(obj.data, "daz_importer", None))
    for owner in owners:
        if owner is None:
            continue
        names = {'DazVisemes', 'DazFacs', 'DazFacsUnits', 'DazFacsExpressions', 'DazFacsDetails', 'DazFacsVisemes', 'DazFacsexpr', 'DazFacsdetails'}
        names.update(name for name in dir(owner) if name.lower().startswith('dazfacs'))
        for name in names:
            collection = getattr(owner, name, ())
            try:
                items = iter(collection)
            except TypeError:
                continue
            for item in items:
                key = getattr(item, 'name', '')
                if not key:
                    continue
                (tagged if name in ('DazVisemes', 'DazFacsVisemes') else facs).add(key)
                text = getattr(item, 'text', '')
                if isinstance(text, str) and text:
                    labels.setdefault(key, []).append(text)
    return tagged, facs, labels

def candidates(obj):
    if not obj:
        return []
    tagged, facs, labels = morph_metadata(obj)
    driven = {fc.data_path for fc in obj.animation_data.drivers} if obj.animation_data else set()
    result = []
    for key in obj.keys():
        if key in tagged or is_viseme(key, labels.get(key, ()), key in facs):
            if isinstance(obj[key], (int, float)) and not isinstance(obj[key], bool):
                if not key.lower().endswith(('(fin)', '(rst)')) and path_for(key) not in driven:
                    result.append(key)
    return sorted(result)

class DVS_Candidate(bpy.types.PropertyGroup):
    name: StringProperty()

class DVS_Map(bpy.types.PropertyGroup):
    code: StringProperty()
    target: StringProperty(name='Viseme property')
    gain: FloatProperty(name='Gain', default=1.0, min=0.0, max=1.0)

class DVS_Settings(bpy.types.PropertyGroup):
    rig: PointerProperty(name='DAZ rig', type=bpy.types.Object, poll=lambda self, ob: ob.type == 'ARMATURE')
    engine: EnumProperty(name='Engine', items=[('MFA', 'MFA (English + transcript)', ''), ('RHUBARB', 'Rhubarb', '')], default='MFA')
    mfa_maps: CollectionProperty(type=DVS_Map)
    mfa_grid: StringProperty(name='MFA long TextGrid', subtype='FILE_PATH')
    audio: StringProperty(name='Voice file', subtype='FILE_PATH')
    transcript: StringProperty(name='Transcript (optional)', subtype='FILE_PATH')
    recognizer: EnumProperty(name='Speech', items=[('pocketSphinx', 'English', ''), ('phonetic', 'Other languages', '')])
    start: IntProperty(name='Start frame', default=1)
    strength: FloatProperty(name='Strength', default=1.0, min=0.0, max=1.0)
    blend: FloatProperty(name='Blend (frames)', default=2.0, min=0.0, max=12.0)
    replace: BoolProperty(name='Replace overlapping viseme keys', default=False)
    status: StringProperty(default='Select the DAZ armature, then scan visemes.')
    maps: CollectionProperty(type=DVS_Map)
    available: CollectionProperty(type=DVS_Candidate)
    json_file: StringProperty(name='Rhubarb JSON', subtype='FILE_PATH')
    reviewed: BoolProperty(name='I checked the viseme mapping', default=False)

class DVS_Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    executable: StringProperty(name='Rhubarb executable', subtype='FILE_PATH')
    ffmpeg: StringProperty(name='FFmpeg executable', subtype='FILE_PATH')
    conda: StringProperty(name='Conda executable', subtype='FILE_PATH')
    mfa_env: StringProperty(name='MFA Conda environment', default='daz-lipsync')
    mfa_dictionary: StringProperty(name='MFA dictionary', default='english_us_arpa')
    mfa_acoustic: StringProperty(name='MFA acoustic model', default='english_us_arpa')
    def draw(self, context):
        self.layout.prop(self, 'conda')
        self.layout.prop(self, 'mfa_env')
        self.layout.prop(self, 'mfa_dictionary')
        self.layout.prop(self, 'mfa_acoustic')
        self.layout.label(text='MFA: install version 3.x and english_us_arpa models first.')
        self.layout.prop(self, 'executable')
        self.layout.prop(self, 'ffmpeg')
        self.layout.label(text='FFmpeg: select executable, or leave blank to use PATH.')
        self.layout.operator('wm.url_open', text='Download FFmpeg').url = 'https://ffmpeg.org/download.html'
        self.layout.label(text='Select rhubarb.exe on Windows. Keep its full extracted folder.')
        self.layout.operator('wm.url_open', text='Download Rhubarb').url = 'https://github.com/DanielSWolf/rhubarb-lip-sync/releases'

class DVS_OT_Scan(bpy.types.Operator):
    bl_idname = 'dvs.scan'
    bl_label = 'Scan Visemes + FACS'
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        s = context.scene.dvs
        if not s.rig and context.object and context.object.type == 'ARMATURE':
            s.rig = context.object
        keys = candidates(s.rig)
        s.available.clear()
        for key in keys:
            s.available.add().name = key
        s.maps.clear()
        for code, label in LABELS:
            item = s.maps.add()
            item.code = code
            item.target = suggest(code, keys, morph_metadata(s.rig)[2])
        s.mfa_maps.clear()
        labels = morph_metadata(s.rig)[2]
        for code, label, aliases in MFA_POSES:
            item = s.mfa_maps.add()
            item.code = code
            item.target = suggest(code, keys, labels, aliases)
        s.reviewed = False
        s.status = f'Found {len(keys)} Visemes/FACS viseme controls. Review the mappings for your engine.'
        self.report({'INFO'}, s.status)
        return {'FINISHED'}

def validate(s, engine=None, required=None):
    if not s.rig:
        raise ValueError('Select the DAZ armature first.')
    if not s.reviewed:
        raise ValueError('Review the mapping and check the confirmation box.')
    valid = set(candidates(s.rig))
    engine = engine or s.engine
    rows = s.mfa_maps if engine == 'MFA' else s.maps
    if len(rows) != (len(MFA_POSES) if engine == 'MFA' else 8):
        raise ValueError('Scan visemes first.')
    mapping = {}
    for item in rows:
        if not item.target and engine == 'MFA' and (required is None or item.code not in required):
            continue
        if item.target not in valid:
            raise ValueError(f'{item.code}: choose an imported, undriven viseme control.')
        mapping[item.code] = (item.target, item.gain)
    if not mapping:
        raise ValueError('Map at least one viseme first.')
    ad = s.rig.animation_data
    if ad and any(not track.mute for track in ad.nla_tracks):
        raise ValueError('Mute NLA tracks on this rig before generating; they can affect the result.')
    if ad and ad.action and len(ad.action.layers) > 1:
        raise ValueError('This prototype supports single-layer actions only.')
    if ad and ad.use_tweak_mode:
        raise ValueError('Exit NLA tweak mode before generating.')
    return mapping

def apply_data(context, data, engine=None):
    s = context.scene.dvs
    engine = engine or s.engine
    cues, duration = parse_cues(data, MFA_CODES if engine == 'MFA' else 'ABCDEFGHX')
    mapping = validate(s, engine, {code for a,b,code in cues if code != 'X'})
    fps = context.scene.render.fps / context.scene.render.fps_base
    curves = build_curves(cues, mapping, fps, s.start, s.blend, s.strength)
    lo = min(v[0][0] for v in curves.values())
    hi = max(v[-1][0] for v in curves.values())
    paths = {path_for(p) for p in curves}
    obj = s.rig
    old_ad = obj.animation_data
    old_action = old_ad.action if old_ad else None
    old_slot = old_ad.action_slot if old_ad else None
    for fc in fcurves(obj):
        if fc.data_path in paths:
            if fc.modifiers:
                raise ValueError('Mapped viseme curve has modifiers; remove those modifiers first.')
            if not s.replace and any(lo <= kp.co.x <= hi for kp in fc.keyframe_points):
                raise ValueError('Existing viseme keys overlap. Enable replacement or choose another start frame.')
    # Copy the action, preserving other channels and the original as a saved backup.
    ad = obj.animation_data_create()
    working = old_action.copy() if old_action else bpy.data.actions.new('DAZ Viseme Sync')
    working.name = (old_action.name if old_action else obj.name) + ' - Viseme Sync'
    values = {prop: obj[prop] for prop in curves}
    old_fake_user = old_action.use_fake_user if old_action else False
    try:
        ad.action = working
        if old_slot:
            ad.action_slot = working.slots[old_slot.identifier]
        for fc in fcurves(obj):
            if fc.data_path in paths:
                for kp in list(fc.keyframe_points):
                    if lo <= kp.co.x <= hi:
                        fc.keyframe_points.remove(kp, fast=True)
                fc.update()
        for prop, points in curves.items():
            for frame, value in points:
                obj[prop] = value
                if not obj.keyframe_insert(data_path=path_for(prop), frame=frame, group='Viseme Sync'):
                    raise RuntimeError(f'Could not key {prop}')
        for fc in fcurves(obj):
            if fc.data_path in paths:
                for kp in fc.keyframe_points:
                    if lo <= kp.co.x <= hi:
                        kp.interpolation = 'LINEAR'
                fc.update()
        if old_action:
            old_action.use_fake_user = True
    except Exception:
        ad.action = old_action
        if old_slot:
            ad.action_slot = old_slot
        if old_action:
            old_action.use_fake_user = old_fake_user
        bpy.data.actions.remove(working)
        raise
    finally:
        for prop, value in values.items():
            obj[prop] = value
        context.scene.frame_set(context.scene.frame_current, subframe=context.scene.frame_subframe)
    s.status = f'Created {len(curves)} viseme channels; {duration:.2f}s. Original action retained.'

class DVS_OT_Import(bpy.types.Operator):
    bl_idname = 'dvs.import_json'
    bl_label = 'Animate from Rhubarb JSON'
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        try:
            with open(bpy.path.abspath(context.scene.dvs.json_file), encoding='utf8') as f:
                apply_data(context, json.load(f), "RHUBARB")
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}

class DVS_OT_ImportMFA(bpy.types.Operator):
    bl_idname = 'dvs.import_mfa'
    bl_label = 'Animate from MFA TextGrid'
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        try:
            with open(bpy.path.abspath(context.scene.dvs.mfa_grid), encoding='utf-8-sig') as f:
                apply_data(context, parse_textgrid(f.read()), 'MFA')
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}

class DVS_OT_Diagnostics(bpy.types.Operator):
    bl_idname = 'dvs.diagnostics'
    bl_label = 'Create Scan Report'
    def execute(self, context):
        rig = context.scene.dvs.rig
        if not rig:
            self.report({'ERROR'}, 'Select a rig first.')
            return {'CANCELLED'}
        tagged, facs, labels = morph_metadata(rig)
        accepted = set(candidates(rig))
        lines = ['DAZ Viseme Sync 0.2.0', 'Rig: '+rig.name]
        for key in sorted(set(rig.keys()) | tagged | facs):
            if key in tagged or key in facs or is_viseme(key, labels.get(key, ())):
                lines.append(f'{key} | labels={labels.get(key, [])} | accepted={key in accepted} | on rig={key in rig}')
        text = bpy.data.texts.get('DAZ Viseme Scan Report') or bpy.data.texts.new('DAZ Viseme Scan Report')
        text.clear(); text.write('\n'.join(lines))
        self.report({'INFO'}, 'Open DAZ Viseme Scan Report in Blender Text Editor.')
        return {'FINISHED'}

class DVS_OT_Generate(bpy.types.Operator):
    bl_idname = 'dvs.generate'
    bl_label = 'Generate Lip Sync'
    bl_options = {'REGISTER', 'UNDO'}
    _process = None
    _timer = None
    _temp = None
    _log = None

    def launch(self, command):
        options = {'stdout': self._log, 'stderr': self._log, 'stdin': subprocess.DEVNULL}
        if os.name == 'nt':
            options['creationflags'] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            options['start_new_session'] = True
        self._process = subprocess.Popen(command, **options)

    def execute(self, context):
        if RUNNING:
            self.report({'ERROR'}, 'Analysis already running.')
            return {'CANCELLED'}
        try:
            s = context.scene.dvs
            validate(s)
            self._engine = s.engine
            prefs = context.preferences.addons[__package__].preferences
            audio = bpy.path.abspath(s.audio)
            compressed = needs_conversion(audio)
            convert = compressed or self._engine == 'MFA'
            ffmpeg = resolve_ffmpeg(bpy.path.abspath(prefs.ffmpeg) if prefs.ffmpeg else '') if convert else None
            transcript = ''
            if s.transcript:
                with open(bpy.path.abspath(s.transcript), encoding='utf-8-sig') as f:
                    transcript = f.read().strip()
            if self._engine == 'MFA' and not transcript:
                raise ValueError('MFA requires a nonempty UTF-8 .txt transcript matching the recording.')
            self._temp = tempfile.TemporaryDirectory(prefix='daz_viseme_')
            root = Path(self._temp.name)
            self._wav = str(root / 'voice.wav')
            if self._engine == 'MFA':
                conda = bpy.path.abspath(prefs.conda) if prefs.conda else shutil.which('conda')
                if not conda or not os.path.isfile(conda) or conda.lower().endswith(('.bat', '.cmd')):
                    raise ValueError('Select Miniforge Scripts/conda.exe in preferences (not conda.bat).')
                if not prefs.mfa_env.strip() or not prefs.mfa_dictionary.strip() or not prefs.mfa_acoustic.strip():
                    raise ValueError('Set the MFA environment, dictionary and acoustic model in preferences.')
                corpus = root / 'corpus'
                corpus.mkdir()
                self._wav = str(corpus / 'voice.wav')
                (corpus / 'voice.lab').write_text(transcript, encoding='utf8')
                output = root / 'aligned'
                self._output_dir = str(output)
                runner = str(Path(__file__).with_name('mfa_runner.py'))
                self._analysis_cmd = [conda, 'run', '--no-capture-output', '-n', prefs.mfa_env,
                    'python', runner, str(corpus), prefs.mfa_dictionary, prefs.mfa_acoustic,
                    str(output), str(root / 'mfa_work')]
            else:
                exe = bpy.path.abspath(prefs.executable)
                if not os.path.isfile(exe):
                    raise ValueError('Set the Rhubarb executable in add-on preferences.')
                self._output = str(root / 'cues.json')
                self._analysis_cmd = [exe, '-f', 'json', '--extendedShapes', 'GHX', '-r', s.recognizer, '-o', self._output]
                if transcript:
                    dialogue = root / 'dialogue.txt'
                    dialogue.write_text(transcript, encoding='utf8')
                    self._analysis_cmd.extend(['-d', str(dialogue)])
                self._analysis_cmd.append(self._wav if convert else audio)
            self._phase = 'conversion' if convert else 'analysis'
            command = conversion_command(ffmpeg, audio, self._wav) if convert else self._analysis_cmd
            self._log = open(str(root / 'log.txt'), 'w+b')
            self.launch(command)
            self._scene = context.scene
            self._rig = s.rig
            self._timer = context.window_manager.event_timer_add(0.25, window=context.window)
            RUNNING.add(self)
            context.window_manager.modal_handler_add(self)
            s.status = ('Converting to WAV...' if convert else 'Analyzing audio...') + ' Esc cancels.'
            return {'RUNNING_MODAL'}
        except Exception as exc:
            self.cleanup(context)
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}

    def cleanup(self, context):
        if self._process and self._process.poll() is None:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(self._process.pid), '/T', '/F'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NO_WINDOW, timeout=5)
            else:
                try:
                    os.killpg(self._process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            self._process.wait(timeout=5)
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        if self._log:
            self._log.close()
            self._log = None
        if self._temp:
            self._temp.cleanup()
            self._temp = None
        RUNNING.discard(self)

    def save_log(self, message):
        self._log.seek(0)
        details = self._log.read().decode('utf8', errors='replace')
        text = bpy.data.texts.get('DAZ Lip Sync Log') or bpy.data.texts.new('DAZ Lip Sync Log')
        text.clear(); text.write(message + '\n' + details)

    def modal(self, context, event):
        if event.type == 'ESC' or context.scene != self._scene or context.scene.dvs.rig != self._rig:
            self._scene.dvs.status = 'Cancelled; no animation changed.'
            self.cleanup(context)
            return {'CANCELLED'}
        if event.type != 'TIMER' or self._process.poll() is None:
            return {'PASS_THROUGH'}
        try:
            if self._process.returncode:
                name = 'FFmpeg' if self._phase == 'conversion' else self._engine
                raise RuntimeError(name + ' failed. See DAZ Lip Sync Log in the Text Editor.')
            if self._phase == 'conversion':
                validate_wav(self._wav)
                self.launch(self._analysis_cmd)
                self._phase = 'analysis'
                context.scene.dvs.status = f'{self._engine}: analyzing audio... Esc cancels.'
                return {'RUNNING_MODAL'}
            if self._engine == 'MFA':
                files = list(Path(self._output_dir).rglob('*.TextGrid'))
                if len(files) != 1:
                    raise RuntimeError('MFA did not produce exactly one TextGrid. Check the transcript, dictionary and log.')
                data = parse_textgrid(files[0].read_text(encoding='utf-8-sig'))
            else:
                with open(self._output, encoding='utf8') as f:
                    data = json.load(f)
            apply_data(context, data, self._engine)
            self.save_log('Completed successfully.')
            self.report({'INFO'}, context.scene.dvs.status)
            result = {'FINISHED'}
        except Exception as exc:
            context.scene.dvs.status = str(exc)[:250]
            self.save_log(str(exc))
            self.report({'ERROR'}, str(exc))
            result = {'CANCELLED'}
        self.cleanup(context)
        return result

    def cancel(self, context):
        self.cleanup(context)

class DVS_PT_Panel(bpy.types.Panel):
    bl_label = 'DAZ Viseme Sync'
    bl_idname = 'DVS_PT_panel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Viseme Sync'
    def draw(self, context):
        layout = self.layout
        s = context.scene.dvs
        layout.label(text=s.status[:80])
        body = layout.column()
        body.enabled = not bool(RUNNING)
        body.prop(s, 'engine')
        body.prop(s, 'rig')
        body.operator('dvs.scan')
        body.operator('dvs.diagnostics')
        rows = s.mfa_maps if s.engine == 'MFA' else s.maps
        titles = {code: label for code, label, aliases in MFA_POSES} if s.engine == 'MFA' else dict(LABELS)
        if rows:
            box = body.box()
            for item in rows:
                label = titles.get(item.code, item.code)
                row = box.row(align=True)
                row.label(text=f'{item.code}: {label}')
                row.prop_search(item, 'target', s, 'available', text='')
                row.prop(item, 'gain', text='')
            box.label(text='X (silence): all mapped visemes = 0')
            box.prop(s, 'reviewed')
        body.prop(s, 'audio')
        if s.engine == 'RHUBARB':
            body.prop(s, 'recognizer')
        body.prop(s, 'transcript', text='Transcript (required)' if s.engine == 'MFA' else 'Transcript (optional)')
        body.prop(s, 'start')
        body.prop(s, 'strength')
        body.prop(s, 'blend')
        body.prop(s, 'replace')
        body.operator('dvs.generate', icon='PLAY')
        box = body.box()
        box.label(text='Or use previously analyzed audio:')
        if s.engine == 'MFA':
            box.prop(s, 'mfa_grid')
            box.operator('dvs.import_mfa')
        else:
            box.prop(s, 'json_file')
            box.operator('dvs.import_json')

CLASSES = (DVS_Candidate, DVS_Map, DVS_Settings, DVS_Preferences,
           DVS_OT_Scan, DVS_OT_Import, DVS_OT_ImportMFA, DVS_OT_Diagnostics, DVS_OT_Generate, DVS_PT_Panel)

def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dvs = PointerProperty(type=DVS_Settings)

def unregister():
    for op in list(RUNNING):
        op.cleanup(bpy.context)
    del bpy.types.Scene.dvs
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    register()
