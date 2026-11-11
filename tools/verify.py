"""Reproducible smoke checks; does not run Blender or external engines."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core, discovery, mfa, audio = [load(n) for n in ('core', 'discovery', 'mfa', 'audio')]


def grid(label='AY1'):
    return '''File type = "ooTextFile"
Object class = "TextGrid"
xmin = 0
xmax = 1
item []:
    item [1]:
        class = "IntervalTier"
        name = "phones"
        xmin = 0
        xmax = 1
        intervals: size = 1
        intervals [1]:
            xmin = 0
            xmax = 1
            text = "''' + label + '"\n'


class SmokeChecks(unittest.TestCase):
    def test_source_syntax(self):
        for path in ROOT.rglob('*.py'):
            compile(path.read_text(encoding='utf-8'), str(path), 'exec')

    def test_cue_gaps_are_silence(self):
        cues, duration = core.parse_cues({'metadata': {'duration': 2},
            'mouthCues': [{'start': .5, 'end': 1, 'value': 'A'}]})
        self.assertEqual(cues, [(0, .5, 'X'), (.5, 1, 'A'), (1, 2, 'X')])
        self.assertEqual(duration, 2)

    def test_invalid_cues(self):
        for cue in ({'start': 1, 'end': 0, 'value': 'A'},
                    {'start': 0, 'end': 1, 'value': '?'},
                    {'start': 0, 'end': float('inf'), 'value': 'A'}):
            with self.subTest(cue=cue), self.assertRaises(ValueError):
                core.parse_cues({'mouthCues': [cue]})

    def test_overlapping_cues(self):
        with self.assertRaises(ValueError):
            core.parse_cues({'mouthCues': [
                {'start': 0, 'end': 1, 'value': 'A'},
                {'start': .5, 'end': 2, 'value': 'B'}]})

    def test_duration_limit(self):
        with self.assertRaises(ValueError):
            core.parse_cues({'mouthCues': [{'start': 0, 'end': 3601, 'value': 'A'}]})

    def test_curve_bounds_padding_and_gain(self):
        result = core.build_curves([(0, 1, 'A'), (1, 2, 'X')],
            {'A': ('mouth', .5)}, 24, 10, 2, .8)['mouth']
        self.assertEqual(result[0], (9, 0))
        self.assertEqual(result[-1], (59, 0))
        self.assertAlmostEqual(max(v for f, v in result), .4)
        self.assertTrue(all(0 <= v <= .4 for f, v in result))
        self.assertEqual(result, sorted(result))

    def test_facs_discovery(self):
        self.assertTrue(discovery.is_viseme('facs_ctrl_VisAA'))
        self.assertTrue(discovery.is_viseme('custom', ('Vis L',)))
        self.assertFalse(discovery.is_viseme('facs_ctrl_VisAA(fin)'))
        self.assertFalse(discovery.is_viseme('browRaise'))

    def test_mapping_ambiguity(self):
        self.assertEqual(discovery.suggest('D', ['VisAA'], {}), 'VisAA')
        self.assertEqual(discovery.suggest('D', ['VisAA', 'visemeAA'], {}), '')

    def test_textgrid_stress_and_diphthong(self):
        data = mfa.parse_textgrid(grid())
        self.assertEqual(data['mouthCues'], [
            {'start': 0, 'end': .6, 'value': 'AA'},
            {'start': .6, 'end': 1, 'value': 'IY'}])
        core.parse_cues(data, mfa.CODES)

    def test_textgrid_silence(self):
        self.assertEqual(mfa.parse_textgrid(grid('sil'))['mouthCues'][0]['value'], 'X')

    def test_textgrid_unknown_phone(self):
        with self.assertRaises(ValueError):
            mfa.parse_textgrid(grid('spn'))

    def test_audio_command(self):
        cmd = audio.conversion_command('ffmpeg', 'in.mp3', 'out.wav')
        self.assertEqual(cmd[0], 'ffmpeg')
        self.assertEqual(cmd[-1], 'out.wav')
        for option, value in (('-ac', '1'), ('-ar', '16000'), ('-c:a', 'pcm_s16le')):
            self.assertEqual(cmd[cmd.index(option) + 1], value)


if __name__ == '__main__':
    unittest.main(verbosity=2)
