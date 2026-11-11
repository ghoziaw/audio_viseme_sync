"""Audio cue validation and bounded crossfades. No Blender dependency."""
import math

CODES = 'ABCDEFGHX'

def parse_cues(data, allowed_codes=CODES):
    raw = data.get('mouthCues')
    if not isinstance(raw, list) or not raw:
        raise ValueError('No mouth cues found in Rhubarb output.')
    cues, previous = [], 0.0
    for cue in raw:
        a, b, code = float(cue['start']), float(cue['end']), cue['value']
        if not math.isfinite(a) or not math.isfinite(b) or a < previous - 1e-6 or b <= a or code not in allowed_codes:
            raise ValueError('Invalid or overlapping Rhubarb mouth cues.')
        if a > previous:
            cues.append((previous, a, 'X'))
        cues.append((a, b, code))
        previous = b
    duration = float(data.get('metadata', {}).get('duration', previous))
    if not math.isfinite(duration) or duration < previous - 1e-6:
        raise ValueError('Invalid audio duration.')
    if duration > previous:
        cues.append((previous, duration, 'X'))
    if duration > 3600:
        raise ValueError('Please split recordings longer than one hour.')
    return cues, duration

def build_curves(cues, mapping, fps, start, blend_frames, strength):
    """Sparse linear crossfades; short cues retain a plateau, weights stay bounded."""
    if fps <= 0:
        raise ValueError('Frame rate must be positive.')
    channels = sorted({prop for prop, gain in mapping.values() if prop})
    def pose(code):
        prop, gain = mapping.get(code, ('', 0))
        return {p: strength * gain if p == prop else 0.0 for p in channels}
    # Merge adjacent identical mouth poses, including cues sharing a mapped morph.
    segments = []
    for a, b, code in cues:
        values = pose(code)
        if segments and values == segments[-1][2]:
            segments[-1] = (segments[-1][0], b, values)
        else:
            segments.append((a, b, values))
    points = {}
    def put(t, values):
        points[round(start + t * fps, 6)] = values
    zero = {p: 0.0 for p in channels}
    half = max(0.0, blend_frames / fps / 2)
    a, b, first = segments[0]
    put(a - max(1 / fps, half), zero)
    put(a, first)
    for prev, nxt in zip(segments, segments[1:]):
        boundary = nxt[0]
        width = min(half, (prev[1] - prev[0]) / 3, (nxt[1] - nxt[0]) / 3)
        # With zero smoothing use a near-instant change without duplicate frames.
        width = max(width, min(0.001 / fps, (prev[1] - prev[0]) / 3, (nxt[1] - nxt[0]) / 3))
        put(boundary - width, prev[2])
        put(boundary + width, nxt[2])
    put(segments[-1][1], segments[-1][2])
    put(segments[-1][1] + max(1 / fps, half), zero)
    return {p: [(frame, values[p]) for frame, values in sorted(points.items())] for p in channels}
