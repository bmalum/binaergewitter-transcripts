"""Correct systematic ASR errors in the -speech.json files: product names, people, rubric names, the "⁇" artifact.

Every rule is a regular expression over the sentence text (matched on whole words), a replacement and optionally a
context test on the sentence and its two neighbours. The rules only cover errors that are the same everywhere ("ButterFS"
is always btrfs); words that are also real German words (Nass, Skala, Wim, Erlangen ...) are only replaced when the
context fits. The word timestamps are kept in step: a replacement that changes the number of words merges or splits
the timings of the affected words.

Usage: fix_terms.py <in-dir> <out-dir> [report.txt]    (in-dir and out-dir may be the same)
"""
import glob, json, os, random, re, sys
from collections import Counter, defaultdict

NB = r"(?<![\wäöüÄÖÜß])"
NE = r"(?![\wäöüÄÖÜß])"
I = re.I

# (name, pattern, replacement, flags, context, not_context)
#  - replacement may use \g<sfx>, an optional ending captured as (?P<sfx>...) in the pattern
#  - context must occur in the sentence or one of its neighbours (case-insensitive); not_context must not
RULES = [
    # ---- "⁇" is what the ASR emits for + and &; the specific ones first ----
    ("AT&T", r"AT\s*⁇\s*T", "AT&T", 0, None, None),
    ("1&1", r"1\s*⁇\s*1", "1&1", 0, None, None),
    ("M&M", r"M\s*⁇\s*M", "M&M", 0, None, None),
    ("Google+", r"Google\s*⁇", "Google+", 0, None, None),
    ("C++", r"C\s*⁇", "C++", 0, None, None),
    ("& (between words)", r"(?<=\w)\s+⁇\s+(?=\w)", " & ", 0, None, None),
    # ---- tech terms that are never right as heard ----
    ("btrfs", r"butter[ -]?f\s?s|butterfest|butterfass|better[ -]?fs|butfs|b-tree[ -]?fs", "btrfs", I, None, None),
    ("systemd", r"system d", "systemd", I, None, None),
    ("McAfee", r"mc ?a?e?ffie|mcaffey|mceffy|mcaffy|mcgaffey|macaffie|mceffe|mc ?affee|mcgafee|mcafey", "McAfee", I, None, None),
    ("Tizen", r"tizzen|titzen|tizenfon", "Tizen", I, None, None),
    ("ownCloud", r"oncloud|omcloud|own cloud", "ownCloud", I, None, None),
    ("Threema", r"threamer", "Threema", I, None, None),
    ("Thorium", r"torium", "Thorium", I, None, None),
    ("Ubiquiti", r"ubiquity", "Ubiquiti", I, None, None),
    ("ZigBee", r"sigbee|sigbi", "ZigBee", I, None, None),
    ("Jolla", r"joller|yolla", "Jolla", I, None, None),
    ("PadFone", r"petphone|padphone", "PadFone", I, None, None),
    ("Congstar", r"kongstar|bongstar", "Congstar", I, None, None),
    ("OPNsense", r"open ?sense", "OPNsense", I, None, None),
    ("QEMU", r"qemo|cuemo|kimu", "QEMU", I, None, None),
    ("nginx", r"ngin[ -]x|engine[ -]x", "nginx", I, None, None),
    ("Piwik", r"pivik|pivic", "Piwik", I, None, None),
    ("Sipgate", r"zip ?gate", "Sipgate", I, None, None),
    ("WebDAV", r"webdaf", "WebDAV", I, None, None),
    ("Hacktoberfest", r"hektoberfest|hoktoberfest|hectoberfest|haktoberfest|hacktober", "Hacktoberfest", I, None, None),
    ("Zarafa", r"zaraffa", "Zarafa", I, None, None),
    ("Telefónica", r"telefonika", "Telefónica", I, None, None),
    ("Homematic", r"homatic", "Homematic", I, None, None),
    ("MeeGo", r"migo", "MeeGo", I, None, None),
    ("FOSDEM", r"fostem", "FOSDEM", I, None, None),
    ("Bloomfilter", r"blumenfilter", "Bloomfilter", I, None, None),
    ("Ansible", r"ensible", "Ansible", I, None, None),
    ("LaTeX", r"latech", "LaTeX", I, None, None),
    ("EC2", r"easy ?2", "EC2", I, None, None),
    ("Lucene", r"lucine?", "Lucene", I, None, None),
    ("FrOSCon", r"frostcon", "FrOSCon", I, None, None),
    ("Linux", r"lunix", "Linux", I, None, None),
    ("Sailfish", r"Selfish|safish|safisch", "Sailfish", 0, None, r"selfish gene|dawkins"),
    ("Sailfish (lower case)", r"selfish", "Sailfish", 0, r"sailfish|jolla|smartphone|handy|nokia|android|tizen|firefox os|ubuntu touch|betriebssystem|rubrik|os\b|mobile|phone", r"selfish gene|dawkins"),
    # ---- file system / NAS ----
    ("Dateisystem", r"(?:fallsystem|pfeilsystem|feilsystem)(?P<sfx>e|en)?", r"Dateisystem\g<sfx>", I, None, None),
    ("Dateisystem (Bildsystem)", r"bildsystem(?P<sfx>e|en)?", r"Dateisystem\g<sfx>", I, r"btrfs|zfs|ext4|platte|festplatte|mount|snapshot|raid|partition|nas|speicher|backup|ordner|dateien|dateisystem", None),
    ("Buildsystem", r"bildsystem(?P<sfx>e|en)?", r"Buildsystem\g<sfx>", I, None, None),
    ("NAS (capitalised noun)", r"(?<=[\wäöüß,;]\s)Nass(?![\wäöüß])(?P<sfx>-[\w-]+)?", r"NAS\g<sfx>", 0, None, r"regen|wasser|durch"),
    ("NAS", r"nass", "NAS", I, r"synology|qnap|nas\b|raid|freenas|truenas|speicher|storage|backup|platten|festplatte|samba|nfs|diskstation", r"regen|wasser|nass[ -]?rasier"),
    # ---- names and rubrics ----
    ("Lesefoo", r"lesefu(?:hr|ß|h|ch)?|lasefu|laserfu|laserfoo|lesefo|lesefr[oa]|lesefond|lesefon", "Lesefoo", I, None, None),
    ("Pfleidi", r"(?:fly ?d[iyeé]?|fleid[iy]|fleity|fladi|flighty|pleity|pleid[iy]|plydi|pfeili|pfeidi|pfleity|flyy|flyd[ey]?)(?P<sfx>s)?", r"Pfleidi\g<sfx>", I, None, None),
    ("l33tname", r"leadname|lead name|liedname|leetname", "l33tname", I, None, None),
    ("Schmittlauch", r"schmidt?lauch|schmidt?loch|schmidlauch|schmidloch", "Schmittlauch", I, None, None),
    ("Torvalds", r"torwal[dtsz]|torwalts|torvalz", "Torvalds", I, None, None),
    ("Stallman", r"(?:storman|stolman|stallmann|stollman|stormann|stolmann)(?P<sfx>s)?", r"Stallman\g<sfx>", I, None, None),
    ("Kim Dotcom", r"kim\.com(?:\.com)?", "Kim Dotcom", I, None, None),
    ("Binärgewitter", r"binäge\w*|bienergewitter|winärgewitter|benegewitter|benägewitter|benärgewitter|binary gewitter", "Binärgewitter", I, None, None),
    ("RadioTux", r"radio tux|radetux|radetucks", "RadioTux", I, None, None),
    ("Yodeling Yeti", r"jodling[ -]?jeti|yodling yeti|yodeling jeti", "Yodeling Yeti", I, None, None),
    ("Poettering", r"pöttering", "Poettering", I, None, None),
    # ---- Heise (the news site), heard as "heiße" before the nouns it is used with ----
    ("Heise", r"heiße[r]?(?=\s+(?:Artikel|Forum|Kommentar|Verlag|Developer|Online|Nachrichten|News|Newsticker|Security)\b)", "Heise", I, None, None),
    ("Heise (capital, mid-sentence)", r"(?<=[\wäöüß,;]\s)Heiße(?![\wäöüß])", "Heise", 0, None, r"jürgen|heißen"),
    # ---- real German words standing for a term: only with fitting context ----
    ("Vim", r"(?<![\w.\-])wim(?![\w])", "Vim", I, None, r"wenders|wim hof|thoelke|wim kok|wim sonne"),
    ("Scala", r"skala", "Scala", I, r"java|jvm|programmiersprache|funktional|haskell|clojure|kotlin|akka|play|typsystem|framework|compiler|entwickl|code|sprache|node|ruby|python|\bgo\b|php|applikation", None),
    ("Erlang", r"Erlangen", "Erlang", 0, r"elixir|beam|otp|erlang|funktional|prozess|mnesia|couchdb|riak|programmiersprache|ejabberd|rabbitmq|actor|sprache", r"universität|uni\b|fau\b|friedrich|stadt|nürnberg|fürth|wohn|studier"),
    ("Elixir", r"elixier", "Elixir", I, None, r"lebens|zauber|trank|liebes"),
    ("DECT", r"Deckt(?!\s+(?:sich|das|es|ab|alles|nicht|euch|uns|die|den|dein|meine))", "DECT", 0, None, None),
    ("Gentoo", r"gento|gentu", "Gentoo", I, None, None),
    ("Arch Linux", r"archinux", "Arch Linux", I, None, None),
    ("Emacs", r"e-macs", "Emacs", I, None, None),
]
COMPILED = []
for name, pat, rep, fl, ctx, nctx in RULES:
    full = pat if ("⁇" in pat or pat.startswith("(?<")) else NB + "(?:" + pat + ")" + NE
    COMPILED.append((name, re.compile(full, fl), rep, re.compile(ctx, I) if ctx else None, re.compile(nctx, I) if nctx else None))
