"""Write <base>.vtt next to every <base>-speech.json, in the same style as Binaergewitter's Auphonic VTTs:
one cue per line of speech, voice tag with the speaker name. Long segments are split into cues of at most
MAX_S seconds / MAX_C characters at word boundaries (preferring punctuation), using the word timestamps.
Usage: make_vtt.py <dir>
"""
import glob, json, os, sys

MAX_S, MAX_C = 7.0, 110


def ts(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def cues(seg):
    words = seg.get("timestamps")
    if not words or (seg["end"] - seg["start"] <= MAX_S and len(seg["text"]) <= MAX_C):
        return [(seg["start"], seg["end"], seg["text"])]
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        text = " ".join(x[0] for x in cur)
        nxt = words[i + 1] if i + 1 < len(words) else None
        too_long = nxt is not None and (nxt[2] - cur[0][1] > MAX_S or len(text) + 1 + len(nxt[0]) > MAX_C)
        soft = nxt is not None and w[0][-1:] in ".?!,;:" and (w[2] - cur[0][1] > MAX_S * 0.6 or len(text) > MAX_C * 0.6)
        if nxt is None or too_long or soft:
            out.append((cur[0][1], cur[-1][2], text))
            cur = []
    return out


def main(d):
    n = 0
    for f in sorted(glob.glob(f"{d}/*-speech.json")):
        segs = json.load(open(f))
        lines = ["WEBVTT", ""]
        for s in segs:
            for a, b, t in cues(s):
                lines += [f"{ts(a)} --> {ts(max(b, a + 0.01))}", f"<v {s['speaker']}>{esc(t)}", ""]
        open(f.replace("-speech.json", ".vtt"), "w", encoding="utf-8").write("\n".join(lines))
        n += 1
    print("wrote", n, "vtt files")


if __name__ == "__main__":
    main(sys.argv[1])
