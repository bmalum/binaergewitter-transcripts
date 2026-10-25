"""Offline speaker naming + export of Auphonic-style <base>-speech.json.

Inputs : $BG_OUT/<base>.asr.json + .emb.npy (from the GPU workers), $BG_AUPHONIC (Auphonic -speech.json ground truth),
         $BG_WORKLIST (which bases are calibration episodes)
Usage  : name_speakers.py eval            leave-one-episode-out accuracy on the calibration episodes
         name_speakers.py export <dir>    write <dir>/<base>-speech.json for every non-calibration episode
"""
import json, os, sys
from collections import Counter, defaultdict

import numpy as np
from sklearn.cluster import AgglomerativeClustering

OUT = os.environ.get("BG_OUT", "data/out")
GT = os.environ.get("BG_AUPHONIC", "data/auphonic")
WORK = json.load(open(os.environ.get("BG_WORKLIST", "tools/worklist.json")))
CALIB = [w["base"] for w in WORK if w["calib"]]
CANON = {"sebastian": "Sebastian"}
SKIP = {None, "", "IngoundFelix", "Felix 2"}
T_KNOWN = float(os.environ.get("T_KNOWN", "0.42"))   # sentence sim below this -> candidate for unknown voice
T_ADAPT = float(os.environ.get("T_ADAPT", "0.45"))   # confident sentences used to adapt prints per episode
T_EP = float(os.environ.get("T_EP", "0.75"))         # episode centroid of a name must be this close to its print


def load(base):
    a = json.load(open(f"{OUT}/{base}.asr.json"))
    e = np.load(f"{OUT}/{base}.emb.npy").astype(np.float32)
    return a, e


def gt_sentence_labels(base, segs):
    """Majority Auphonic speaker over the GT words inside each ASR sentence."""
    gt = json.load(open(f"{GT}/{base}-speech.json"))
    gw = []
    for s in gt:
        spk = CANON.get(s.get("speaker"), s.get("speaker"))
        ts = s.get("timestamps") or []
        if ts:
            gw += [(w[1], w[2], spk) for w in ts]
        else:  # older Auphonic files: segment-level only -> spread the words evenly over the segment
            toks = (s.get("text") or "").split()
            d = (s["end"] - s["start"]) / max(len(toks), 1)
            gw += [(s["start"] + k * d, s["start"] + (k + 1) * d, spk) for k in range(len(toks))]
    gw.sort()
    starts = np.array([w[0] for w in gw])
    labs = []
    for s, e, _ in segs:
        i, j = np.searchsorted(starts, s), np.searchsorted(starts, e)
        c = Counter(w[2] for w in gw[i:j] if w[2] not in SKIP)
        labs.append(c.most_common(1)[0][0] if c else None)
    return labs, gw


def build_prints(bases):
    acc = defaultdict(list)
    for b in bases:
        a, e = load(b)
        labs, _ = gt_sentence_labels(b, a["segments"])
        for (s, t, _), l, v in zip(a["segments"], labs, e):
            if l and t - s >= 2.0 and not np.isnan(v[0]):
                acc[l].append(v)
    prints = {}
    for k, vs in acc.items():
        c = np.mean(vs, 0)
        prints[k] = c / np.linalg.norm(c)
    return prints


def name_episode(segs, emb, prints, adapt=True, unknown=True):
    names = list(prints)
    P = np.stack([prints[n] for n in names])
    ok = ~np.isnan(emb[:, 0])
    E = np.where(ok[:, None], emb, 0)
    sims = E @ P.T
    best = sims.argmax(1)
    bsim = sims.max(1)
    bsim0 = bsim.copy()  # similarity to the global prints; used for unknown-voice detection
    lab = np.array([names[i] for i in best], dtype=object)
    # 1. adapt: per-episode centroid per host from confident sentences, then relabel
    if adapt:
        P2 = []
        for k, n in enumerate(names):
            m = ok & (best == k) & (bsim >= T_ADAPT)
            if m.sum() >= 5:
                c = E[m].mean(0); P2.append(c / np.linalg.norm(c))
            else:
                P2.append(P[k])
        P2 = np.stack(P2)
        sims2 = E @ P2.T
        best, bsim = sims2.argmax(1), sims2.max(1)
        lab = np.array([names[i] for i in best], dtype=object)
    # 1b. episode-level check: a name is accepted only if the centroid of its sentences in THIS episode is close to
    #     the print. Rejected names (an unenrolled voice that happens to sit nearest some host) go to unknown.
    rejected = np.zeros(len(lab), dtype=bool)
    ep_sim = {}
    for k, n in enumerate(names):
        m = ok & (lab == n)
        if m.sum() == 0:
            continue
        c = E[m].mean(0); c /= np.linalg.norm(c)
        ep_sim[n] = float(c @ P[k])
        if ep_sim[n] < T_EP:
            rejected |= m
    # 2. unknown voices: cluster low-similarity + rejected sentences; clusters with >= 3 min speech become "Gast N",
    #    rejected sentences outside such a cluster become "Unbekannt"
    if unknown:
        low = np.where(ok & ((bsim0 < T_KNOWN) | rejected))[0]
        for i in np.where(rejected)[0]:
            lab[i] = "Unbekannt"
        if len(low) >= 10:
            cl = AgglomerativeClustering(n_clusters=None, metric="cosine", linkage="average",
                                         distance_threshold=0.6).fit(E[low]).labels_
            dur = Counter()
            for i, c in zip(low, cl):
                dur[c] += segs[i][1] - segs[i][0]
            g = 0
            for c, d in dur.most_common():
                if d < 180:
                    break
                g += 1
                for i in low[cl == c]:
                    lab[i] = f"Gast {g}"
    # 3. sentences without embedding (< 0.8 s): take the previous sentence's speaker
    for i in range(len(lab)):
        if not ok[i]:
            lab[i] = lab[i - 1] if i else lab[i]
    global LAST_EP_SIM
    LAST_EP_SIM = ep_sim
    return list(lab), bsim