GATE = re.compile("|".join("(?:%s)" % c[1].pattern.replace("(?P<sfx>", "(?:") for c in COMPILED), re.I)


def spans(words):
    out, pos = [], 0
    for w in words:
        out.append((pos, pos + len(w)))
        pos += len(w) + 1
    return out


def splice(ts, text, sp, a, b, new):
    """Replace text[a:b] by `new` inside the word list `ts` (in place); returns (old words as string, new tokens)."""
    ids = [k for k, (s0, e0) in enumerate(sp) if e0 > a and s0 < b]
    if not ids:
        return None
    i, j = ids[0], ids[-1]
    pre = text[sp[i][0]:a] if a > sp[i][0] else ""
    post = text[b:sp[j][1]] if b < sp[j][1] else ""
    toks = (pre + new + post).split()
    old = ts[i:j + 1]
    t0, t1, conf = old[0][1], old[-1][2], min(w[3] for w in old)
    if len(toks) == len(old):
        repl = [[t, w[1], w[2], w[3]] for t, w in zip(toks, old)]
    elif len(toks) == 1:
        repl = [[toks[0], t0, t1, conf]]
    elif not toks:
        repl = []
    else:
        step = (t1 - t0) / len(toks)
        repl = [[t, round(t0 + k * step, 3), round(t0 + (k + 1) * step, 3), conf] for k, t in enumerate(toks)]
    old_str = " ".join(w[0] for w in old).strip()
    ts[i:j + 1] = repl
    return old_str, toks


