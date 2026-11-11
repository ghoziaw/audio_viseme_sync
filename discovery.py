"""Conservative recognition of viseme names and FACS category labels."""
import re

ALIASES = {'A': ('M', 'MBP'), 'B': ('IY', 'EE', 'I'), 'C': ('EH', 'E'),
           'D': ('AA', 'AH', 'A'), 'E': ('OW', 'OH', 'O'),
           'F': ('UW', 'OO', 'U', 'W'), 'G': ('F', 'FV'), 'H': ('L',)}
SOUNDS = {x.lower() for group in ALIASES.values() for x in group} | {
    'ch', 'dd', 'dh', 'er', 'ih', 'k', 'n', 'ng', 'r', 's', 'sh', 'sil',
    'ff', 'sz', 'kg', 't', 'th', 'uh', 'y', 'z', 'zh', 'rest', 'neutral', 'b', 'p', 'v'}

def sound_name(value):
    value = re.sub(r'[^a-z0-9]', '', value.lower())
    # Longest meaningful prefixes first. Do not interpret arbitrary suffixes.
    for prefix in ('facs',):
        if value.startswith(prefix):
            value = value[len(prefix):]
    for prefix in ('ectrl', 'ctrl', 'bs'):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    for prefix in ('visemes', 'viseme', 'phoneme', 'vis', 'v'):
        if value.startswith(prefix) and value[len(prefix):] in SOUNDS:
            value = value[len(prefix):]
            break
    return value if value in SOUNDS else ''

def is_viseme(key, labels=(), in_facs=False):
    if key.lower().endswith(('(fin)', '(rst)')):
        return False
    if key.lower().startswith(('ectrlv', 'ctrlv', 'viseme')):
        return True
    values = (key, *labels)
    for value in values:
        compact = re.sub(r'[^a-z0-9]', '', value.lower())
        if ('vis' in compact or 'phoneme' in compact) and sound_name(value):
            return True
        if (in_facs or compact.startswith('facs')) and sound_name(value):
            return True
    return False

def suggest(code, keys, labels, aliases=None):
    # Ambiguity is left for the user, instead of choosing between FACS/legacy.
    for alias in (aliases if aliases is not None else ALIASES[code]):
        found = [key for key in keys if any(sound_name(v) == alias.lower()
                 for v in (key, *labels.get(key, ())))]
        if len(found) == 1:
            return found[0]
        if len(found) > 1:
            return ''
    return ''
