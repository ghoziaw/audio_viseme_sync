"""Local audio conversion helpers; no Blender dependency."""
import os
import shutil
import wave

SUPPORTED = {'.wav', '.ogg', '.mp3', '.m4a'}

def needs_conversion(path):
    if not os.path.isfile(path):
        raise ValueError('Voice file does not exist.')
    suffix = os.path.splitext(path)[1].lower()
    if suffix not in SUPPORTED:
        raise ValueError('Select a WAV, OGG, MP3 or M4A voice file.')
    return suffix in {'.mp3', '.m4a'}

def resolve_ffmpeg(configured):
    exe = configured if configured else shutil.which('ffmpeg')
    if not exe or not os.path.isfile(exe):
        raise ValueError('MP3/M4A needs FFmpeg. Select ffmpeg.exe in add-on preferences, or install ffmpeg on PATH.')
    return exe

def conversion_command(exe, source, output):
    return [exe, '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
            '-i', source, '-map', '0:a:0', '-vn', '-sn', '-dn',
            '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', '-f', 'wav', output]

def validate_wav(path):
    with wave.open(path, 'rb') as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 16000):
            raise ValueError('FFmpeg did not produce the expected mono PCM WAV.')
        if wav.getnframes() == 0:
            raise ValueError('Converted recording contains no audio samples.')