def apply_rules(seg, neighbours, stats):
    """Apply all rules to one sentence in place; returns [(rule, old, new)]. stats counts skipped-by-context."""
    ts = seg["timestamps"]
    text = " ".join(w[0] for w in ts)
    if text != seg["text"] or not GATE.search(text):
        return []                          # (14 sentences have words and text out of step: left alone)
    done = []
    for name, rx, rep, ctx, nctx in COMPILED:
        matches = []
        for m in rx.finditer(text):
            if ctx or nctx:
                window = neighbours + " " + text
                if (ctx and not ctx.search(window)) or (nctx and nctx.search(window)):
                    stats[name]["skipped"] += 1
                    if len(stats[name]["skex"]) < 40:
                        stats[name]["skex"].append((seg.get("_ep", ""), text))
                    continue
            matches.append(m)
        if not matches:
            continue
        sp = spans([w[0] for w in ts])
        for m in reversed(matches):       # right to left, so earlier offsets stay valid
            a, b = m.start(), m.end()
            new = m.expand(rep) if "\\g<" in rep else rep
            before = text[:a].rstrip()
            if new[:1].islower() and m.group(0).strip()[:1].isupper() and (not before or before[-1] in ".!?"):
                new = new[:1].upper() + new[1:]
            r = splice(ts, text, sp, a, b, new)
            if r:
                done.append((name, r[0], " ".join(r[1])))
        text = " ".join(w[0] for w in ts)
    seg["text"] = text
    return done


