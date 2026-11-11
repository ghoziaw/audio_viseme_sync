# Audio to Viseme Sync

**Turn recorded dialogue into editable DAZ viseme animation in Blender.**

Audio to Viseme Sync connects Montreal Forced Aligner (MFA) or Rhubarb Lip Sync
to the numeric viseme controls of a Diffeomorphic-imported DAZ armature. It
creates editable keyframes while leaving the controls' facial drivers intact.

**Author:** GhoziAW · **Version:** 0.2.0 · **Blender target:** 5.0

## Start here

- **[Complete installation and usage tutorial](docs/TUTORIAL.md)** — dependencies,
  rig setup, both engines, mapping reference, settings, playback, and troubleshooting.
- **[Installable add-on ZIP](downloads/audio_viseme_sync-0.2.0.zip)** — open the
  file and use GitHub's download button; do not save the HTML preview page.
- The Blender preferences entry is **Audio to Viseme Sync**. The sidebar tab is
  **Viseme Sync**, and the panel title is **DAZ Viseme Sync**.

## Features at a glance

| Feature | What it provides |
|---|---|
| Two analysis engines | English transcript-based MFA or Rhubarb recognition |
| Editable mapping | Sixteen MFA poses or eight Rhubarb poses, each with gain |
| Reuse analysis | Import long-format MFA TextGrid or Rhubarb JSON |
| Audio formats | WAV, OGG, MP3, M4A; FFmpeg conversion when required |
| Animation tuning | Start frame, strength, bounded linear blending |
| Existing-action protection | Copies the active action; retains the original |
| Diagnostics | Scan report and processing log inside Blender |

The adapter runs external tools locally; it implements no cloud analysis API.
Programs, models, and character assets are not bundled. This is a prototype for
armature-object viseme properties, not a universal facial-rig or direct shape-key
animation system.

## Technical overview

Target: Blender 5.0 and Diffeomorphic DAZ Importer 5.0.
Recorded audio -> MFA or Rhubarb -> editable viseme-control keyframes.
Only mapped viseme controls are keyed. No separate brow, eye, jaw or tongue
animation is generated. A viseme's own facial-bone/shape-key drivers stay intact.

## Changes in 0.2.0

- Recognizes short FACS display labels: Vis AA, Vis L, etc., as well as internal
  names such as facs_ctrl_VisAA. Previous versions missed the short Vis prefix.
- Reads morph metadata on the rig/data directly AND inside their daz_importer
  property groups. Includes DazFacs, DazFacsVisemes and other DazFacs* categories.
- Keys the raw numeric property on the armature object, as the Runtime slider
  does. It does not require a directly corresponding mesh shape key.
- New MFA engine with 16 editable mouth-pose mappings, English ARPABET phone
  timing, stress-marker handling, silence and simple two-part diphthongs.
- Retains Rhubarb and automatic MP3/M4A conversion.
- Scan report and processing log are accessible in Blender's Text Editor.

The Diffeomorphic source inspected confirms that morph category items use name
for the rig-property key and text for the display label, and that newer metadata
can be nested under daz_importer. This release supports both layouts without
importing Diffeomorphic's Python modules. No user character file was available.

## Update/install

Save your .blend. In Edit > Preferences > Add-ons > menu > Install from Disk,
select audio_viseme_sync-0.2.0.zip and enable the add-on. Restart Blender after
upgrading so its modules reload. This ZIP is a legacy Python add-on.

Open the 3D View's N sidebar > Viseme Sync. Choose the engine, select the rig,
and click Scan Visemes + FACS again. Review the mappings and check the confirmation
box. Scanning regenerates BOTH engines' mappings, so reapply custom choices.

## MFA setup for Windows (one time)

MFA is a separate application with acoustic models, not another Blender add-on.
This adapter targets MFA 3.x and the English US ARPABET models. MFA 4.x changes
the CLI; the runner rejects it rather than attempting an incompatible command.

1. Install Miniforge using the link from MFA's official installation guide:
   https://montreal-forced-aligner.readthedocs.io/en/latest/installation.html
2. Open Miniforge Prompt and run:

   conda create -n daz-lipsync -c conda-forge "montreal-forced-aligner>=3.3,<4" -y
   conda activate daz-lipsync
   mfa model download acoustic english_us_arpa
   mfa model download dictionary english_us_arpa
   mfa --version

3. In the Blender add-on preferences set:
   - Conda executable: Miniforge's Scripts/conda.exe, NOT conda.bat.
     Example location: C:/Users/YOUR_NAME/miniforge3/Scripts/conda.exe
   - MFA Conda environment: daz-lipsync
   - MFA dictionary: english_us_arpa
   - MFA acoustic model: english_us_arpa
   - FFmpeg executable: your existing ffmpeg.exe path.

MFA's dependencies run inside that Conda environment, not Blender Python.
No GPU-specific setup is required by this adapter. Download the models once
before using Generate. A compatible custom ARPABET dictionary/model may be
specified by name or absolute path. IPA model sets are not supported by this
phone mapper; unrecognized phones generate an error.

On macOS/Linux, use the installed conda executable instead of conda.exe. The
Windows workflow is the primary target, and actual platform integration has not
been verified in the build workspace.

## Generate with MFA

1. Choose MFA (English + transcript).
2. Select your rig, scan, and review the MFA mapping rows. These are approximate
   phoneme-to-mouth-pose choices and can be changed to your preferred Vis controls.
   Where a specific pose is absent, the scanner may suggest a broader fallback.
   Ambiguous choices stay blank. All poses USED by the resulting alignment must
   be mapped; unused blank rows are allowed. It stops before changing animation
   if a required pose is missing.
