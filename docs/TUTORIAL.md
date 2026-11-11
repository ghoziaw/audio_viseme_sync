# Audio to Viseme Sync: installation and first animation

[Back to README](../README.md)

This guide describes version 0.2.0 as implemented in the supplied source. Blender 5.0 and Diffeomorphic DAZ Importer 5.0 are the intended targets, not a claim that every character or later Blender version has been tested. Windows is the primary documented setup; macOS/Linux integration has not been verified here.

## Contents

1. [Choose an engine](#1-choose-an-engine)
2. [Install the add-on](#2-install-the-add-on)
3. [Install external tools](#3-install-external-tools)
4. [Prepare your character](#4-prepare-your-character), including [your own custom visemes](#use-your-own-visemes-without-daz)
5. [Generate with MFA](#5-generate-with-mfa)
6. [Generate with Rhubarb](#6-generate-with-rhubarb)
7. [Import existing analysis](#7-import-existing-analysis)
8. [Review and refine](#8-review-and-refine)
9. [Mapping reference](#mapping-reference)
10. [Settings reference](#settings-reference)
11. [Troubleshooting](#troubleshooting)
12. [Restore the previous action](#restore-the-previous-action)

## 1. Choose an engine

A **viseme** is a mouth pose representing one or more speech sounds. This add-on turns timed sound labels into animation of the corresponding imported or user-created facial controls. It does not create missing visemes or repair a character's drivers.

**Choose MFA** when you have an accurate English transcript and want the sixteen-pose workflow. MFA aligns the written dialogue to the recording; the add-on maps its English ARPABET phones to mouth poses.

**Choose Rhubarb** when you prefer a simpler eight-pose workflow or want recognition without a required transcript. The panel offers English and phonetic recognition options. Neither engine guarantees natural facial acting without mapping review and animation cleanup.

**Choose an import workflow** if you already have compatible JSON or TextGrid analysis. Importing bypasses the external programs entirely.

## 2. Install the add-on

1. Save a backup of your `.blend` file.
2. Download `downloads/audio_viseme_sync-0.2.0.zip` from this repository using GitHub's file-download button.
3. Open Blender's **Edit → Preferences → Add-ons**.
4. Open the add-ons menu and select **Install from Disk**. Select the ZIP.
5. Enable **Audio to Viseme Sync** and expand its preferences.
6. In the 3D Viewport, press `N` and select **Viseme Sync**. Its panel heading is **DAZ Viseme Sync**.

This is a legacy add-on. It has no `blender_manifest.toml`. The installable ZIP contains:

```text
audio_viseme_sync/
  __init__.py
  audio.py
  core.py
  discovery.py
  mfa.py
  mfa_runner.py
  README.md
  LICENSE
  docs/
    TUTORIAL.md
```

Do not install a single Python file or a ZIP containing an extra nested `audio_viseme_sync` folder. After an upgrade, restart Blender and scan the rig again. Scanning resets both engines' mappings, including custom choices and gains.

To build the ZIP yourself, run `python tools/package.py` from the repository directory. The script uses an explicit file list and excludes caches and Git metadata.

## 3. Install external tools

Skip this section if you only import previously analyzed files.

### FFmpeg

Obtain FFmpeg from its official download page. Extract/install it separately and select the actual `ffmpeg.exe` file in **FFmpeg executable**. Alternatively, leave that preference blank if `ffmpeg` is on the PATH visible to Blender. Restart Blender after changing PATH.

FFmpeg is needed for:

- **Every MFA generation**, including WAV and OGG input.
- **MP3/M4A input with Rhubarb**. WAV/OGG is passed directly to Rhubarb.

Conversion selects the first audio stream and creates mono, 16-bit PCM, 16 kHz WAV in a temporary directory. The original recording is not overwritten. The current missing-FFmpeg error mentions MP3/M4A even when MFA requires FFmpeg for a WAV file.

### MFA: one-time Windows setup

The runner explicitly accepts **MFA 3.x only**. Follow the version constraint below rather than installing an unrestricted latest version.

1. Install Miniforge using MFA's official installation documentation.
2. Open Miniforge Prompt and run:

```sh
conda create -n daz-lipsync -c conda-forge "montreal-forced-aligner>=3.3,<4" -y
conda activate daz-lipsync
mfa model download acoustic english_us_arpa
mfa model download dictionary english_us_arpa
mfa --version
```

3. Confirm the reported version starts with `3.`.
4. In the add-on preferences set:

| Preference | Value |
|---|---|
| Conda executable | Your Miniforge `Scripts/conda.exe` |
| MFA Conda environment | `daz-lipsync` |
| MFA dictionary | `english_us_arpa` |
| MFA acoustic model | `english_us_arpa` |
| FFmpeg executable | Your `ffmpeg.exe`, or blank if available on PATH |

Example Conda location, to be adapted to your installation:

```text
C:/Users/YOUR_NAME/miniforge3/Scripts/conda.exe
```

Do not choose `conda.bat`, `conda.cmd`, a directory, or Blender's Python executable. The runner executes in the named external Conda environment; installing MFA into Blender's Python is not this workflow.

Custom model/dictionary names or paths may be used, but they must produce supported English ARPABET labels. IPA models are not supported. Finish model downloads before generating animation.

### Rhubarb: one-time setup

1. Download the appropriate Rhubarb release from its official repository.
2. Extract the **entire distribution**, retaining its supporting files.
3. In add-on preferences, choose the actual executable under **Rhubarb executable** (`rhubarb.exe` on Windows).
4. Configure FFmpeg if you intend to use MP3/M4A.

The add-on calls Rhubarb with JSON output and extended shapes `GHX`.

## 4. Prepare your character

1. Prepare your character: either use your Diffeomorphic DAZ workflow or follow [Use your own visemes without DAZ](#use-your-own-visemes-without-daz) below.
2. Ensure its required mouth poses are exposed through imported or custom armature-object viseme controls.
3. Move a viseme slider manually and confirm the face responds, then return it to neutral. If the slider does not work manually, generating keyframes will not fix it.
4. Select the character's **armature**, not its face mesh.
5. In **Viseme Sync**, choose the armature in **DAZ rig**. When no rig is set, scanning can use the active armature.
6. Set your final scene frame rate before generation.
7. Mute the rig's NLA tracks and exit NLA tweak mode. Use a single-layer active action, without modifiers on the mapped viseme curves.
8. Select the intended engine and click **Scan Visemes + FACS**.
9. Review every mapping. Automatic suggestions are starting points, not confirmation that the pose looks right on your character.
10. Check **I checked the viseme mapping**.

The scanner considers numeric custom properties on the armature object, together with supported Diffeomorphic metadata and labels. It excludes booleans, directly driven properties, final/reset properties, and unrelated FACS controls. Visemes do not need a matching mesh shape-key name.

An ambiguous suggestion is intentionally left blank. Choose the appropriate control manually. If necessary, map multiple sound codes to the same broader mouth pose. Scanning again clears both engines' mappings and resets the confirmation checkbox.

### Use your own visemes without DAZ

**You can use mouth poses you made yourself. A DAZ character and Diffeomorphic are not required for this workflow.** The current add-on needs an armature-object property interface to those poses; it cannot directly select arbitrary mesh shape keys or pose-bone controls.

#### A. Expose your poses as armature controls

1. Prepare your mouth poses using shape keys, bones, or your existing facial rig.
2. On the **armature object**, add one numeric custom property per mouth-pose control. Use float properties, with a neutral value of `0.0` and a useful working range of `0.0`–`1.0`. Put these on the object, **not** the armature data block, a pose bone, or the face mesh.
3. Name them with the `viseme_` prefix. Examples: `viseme_AA`, `viseme_M`, `viseme_OH`, or `viseme_MyMouthPose`. The scanner accepts the `viseme` prefix even when the remaining name is your own label. Familiar sound labels may get automatic suggestions; custom labels require manual mapping.
4. Connect each property to the corresponding facial pose using drivers. The armature property must be the **input**, not a driven output. For a shape-key example, a driver on the shape key's Value can use a Single Property variable targeting your armature object with data path `["viseme_AA"]`; using that variable as the driver expression makes the shape key follow the slider. Preserve existing rig logic rather than overwriting drivers blindly.
5. Move each custom slider manually and confirm it produces the intended pose. Return it to zero before generating.

The relationship should be:

```text
Add-on keyframes → armature object custom property → your drivers → mouth pose
```

It should **not** be a driver feeding into the property that the add-on must key: directly driven input properties are excluded. Properties ending in `(fin)` or `(rst)` and boolean properties are also excluded.

For Blender's driver configuration concepts, see the [official Drivers Panel reference](https://docs.blender.org/manual/en/2.80/animation/drivers/drivers_panel.html) (the linked reference describes Single Property variables and custom-property paths; UI layout can differ in newer versions).

#### B. Map the controls manually

1. Select your armature in **DAZ rig**. That is the current UI label; the selector accepts armature objects, not only DAZ rigs.
2. Choose your engine and click **Scan Visemes + FACS**. The button also scans recognized custom-property names without DAZ metadata.
3. In each mapping row, choose the custom property that produces the desired mouth pose. You are not required to accept the automatic suggestion or use a DAZ naming convention beyond the scanner requirements above.
4. Adjust each row's Gain. Multiple rows may target the same property if you use a simplified pose set.
5. For Rhubarb, fill all eight rows. For MFA, all poses used in the alignment must be mapped; unused rows can remain blank, with at least one valid mapping overall.
6. Check **I checked the viseme mapping**, then generate or import analysis as usual.

Example: Rhubarb `A` can map to your `viseme_LipsClosed`, `D` to `viseme_WideOpen`, and `E` to `viseme_Round`. These names describe your artwork, not fixed built-in assets. Create the corresponding controls and connections yourself first.

**Important limits:** manually choosing a target does not bypass validation. An arbitrary property called `mouthOpen` will not be accepted unless recognized through supported metadata; expose it through a scanner-compatible input such as `viseme_MouthOpen`. Merely renaming a mesh shape key is not sufficient. Creating a custom property alone does not make the face move. When renaming existing controls, update any driver paths that refer to them. Rescanning resets both engines' mappings and gains.

This documents the existing property-based mechanism; it is not a new universal-rig feature or a claim of end-to-end testing with every custom rig.

## 5. Generate with MFA

### Prepare a first recording

Use a short, clean, single-speaker sentence. Create a UTF-8 plain-text transcript containing exactly the spoken words, without timestamps or speaker labels. For example, you could record:

```text
Please bring my blue bag home.
```

This is an illustrative sentence, not a bundled recording or test result. Include repetitions that are actually spoken; write numbers as pronounced. Background speech, music, omitted words, and unfamiliar pronunciations can degrade alignment.

### Generate the animation

1. Choose **MFA (English + transcript)**.
2. Select and scan the rig, review its mappings, and check the confirmation box.
3. Choose the recording under **Voice file**.
4. Choose the transcript under **Transcript (required)**.
5. Set **Start frame** to the frame where the audio should begin.
6. For an initial trial, use **Strength: 1.0**, **Blend (frames): 2.0**, and leave replacement disabled. These are the implemented defaults, not universal artistic settings.
7. Click **Generate Lip Sync**.
8. Wait while FFmpeg converts the audio and MFA analyzes it. Do not switch scenes or rigs. `Esc` cancels the process.
9. Inspect the result after the completion message.

The add-on creates a temporary audio/transcript pair, invokes MFA through Conda, reads its single output TextGrid, and builds keyframes. The original action is copied before animation is applied.

All poses used by the alignment must be mapped. Unused MFA rows may remain blank, but at least one valid mapping is required. If analysis reveals a required unmapped pose, application fails before changing animation. Nonempty mappings must always reference valid controls.

MFA diphthongs `AY`, `AW`, `EY`, and `OY` use an approximate 60/40 split into two poses. Those internal transitions are not separately measured by the add-on.

## 6. Generate with Rhubarb

1. Choose **Rhubarb**.
2. Select and scan the rig; review all eight `A`–`H` rows.
3. Fill every row with a valid control. Unlike MFA, all eight Rhubarb mappings are required, even if a particular recording does not use all of them.
4. Check **I checked the viseme mapping**.
5. Select a **Voice file**.
6. Under **Speech**, choose **English** for the `pocketSphinx` recognizer or **Other languages** for the `phonetic` recognizer.
7. Optionally provide a UTF-8 transcript. Leave its path blank if you do not want to use one.
8. Set start frame, strength, and blending. Leave replacement off for the first run.
9. Click **Generate Lip Sync** and wait for completion.

MP3/M4A is converted before analysis. WAV/OGG is sent directly to Rhubarb, so its decoder must be able to read the file. If a WAV variant fails, try a standard PCM WAV.

## 7. Import existing analysis

### Rhubarb JSON

Choose **Rhubarb**, review/confirm the mapping, then select **Rhubarb JSON** in the lower panel and click **Animate from Rhubarb JSON**.

The file must contain nonempty, ordered `mouthCues`, each with `start`, `end`, and `value`, with codes `A`–`H` or `X`. Optional `metadata.duration` must be consistent with the cues. Overlaps, invalid codes/times, and durations over one hour are rejected. Cue gaps become silence.

No Rhubarb executable, FFmpeg, voice-file selection, or transcript is needed for this import operation.

### MFA TextGrid

Choose **MFA**, review/confirm the mapping, select **MFA long TextGrid**, and click **Animate from MFA TextGrid**.

Requirements:

- Long-format TextGrid with a valid `xmax` duration.
- Exactly one interval tier named `phones` or ending in ` - phones`.
- Supported English ARPABET phone labels.
- Ordered, non-overlapping intervals and a duration no longer than one hour.

Short TextGrid, multi-speaker phone tiers, unsupported phones, and IPA output are rejected. Stress digits and supported word-position suffixes are handled. No Conda, MFA, FFmpeg, audio, or transcript is needed for this import operation.

The generated run's temporary analysis files are cleaned up, so this UI is for files you saved/exported separately; it is not an export button for the last generation.

## 8. Review and refine

The add-on does not insert audio or set the scene's playback range.

1. Add the original audio as a sound strip in Blender's Video Sequencer.
2. Align the strip's start to the add-on's **Start frame**.
3. Extend the scene playback range to cover the recording if necessary.
4. Play and scrub the animation while watching the face.
5. In the Dope Sheet or Graph Editor, inspect the rig's active action and **Viseme Sync** channels.

If mouth shapes are wrong, correct the mappings before tuning blend values. If the motion is too strong, reduce overall Strength or the Gain of specific rows. Excessive smoothing can soften important closures; too little blending can look abrupt.

Generated timing uses `scene.render.fps / scene.render.fps_base`. Changing FPS afterward changes the relationship between the existing keys and audio playback; regenerate with the intended FPS. Time-stretched audio is not accounted for.

Silence zeros **mapped** properties, not every facial property on the rig. Unmapped mouth controls or expressions may prevent a neutral resting pose.

Before regenerating into the same time range, either choose a different start frame or enable **Replace overlapping viseme keys** deliberately. The affected interval includes short neutral padding. Existing keys outside that interval remain, but interpolation near its edges may change.

## Mapping reference

### MFA poses

These are the implemented phone groups, not promises about the appearance of a specific DAZ slider.

| Pose code | Phone group / use | Suggested fallback family |
|---|---|---|
| AA | AA, AH | AA / AH / A |
| EH | AE, EH | EH / E / AA |
| IH | IH; broad HH fallback | IH / IY / I |
| IY | IY, Y | IY / EE / I |
| OW | AO, OW | OW / OH / O |
| UW | UH, UW | UW / OO / U |
| M | M, B, P | M / MBP |
| F | F, V | F / FV / FF |
| L | L | L |
| TH | TH, DH | TH / DH / L |
| S | S, Z | S / SZ / IY / I |
| SH | SH, ZH, CH, JH | SH / CH / S / IY |
| K | K, G, NG | K / KG / IH / IY |
| T | T, D, N | T / DD / D / N / L |
| ER | R, ER | ER / R / OW |
| W | W | W / UW / U |

Diphthongs: `AY → AA, IY`; `AW → AA, UW`; `EY → EH, IY`; `OY → OW, IY`.

Empty labels, `sil`, `sp`, and `<eps>` are treated as silence. `spn` is not silently ignored; it raises an unknown-phone error.

### Rhubarb poses

| Code | Panel label | Mapping family |
|---|---|---|
| A | M / B / P | Closed lips |
| B | EE / consonants | IY / EE / I |
| C | EH | EH / E |
| D | AA | AA / AH / A |
| E | OH | OW / OH / O |
| F | OO / W | UW / OO / U / W |
| G | F / V | F / FV |
| H | L | L |
| X | Silence | All mapped controls zero; no separate mapping row |

Codes are engine-specific. In particular, Rhubarb `F` is not MFA `F`: Rhubarb's `F` row represents OO/W, while MFA's `F` row represents F/V.

## Settings reference

| Control | Default / range | Meaning |
|---|---|---|
| Engine | MFA | Chooses mapping and analysis/import workflow |
| DAZ rig | Unset | Armature object whose properties will be keyed |
| Gain | 1.0; 0–1 | Per-row amplitude multiplier |
| Start frame | 1 | Frame corresponding to audio time zero |
| Strength | 1.0; 0–1 | Global amplitude multiplier |
| Blend (frames) | 2.0; 0–12 | Transition width, automatically narrowed around short cues |
| Replace overlapping viseme keys | Off | Allows replacement on mapped channels inside the generated interval |
| I checked the viseme mapping | Off after scan | Required manual confirmation |

Peak value is Strength × Gain. Shared property mappings are not added together. Adjacent cues producing the same property values are merged. Zero blending uses a near-instant linear transition, not constant-interpolation keys. Neutral padding extends by at least one frame at each end.

## Troubleshooting

| Symptom / message | What to check |
|---|---|
| Sidebar tab missing | Enable Audio to Viseme Sync, use a 3D Viewport, and open the `N` sidebar. Check ZIP nesting and restart after upgrades. |
| No viseme candidates | Select the armature, import the needed controls, verify sliders work, and generate a scan report. Mesh-only or pose-bone properties are not supported. |
| Blank auto-mapping | Several controls may match, or no recognized alias is available. Choose manually after testing the controls. |
| Mapping confirmation error | Check the confirmation box after reviewing the active engine's rows. Rescanning clears it. |
| Choose an imported, undriven control | A target is missing, stale, driven, or unsupported. Scan and select a valid raw armature property. |
| MFA requires a nonempty transcript | Select a UTF-8 text file containing the spoken dialogue. |
| Conda executable error | Choose the real executable, not `conda.bat` or `conda.cmd`; check the named environment exists. |
| MFA version error | The adapter accepts major version 3 only. Check `mfa --version` inside the selected environment. |
| `spn` / unrecognized phones | Check model family and dictionary pronunciation coverage. Correct transcript errors or supply a compatible custom ARPABET dictionary. |
| Expected exactly one phones tier | Export a single-speaker long TextGrid with a supported tier name. |
| FFmpeg error on WAV with MFA | MFA always normalizes audio. Configure FFmpeg even for WAV input. |
| Audio format rejected | Only WAV, OGG, MP3, and M4A extensions are accepted. Convert other formats externally. |
| Existing keys overlap | Use another start frame or explicitly allow replacement after saving a backup. |
| NLA/action/modifier error | Mute NLA tracks, exit tweak mode, use a single-layer action, and remove modifiers from mapped curves. |
| Mouth still moves during silence | Check unmapped expression/viseme channels; only mapped controls are zeroed. |
| Audio and animation drift | Check FPS/FPS base, strip start frame, recording used, and any audio stretching. |
| Analysis succeeds but mouth looks wrong | Test the selected sliders manually; inspect mappings, driver state, gains, and overlapping facial animation. |

### Collect diagnostics

For discovery problems:

1. Select the target rig in the panel.
2. Click **Create Scan Report**.
3. Switch an editor to **Text Editor**.
4. Select **DAZ Viseme Scan Report** from the text datablock list.

The report lists property names, labels, acceptance, and whether the property exists on the rig. It does not modify the rig.

For processing failures, open **DAZ Lip Sync Log** in the Text Editor. It contains output from the latest completed or failed processing phase. Errors occurring before process launch may only appear as operator errors; JSON/TextGrid imports do not create a subprocess log. Copy useful logs before another run overwrites them, and remove private local paths before posting publicly.

Include Blender version, add-on version, selected engine, external-tool versions, exact error, and a sanitized report when asking for help. Do not upload proprietary DAZ assets or private recordings without permission.

## Restore the previous action

On successful application, a copied action becomes active with a name ending in ` - Viseme Sync` (Blender may append a uniqueness suffix). The original action gets a fake user so it is retained when saving.

To revert, select the armature and choose the original action in the Dope Sheet's Action Editor. Verify the action/slot assignment and playback. The code tries to restore the previous action if application fails, but a separately saved `.blend` remains the safest recovery option.

Other objects sharing the original action are not deliberately reassigned to the new copy. Repeated generation creates more action copies; review unused actions manually rather than deleting backups blindly.

## Official external resources

These links are references for installing external dependencies, not evidence of an end-to-end test of this add-on.

- Blender manual: https://docs.blender.org/manual/en/latest/editors/preferences/addons.html
- Diffeomorphic DAZ Importer: https://github.com/Diffeomorphic/import_daz
- MFA installation: https://montreal-forced-aligner.readthedocs.io/en/latest/installation.html
- MFA alignment workflow: https://montreal-forced-aligner.readthedocs.io/en/latest/user_guide/workflows/alignment.html
- Rhubarb releases: https://github.com/DanielSWolf/rhubarb-lip-sync/releases
- FFmpeg downloads: https://ffmpeg.org/download.html

Always retain this adapter's MFA 3.x requirement when consulting documentation for newer upstream versions.
