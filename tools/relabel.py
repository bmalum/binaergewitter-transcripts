"""Second speaker-naming pass (offline, no GPU): re-label the speakers in the existing <base>-speech.json files.

The first pass (name_speakers.py) compared every sentence with voiceprints of the current hosts. Voices without a
voiceprint became "Gast N" (per episode), and early-era hosts whose voice or microphone had changed were often
misnamed. This pass does not depend on enrolled voiceprints:

  1. cluster    Cluster the sentence embeddings of each episode on their own (agglomerative, cosine). On the 17
                Auphonic-labelled episodes this finds the right number of speakers and is as accurate as the first
                pass (93.4 % of words vs. 92.9 %).
  2. persons    Group the per-episode clusters of all episodes into persons (average linkage over cluster centroids).
                A person is one voice across years, e.g. "Pfleidi" in 109 episodes from 2011 to 2020.
  3. export     Match every cluster to the nearest person and write the person's name as speaker.

Persons get their names from outside the audio: show notes ("Heute mit Marc, Mat und Ingo"), introductions in the
episodes ("Ich bin der Pfleidi"), vocatives ("Hallo, Jan") and the guest lists. The evidence is in PERSON_NAMES below
and in the README. Person ids are the rank by total speech time; PERSON_CHECK makes export stop if the ids moved.

Inputs : $BG_OUT/<base>.emb.npy (+ .asr.json for the one episode whose sentences were split differently), and the
         transcripts/<base>-speech.json from the first pass as the text source.
Usage  : relabel.py cluster            write $BG_WORK/diar.pkl
         relabel.py persons [sim]      write $BG_WORK/persons.json, library.pkl and assign.json (default sim 0.6)
         relabel.py export <dir>       write <dir>/<base>-speech.json and <dir>/manifest.json (run make_vtt.py after)
Needs numpy and scikit-learn.
"""
import glob, json, os, pickle, sys
from collections import Counter, defaultdict

import numpy as np
from sklearn.cluster import AgglomerativeClustering

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.environ.get("BG_OUT", f"{ROOT}/data/out")
WORK = os.environ.get("BG_WORK", f"{ROOT}/data")
TR = os.environ.get("BG_TRANSCRIPTS", f"{ROOT}/transcripts")

T_CLUSTER = 0.58      # cosine distance at which sentences of one episode are merged into one voice
MIN_CORE_S = 2.0      # only sentences at least this long form the clusters; shorter ones are assigned afterwards
MIN_CLUSTER_S = 60.0  # voices with less speech than this are folded into the nearest bigger voice
PERSON_SIM = 0.6      # average-linkage similarity at which voices of different episodes count as one person
PERSON_MIN_MIN = 3.0  # voices with at least this many minutes of speech build the persons

# person id (rank by speech time, see PERSON_CHECK) -> speaker name
PERSON_NAMES = {
    0: "Felix", 1: "Ingo", 2: "Pfleidi", 3: "l33tname", 4: "Marc", 5: "Mat", 6: "Markus",
    7: "Schmittlauch", 8: "Jan", 9: "Torbjörn", 10: "Jörg", 11: "Walter Kriha", 12: "Taki", 13: "Tobi",
    14: "Jan (Hackerspace)", 15: "Lukas", 16: "Marcel", 17: "Thomas", 18: "Frank", 19: "Toby", 20: "Dirk",
    21: "Andreas",
}
# evidence episodes: each person must contain a voice from this episode, otherwise the ids moved and export stops
PERSON_CHECK = {
    0: "2011-04-13.RadioTux.Binaergewitter.2", 1: "2011-08-18.RadioTux.Binaergewitter.3",
    2: "2012-03-07.Binaergewitter.Talk.5", 3: "2018-08-25.Binaergewitter.Talk.208", 4: "2017-04-03.Binaergewitter.Westcoast.1",
    5: "2013-11-14.Binaergewitter.Talk.74", 6: "2016-09-08.Binaergewitter.Talk.157",
    7: "2017-09-14.Binaergewitter.Talk.181",
    8: "2013-03-28.Binaergewitter.Talk.46", 9: "2012-05-17.Binaergewitter.Spezial.4",
    10: "2017-09-20.Binaergewitter.Spezial.7", 11: "2011-04-13.RadioTux.Binaergewitter.2",
    12: "2017-01-19.Binaergewitter.Talk.164", 13: "2017-10-17.Binaergewitter.Talk.183",
    14: "2011-08-18.RadioTux.Binaergewitter.3", 15: "2017-04-09.Binaergewitter.Westcoast.2",
    16: "2014-12-18.Binaergewitter.Talk.111", 17: "2016-05-29.Binaergewitter.Talk.149",
    18: "2014-03-06.Binaergewitter.Talk.86", 19: "2017-10-17.Binaergewitter.Talk.183",
    20: "2011-01-08.RadioTux.Binaergewitter.NoSQL", 21: "2012-05-17.Binaergewitter.Spezial.4",
}