def word_acc(gw, segs, lab):
    starts = np.array([s for s, _, _ in segs])
    okc = tot = 0
    for s, e, spk in gw:
        if spk in SKIP:
            continue
        m = (s + e) / 2
        i = np.searchsorted(starts, m, side="right") - 1
        tot += 1
        okc += i >= 0 and segs[i][0] <= m <= segs[i][1] + 0.5 and lab[i] == spk
    return okc / tot


def evaluate():
    have = [b for b in CALIB if os.path.exists(f"{OUT}/{b}.asr.json")]
    print(f"{len(have)}/{len(CALIB)} calibration episodes available")
    res = defaultdict(list)
    for b in have:
        prints = build_prints([x for x in have if x != b])
        a, e = load(b)
        labs, gw = gt_sentence_labels(b, a["segments"])
        present = Counter(l for l in labs if l)
        row = [b.split(".")[-1], dict(present.most_common())]
        for name, kw in [("plain", dict(adapt=False, unknown=False)), ("adapt", dict(adapt=True, unknown=False)),
                         ("adapt+unknown", dict(adapt=True, unknown=True))]:
            lab, _ = name_episode(a["segments"], e, prints, **kw)
            # a detected guest cluster "Gast N" counts as correct for the GT speaker it mostly covers
            gm = defaultdict(Counter)
            for l, g in zip(lab, labs):
                if str(l).startswith("Gast") and g:
                    gm[l][g] += 1
            lab = [gm[l].most_common(1)[0][0] if l in gm else l for l in lab]
            acc = word_acc(gw, a["segments"], lab)
            res[name].append(acc)
            row.append(f"{name}={acc:.3f}")
        missing = [p for p in present if p not in prints]
        print(*row, "NOT ENROLLED:" if missing else "", *missing)
    for k, v in res.items():
        print(f"mean {k}: {np.mean(v):.3f}  min {np.min(v):.3f}")


def export(dst):
    os.makedirs(dst, exist_ok=True)
    prints = build_prints([b for b in CALIB if os.path.exists(f"{OUT}/{b}.asr.json")])
    manifest = []
    for w in WORK:
        b = w["base"]
        if w["calib"] or not os.path.exists(f"{OUT}/{b}.asr.json"):
            continue
        a, e = load(b)
        segs, words = a["segments"], a["words"]
        lab, bsim = name_episode(segs, e, prints)
        starts = np.array([x[1] for x in words])
        out, prev = [], None
        for (s, t, text), l, sc in zip(segs, lab, bsim):
            i, j = np.searchsorted(starts, s - 0.01), np.searchsorted(starts, t + 0.01)
            out.append({"start": s, "end": t, "text": text, "confidence": 1.0, "track": None, "speaker": l,
                        "newpara": l != prev, "timestamps": [[x[0], x[1], x[2], 1.0] for x in words[i:j]]})
            prev = l
        json.dump(out, open(f"{dst}/{b}-speech.json", "w"), ensure_ascii=False)
        talk = Counter()
        for (s, t, _), l in zip(segs, lab):
            talk[l] += t - s
        manifest.append({"base": b, "duration_s": a["duration_s"], "sentences": len(segs), "words": len(words),
                         "speaker_minutes": {k: round(v / 60, 1) for k, v in talk.most_common()}})
    json.dump({"source": "nvidia/parakeet-tdt-0.6b-v3 + ECAPA voiceprints (speechbrain/spkrec-ecapa-voxceleb)",
               "voiceprints_from": CALIB, "episodes": manifest}, open(f"{dst}/manifest.json", "w"),
              ensure_ascii=False, indent=1)
    print("exported", len(manifest), "episodes to", dst)


if __name__ == "__main__":
    evaluate() if sys.argv[1] == "eval" else export(sys.argv[2])