3. Choose WAV, OGG, MP3 or M4A audio.
4. Supply a plain UTF-8 .txt transcript containing exactly the spoken dialogue,
   with no timestamps. Unlike Rhubarb, MFA requires this transcript. Correct
   omitted/repeated words and write numbers as they are spoken.
5. Choose start frame, strength and blending, then Generate Lip Sync.
6. The add-on normalizes audio to mono 16-bit PCM 16 kHz WAV, creates a temporary
   audio/transcript pair, runs MFA, reads the phone tier from its TextGrid, and
   inserts the mapped keyframes. Wait for completion; Esc cancels.
7. Add the original audio manually to the Video Sequencer at the same start frame
   for playback. The add-on does not add audio or change the scene frame range.

Use one speaker per recording. Start with a short clean sentence. MFA alignment
can fail or misalign unfamiliar names and dictionary-missing words. A 'spn' error
usually needs a pronunciation added to a custom ARPABET dictionary; a matching
transcript alone cannot supply that pronunciation. Examine DAZ Lip Sync Log.
MFA alignment timing does not guarantee natural facial animation; mapping,
strength, blending and manual polish still matter. AY/AW/EY/OY use an approximate
60/40 split into two mouth poses, not separately measured internal boundaries.

Previously exported MFA long-format TextGrid files can be imported using
Animate from MFA TextGrid. This bypasses MFA installation/execution and does not
need the audio or transcript fields. It requires exactly one phones tier and
English ARPABET symbols. Short TextGrid/IPA files are rejected.

## Rhubarb and conversion

Choose Rhubarb to retain the existing eight-shape workflow. Set the executable
in preferences after extracting the full package:
https://github.com/DanielSWolf/rhubarb-lip-sync/releases

Transcript is optional in Rhubarb mode. Use English for English dialogue and the
phonetic option for other languages. Existing Rhubarb JSON import still works.

FFmpeg: https://ffmpeg.org/download.html
Select ffmpeg.exe in preferences, or leave blank when ffmpeg is on PATH.
Rhubarb only requires conversion for MP3/M4A. MFA normalizes all four formats.
Conversion uses the first audio stream without modifying the source recording.
Temporary files are removed after completion/cancellation/error. Encrypted or
corrupt recordings may fail. No external programs/models are bundled in the ZIP.

## FACS scanning and diagnostics

The scan uses metadata labels AND internal property names. Vis AA/Vis L controls
may drive combinations of bones and other morphs; the add-on animates only their
input sliders. It excludes driven final properties and does not add every FACS
unit simply because it belongs to FACS. Non-viseme brow, eye, jaw-open and smile
controls are not inferred as mouth poses.

If controls are missing, choose Create Scan Report, open Blender's Text Editor,
and select DAZ Viseme Scan Report. Copy its text for troubleshooting. It lists
internal names, labels and whether each recognized/category control was accepted.
This report does not change the rig. For processing errors, select DAZ Lip Sync
Log in the Text Editor; it contains the most recent processing output.

## Existing animation and limitations

- A copy of the active action becomes active for generated keys. The original
  action is retained with a fake user as a backup. Other channels are preserved
  in the copy; other objects using the original are not changed.
- Overlapping mapped keys are refused unless Replace overlapping viseme keys is
  enabled. Replacement includes short neutral padding before/after the audio.
  Mapped keys outside the range are retained, but interpolation at range edges
  may change as new keys are inserted.
- Silence zeros mapped visemes. Unmapped visemes/expressions remain untouched and
  can still influence the mouth. Morph drivers must be enabled.
- NLA tracks must be muted; NLA tweak mode, multiple action layers, and modifiers
  on mapped curves are rejected. Only armature-object raw custom properties are
  supported, not direct mesh shape keys or pose-bone property animation.
- Scene FPS and FPS base determine timing. Audio stretching is not supported.
- Keep the current scene/rig during processing. Esc cancels the process tree.

## Validation and development

Run the reproducible Blender-independent checks and rebuild the installable ZIP:

```sh
python tools/verify.py
python tools/package.py
```

The supplied folder did not include the eighteen historical tests mentioned in
its original README. That historical claim is not treated as a reproducible
result. The included smoke checks validate source syntax, cue validation,
curve bounds, discovery, ARPABET conversion, and audio command construction.
They do not run Blender, Conda/MFA alignment, or Rhubarb recognition. Actual
character compatibility and end-to-end lip-sync quality remain unverified.

The original six Python modules are preserved; documentation and packaging
support do not change their runtime behavior.

## License

No license file was supplied with this folder. A license has not been chosen on
the author's behalf. Public repository visibility alone does not specify reuse
permissions. External tools and models have their own licenses.

## Technical sources

- Diffeomorphic property metadata and rig keys:
  https://github.com/Diffeomorphic/import_daz/blob/master/morphing.py
- Legacy/nested metadata access:
  https://github.com/Diffeomorphic/import_daz/blob/master/utils.py
- MFA installation:
  https://montreal-forced-aligner.readthedocs.io/en/latest/installation.html
- MFA align CLI and long TextGrid output:
  https://montreal-forced-aligner.readthedocs.io/en/latest/user_guide/workflows/alignment.html
- English US ARPA model:
  https://mfa-models.readthedocs.io/en/latest/acoustic/English/English%20(US)%20ARPA%20acoustic%20model%20v3_0_0.html