def apply_manual(src, dst, fixes_file):
    """fixes_file: JSON list of {"base", "idx", "old", "new"}; `old` must occur in the sentence (first occurrence is used)."""
    fixes = defaultdict(list)
    for fx in json.load(open(fixes_file)):
        fixes[fx["base"]].append(fx)
    done = bad = 0
    for base, fl in fixes.items():
        f = f"{src}/{base}-speech.json"
        segs = json.load(open(f))
        for fx in sorted(fl, key=lambda x: (x["idx"], -len(x["old"]))):
            s = segs[fx["idx"]]
            ts = s["timestamps"]
            text = " ".join(w[0] for w in ts)
            a = text.find(fx["old"])
            if text != s["text"] or a < 0:
                bad += 1
                print("not applicable:", base, fx["idx"], fx["old"], "->", fx["new"])
                continue
            splice(ts, text, spans([w[0] for w in ts]), a, a + len(fx["old"]), fx["new"])
            s["text"] = " ".join(w[0] for w in ts)
            done += 1
        json.dump(segs, open(f"{dst}/{base}-speech.json", "w"), ensure_ascii=False)
    print("manual fixes applied: %d, not applicable: %d" % (done, bad))


def main(src, dst, report=None):
    os.makedirs(dst, exist_ok=True)
    stats = defaultdict(lambda: dict(n=0, eps=set(), var=Counter(), ex=[], skipped=0, skex=[]))
    changed = 0
    for f in sorted(glob.glob(f"{src}/*-speech.json")):
        b = os.path.basename(f)[:-12]
        segs = json.load(open(f))
        for i, s in enumerate(segs):
            nb = " ".join(segs[k]["text"] for k in (i - 1, i + 1) if 0 <= k < len(segs))
            before = s["text"]
            done = []
            for _ in range(3):               # a second round catches compounds such as "Flydy-Pleity"
                d = apply_rules(s, nb, stats)
                if not d:
                    break
                done += d
            if done:
                changed += 1
                for name, old, new in done:
                    st = stats[name]
                    st["n"] += 1; st["eps"].add(b); st["var"][old] += 1
                    if len(st["ex"]) < 60:
                        st["ex"].append((b, before, s["text"]))
        json.dump(segs, open(f"{dst}/{b}-speech.json", "w"), ensure_ascii=False)
    lines = ["%-26s %6s %5s %7s  variants" % ("rule", "hits", "eps", "skipped")]
    for name, st in sorted(stats.items(), key=lambda x: -x[1]["n"]):
        lines.append("%-26s %6d %5d %7d  %s" % (name, st["n"], len(st["eps"]), st["skipped"], ", ".join("%s %d" % kv for kv in st["var"].most_common(6))))
    for name, st in stats.items():
        pass
    lines.append("sentences changed: %d, corrections: %d" % (changed, sum(s["n"] for s in stats.values())))
    print("\n".join(lines))
    if report:
        random.seed(1)
        out = list(lines) + [""]
        for name, st in sorted(stats.items(), key=lambda x: -x[1]["n"]):
            out.append("## %s (%d hits, %d episodes, %d skipped by context)" % (name, st["n"], len(st["eps"]), st["skipped"]))
            for b, bf, af in random.sample(st["ex"], min(4, len(st["ex"]))):
                out.append("  %s\n    - %s\n    + %s" % (b, bf[:230], af[:230]))
            for _, t in random.sample(st["skex"], min(3, len(st["skex"]))):
                out.append("  SKIPPED (no fitting context): %s" % t[:230])
            out.append("")
        open(report, "w").write("\n".join(out))


if __name__ == "__main__":
    if sys.argv[1] == "--manual":          # fix_terms.py --manual <dir-in> <dir-out> <fixes.json>
        os.makedirs(sys.argv[3], exist_ok=True)
        if os.path.abspath(sys.argv[2]) != os.path.abspath(sys.argv[3]):
            import shutil
            for f in glob.glob(f"{sys.argv[2]}/*-speech.json"):
                shutil.copy(f, sys.argv[3])
        apply_manual(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
