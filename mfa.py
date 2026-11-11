"""MFA 3.x English ARPABET alignment import and mouth-pose mapping."""
import math
import re

# Codes are independent of Rhubarb; aliases are ordered pose suggestions.
POSES = [
 ('AA', 'AA / AH', ('AA','AH','A')),
 ('EH', 'EH / AE', ('EH','E','AA')),
 ('IH', 'IH', ('IH','IY','I')),
 ('IY', 'EE', ('IY','EE','I')),
 ('OW', 'OH', ('OW','OH','O')),
 ('UW', 'OO', ('UW','OO','U')),
 ('M', 'M / B / P', ('M','MBP')),
 ('F', 'F / V', ('F','FV','FF')),
 ('L', 'L', ('L',)),
 ('TH', 'TH', ('TH','DH','L')),
 ('S', 'S / Z', ('S','SZ','IY','I')),
 ('SH', 'SH / CH / J', ('SH','CH','S','IY')),
 ('K', 'K / G / NG', ('K','KG','IH','IY')),
 ('T', 'T / D / N', ('T','DD','D','N','L')),
 ('ER', 'R / ER', ('ER','R','OW')),
 ('W', 'W', ('W','UW','U')),
]
CODES = {p[0] for p in POSES} | {'X'}
PHONE_POSES = {
 'AA':'AA', 'AH':'AA', 'AE':'EH', 'EH':'EH', 'IH':'IH', 'IY':'IY',
 'AO':'OW', 'OW':'OW', 'UH':'UW', 'UW':'UW',
 'M':'M', 'B':'M', 'P':'M', 'F':'F', 'V':'F', 'L':'L',
 'TH':'TH', 'DH':'TH', 'S':'S', 'Z':'S', 'SH':'SH', 'ZH':'SH',
 'CH':'SH', 'JH':'SH', 'K':'K', 'G':'K', 'NG':'K',
 'T':'T', 'D':'T', 'N':'T', 'R':'ER', 'ER':'ER', 'W':'W', 'Y':'IY',
 'HH':'IH',  # Broad fallback, not an independent jaw/bone control.
}
DIPHTHONGS = {'AY':('AA','IY'), 'AW':('AA','UW'), 'EY':('EH','IY'), 'OY':('OW','IY')}
SILENCE = {'', 'sil', 'sp', '<eps>'}
NUMBER = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'

def parse_textgrid(text):
    """Read MFA's long TextGrid format, exactly one speaker phone tier."""
    header = re.split(r'(?m)^\s*item\s*\[\d+\]:', text)[0]
    maximum = re.search(r'\bxmax\s*=\s*(' + NUMBER + ')', header)
    if not maximum:
        raise ValueError('Expected an MFA long TextGrid with xmax header.')
    duration = float(maximum.group(1))
    if not math.isfinite(duration) or not 0 < duration <= 3600:
        raise ValueError('Invalid duration or recording exceeds one hour.')
    tiers = []
    for block in re.split(r'(?m)^\s*item\s*\[\d+\]:', text)[1:]:
        name = re.search(r'\bname\s*=\s*"((?:[^"]|"")*)"', block)
        if not name or not (name.group(1).lower() == 'phones' or name.group(1).lower().endswith(' - phones')):
            continue
        if not re.search(r'\bclass\s*=\s*"IntervalTier"', block):
            continue
        entries = re.findall(r'intervals\s*\[\d+\]:\s*xmin\s*=\s*(' + NUMBER + r')\s*xmax\s*=\s*(' + NUMBER + r')\s*text\s*=\s*"((?:[^"]|"")*)"', block)
        count = re.search(r'intervals:\s*size\s*=\s*(\d+)', block)
        if not count or len(entries) != int(count.group(1)):
            raise ValueError('Incomplete or malformed phone intervals in TextGrid.')
        tiers.append(entries)
    if len(tiers) != 1:
        raise ValueError('Expected exactly one phones tier. Use a single-speaker long TextGrid.')
    cues, previous, unknown = [], 0.0, set()
    def add(a,b,code):
        if b > a:
            cues.append({'start':a, 'end':b, 'value':code})
    for av,bv,label in tiers[0]:
        a,b = float(av),float(bv)
        if not math.isfinite(a+b) or a < previous-1e-6 or b < a or b > duration+1e-6:
            raise ValueError('Invalid or overlapping phone intervals.')
        if a > previous:
            add(previous,a,'X')
        if label.lower() in SILENCE:
            add(a,b,'X')
        else:
            phone = re.sub(r'_[BIES]$', '', label.upper())
            phone = re.sub(r'[012]$', '', phone)
            if phone in DIPHTHONGS:
                left,right = DIPHTHONGS[phone]
                middle = a+(b-a)*.6
                add(a,middle,left); add(middle,b,right)
            elif phone in PHONE_POSES:
                add(a,b,PHONE_POSES[phone])
            else:
                unknown.add(label)
        previous = b
    if unknown:
        raise ValueError('Unrecognized phones: ' + ', '.join(sorted(unknown)) + '. Use english_us_arpa models; spn often means a word is missing from the dictionary.')
    if previous < duration:
        add(previous,duration,'X')
    if not cues:
        raise ValueError('No phone intervals in alignment.')
    return {'metadata':{'duration':duration},'mouthCues':cues}