def bases():
    return [os.path.basename(f)[:-12] for f in sorted(glob.glob(f"{TR}/*-speech.json"))]


def load_episode(b):
    """-> (segments, embeddings) aligned to the sentences of the transcript (NaN row = no embedding)."""
    segs = json.load(open(f"{TR}/{b}-speech.json"))
    emb = np.load(f"{OUT}/{b}.emb.npy").astype(np.float32)
    if len(segs) == len(emb):
        return segs, emb
    # one episode (Talk #212) has sentences that were split differently: average the embeddings over each sentence
    a = json.load(open(f"{OUT}/{b}.asr.json"))["segments"]
    mids = np.array([(x[0] + x[1]) / 2 for x in a])
    rows = []
    for s in segs:
        v = emb[(mids >= s["start"]) & (mids <= s["end"])]
        v = v[~np.isnan(v[:, 0])]
        rows.append(v.mean(0) if len(v) else np.full(emb.shape[1], np.nan, np.float32))
    return segs, np.stack(rows)


def diarize(durs, emb):
    """Voice id per sentence (-1 = no embedding) and {id: unit centroid}."""
    ok = ~np.isnan(emb[:, 0])
    E = np.where(ok[:, None], emb, 0)
    core = np.where(ok & (durs >= MIN_CORE_S))[0]
    cl = AgglomerativeClustering(n_clusters=None, metric="cosine", linkage="average",
                                 distance_threshold=T_CLUSTER).fit(E[core]).labels_
    secs = Counter()
    for i, c in zip(core, cl):
        secs[c] += durs[i]
    keep = [c for c, s in secs.items() if s >= MIN_CLUSTER_S] or [secs.most_common(1)[0][0]]
    cents = {}
    for c in keep:
        v = E[core[cl == c]].mean(0)
        cents[c] = v / np.linalg.norm(v)

    def assign(cents):
        ids = list(cents)
        return np.where(ok, np.array(ids)[(E @ np.stack([cents[c] for c in ids]).T).argmax(1)], -1)

    for _ in range(2):  # reassign every sentence to the nearest voice, then recompute the voices
        lab = assign(cents)
        new = {}
        for c in cents:
            m = np.where((lab == c) & (durs >= MIN_CORE_S))[0]
            if len(m) >= 3:
                v = E[m].mean(0)
                new[c] = v / np.linalg.norm(v)
        cents = new or cents
    return assign(cents), cents


def cmd_cluster():
    res = {}
    for b in bases():
        segs, emb = load_episode(b)
        durs = np.array([s["end"] - s["start"] for s in segs])
        lab, cents = diarize(durs, emb)
        res[b] = dict(labels=lab, clusters={int(c): dict(centroid=v, minutes=float(durs[lab == c].sum() / 60))
                                            for c, v in cents.items()})
        print(b, sorted((round(x["minutes"]) for x in res[b]["clusters"].values()), reverse=True))
    pickle.dump(res, open(f"{WORK}/diar.pkl", "wb"))


def unit(v):
    return v / np.linalg.norm(v)


