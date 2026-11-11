"""Executed by the user's external Conda environment, not Blender Python."""
import importlib.metadata
import os
import shutil
import subprocess
import sys

def main():
    version = importlib.metadata.version('montreal-forced-aligner')
    if version.split('.')[0] != '3':
        raise RuntimeError('This adapter requires MFA 3.x; installed version is '+version)
    exe = shutil.which('mfa')
    if not exe:
        raise RuntimeError('mfa executable missing from the selected Conda environment')
    # All input/output paths are isolated within this generation's temp directory.
    corpus, dictionary, acoustic, output, temporary = sys.argv[1:]
    cmd = [exe, 'align', corpus, dictionary, acoustic, output,
           '--output_format', 'long_textgrid', '--single_speaker',
           '--num_jobs', '1', '--no_use_mp', '--no_use_postgres',
           '--temporary_directory', temporary, '--clean']
    return subprocess.call(cmd)

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print('MFA setup error:', exc, file=sys.stderr)
        sys.exit(1)
