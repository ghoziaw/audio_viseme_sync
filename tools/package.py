"""Build a legacy Blender add-on ZIP using an explicit allowlist."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
FILES = ('__init__.py', 'audio.py', 'core.py', 'discovery.py', 'mfa.py',
         'mfa_runner.py', 'README.md', 'docs/TUTORIAL.md')


def main():
    output = ROOT / 'downloads' / 'audio_viseme_sync-0.2.0.zip'
    output.parent.mkdir(exist_ok=True)
    for name in FILES:
        if not (ROOT / name).is_file():
            raise FileNotFoundError(name)
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for name in FILES:
            archive.write(ROOT / name, 'audio_viseme_sync/' + name)
    with ZipFile(output) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {'audio_viseme_sync/' + n for n in FILES}
        for name in FILES:
            assert archive.read('audio_viseme_sync/' + name) == (ROOT / name).read_bytes()
    print(f'Package verified: {output} ({len(FILES)} files)')


if __name__ == '__main__':
    main()