def cmd_persons(sim=PERSON_SIM):
    D = pickle.load(open(f"{WORK}/diar.pkl", "rb"))
    items = [(b, c, v["centroid"], v["minutes"]) for b, d in D.items() for c, v in d["clusters"].items()]
    X = np.stack([i[2] for i in items])
    big = [k for k, i in enumerate(items) if i[3] >= PERSON_MIN_MIN]
    cl = AgglomerativeClustering(n_clusters=None, metric="cosine", linkage="average",
                                 distance_threshold=1 - sim).fit(X[big]).labels_
    groups = defaultdict(list)
    for k, c in zip(big, cl):
        groups[c].append(k)
    order = sorted(groups, key=lambda g: -sum(items[k][3] for k in groups[g]))
    persons = []
    lib = {}
    for rank, g in enumerate(order):
        ks = groups[g]
        persons.append(dict(person=rank, minutes=round(sum(items[k][3] for k in ks)),
                            members=[[items[k][0], items[k][1], round(items[k][3], 1)] for k in sorted(ks, key=lambda k: items[k][0])]))
        use = [k for k in ks if items[k][3] >= 5] or ks
        lib[rank] = unit(np.mean([X[k] for k in use], 0))
    for _ in range(2):  # refine: library = mean of the voices that are clearly closest to it
        acc = defaultdict(list)
        for k, i in enumerate(items):
            if i[3] < 5:
                continue
            s = {p: float(X[k] @ v) for p, v in lib.items()}
            p = max(s, key=s.get)
            if s[p] >= 0.8:
                acc[p].append(X[k])
        for p, vs in acc.items():
            lib[p] = unit(np.mean(vs, 0))
    assign, weak = {}, []
    for b, d in D.items():
        assign[b] = {}
        for c, v in d["clusters"].items():
            s = sorted(((float(v["centroid"] @ l), p) for p, l in lib.items()), reverse=True)
            assign[b][int(c)] = [s[0][1], round(s[0][0], 3), s[1][1], round(s[1][0], 3), round(v["minutes"], 1)]
            if s[0][0] < 0.75:
                weak.append((b, c, s[0][1], s[0][0], v["minutes"]))
    json.dump(dict(persons=persons), open(f"{WORK}/persons.json", "w"), indent=1)
    json.dump(assign, open(f"{WORK}/assign.json", "w"))
    pickle.dump(lib, open(f"{WORK}/library.pkl", "wb"))
    print(len(persons), "persons;", len(weak), "voices with similarity < 0.75 to their person:")
    for w in weak:
        print("  %-46s voice %d -> person %d (%.2f), %.1f min" % w)


def cmd_export(dst):
    D = pickle.load(open(f"{WORK}/diar.pkl", "rb"))
    A = json.load(open(f"{WORK}/assign.json"))
    P = json.load(open(f"{WORK}/persons.json"))["persons"]
    for pid, base in PERSON_CHECK.items():
        if pid >= len(P) or base not in {m[0] for m in P[pid]["members"]}:
            sys.exit(f"person {pid} is not the one PERSON_NAMES was written for (no voice in {base})")
    os.makedirs(dst, exist_ok=True)
    manifest = json.load(open(f"{ROOT}/manifest.json"))
    mf = {e["base"]: e for e in manifest["episodes"]}
    for b, d in D.items():
        segs = json.load(open(f"{TR}/{b}-speech.json"))
        names = {int(c): PERSON_NAMES.get(v[0], f"Person {v[0]}") for c, v in A[b].items()}
        out = [names[int(l)] if l >= 0 else None for l in d["labels"]]
        for i in range(len(out)):  # sentences without embedding (< 0.8 s) take the previous sentence's speaker
            if out[i] is None and i:
                out[i] = out[i - 1]
        for i in reversed(range(len(out))):  # ... or the next one at the very start
            if out[i] is None:
                out[i] = out[i + 1] if i + 1 < len(out) else "Unbekannt"
        prev, talk = None, Counter()
        for s, spk in zip(segs, out):
            s["speaker"], s["newpara"], prev = spk, spk != prev, spk
            talk[spk] += s["end"] - s["start"]
        json.dump(segs, open(f"{dst}/{b}-speech.json", "w"), ensure_ascii=False)
        mf[b]["speaker_minutes"] = {k: round(v / 60, 1) for k, v in talk.most_common()}
    manifest["speaker_naming"] = ("second pass (tools/relabel.py): voice clustering per episode, voices grouped across "
                                  "episodes into persons, persons named from show notes and in-episode evidence")
    json.dump(manifest, open(f"{dst}/manifest.json", "w"), ensure_ascii=False, indent=1)
    print("wrote", len(D), "episodes to", dst)


if __name__ == "__main__":
    {"cluster": cmd_cluster, "persons": lambda: cmd_persons(*map(float, sys.argv[2:3])),
     "export": lambda: cmd_export(sys.argv[2])}[sys.argv[1]]()
