"""FMD project coverage map.

Mines all FMD sessions for standing instructions, classifies them, and scores
each against EVERY markdown file in the repo to produce a real coverage map:
what is documented, where, in what words, and what is genuinely missing.

Handles: secret redaction (before anything is stored), retry dedupe,
typo-tolerant matching, Snowball stemming, and lead/client authority tagging.
"""
import json, os, re, collections
import snowballstemmer

STEM = snowballstemmer.stemmer("english")
# Typo tolerance: only fuzzy-match tokens long enough that an edit-distance
# hit is meaningful. Short words match everything and would inflate recall.
FUZZY_MIN_LEN = 6
FUZZY_MAX_EDITS = 1

SCRATCH = os.path.expandvars(r"%LOCALAPPDATA%\\hermes\\cache\\scratch")
REPO = r"D:\\fmd-analysis"

# ---------------------------------------------------------------- 1. corpus
NOISE = {".git", ".venv", "run", "model_runs", ".obsidian", ".obsidian-vault",
         "__pycache__", "node_modules", "data", "vm", "tests", "src",
         "notebooks", ".delta", "graphify-out", "handover"}

def load_corpus():
    docs = []
    for root, dirs, fnames in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in NOISE]
        for f in fnames:
            if not f.endswith(".md"):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, REPO).replace("\\", "/")
            if rel.startswith("docs/archive/"):
                continue
            if rel == "docs/reference/session_coverage_map.md":
                # This report quotes instructions verbatim. Leaving it in the
                # corpus lets it certify itself: regenerating it moved the
                # headline by 19 COVERED rows purely from its own quotations.
                continue
            try:
                txt = open(p, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            docs.append({"path": os.path.relpath(p, REPO).replace("\\", "/"),
                         "text": txt})
    return docs

def norm(s):
    s = s.lower()
    s = re.sub(r"`[^`]*`", " ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return " ".join(s.split())

STOP = set("""the a an and or of to in for is are was were we i it that this on
with as at be by not no do does did have has had you your our their from then
than if so what which when how why who all any some more most other into over
under about after before but can could would should will just also there here
they them his her its per also very much like get got make made want need
use used using one two three new old now today please okay ok yes yeah
really actually going thing things stuff lot bit
""".split())

def content_toks(s):
    return [w for w in norm(s).split() if len(w) > 3 and w not in STOP]

print("loading repo corpus...", flush=True)
corpus = load_corpus()
print(f"  {len(corpus)} markdown files", flush=True)

# token index per doc: raw tokens, stemmed tokens, typo-eligible long tokens
for d in corpus:
    raw = set(content_toks(d["text"]))
    d["raw"] = raw
    d["stem"] = set(STEM.stemWords(list(raw)))
    d["long"] = {w for w in raw if len(w) >= FUZZY_MIN_LEN}
    d["low"] = d["text"].lower()
print(f"  total chars: {sum(len(d['text']) for d in corpus):,}", flush=True)

# ------------------------------------------------- 2. conversations
msgs = json.load(open(os.path.join(SCRATCH, "fmd_user_msgs.json"), encoding="utf-8"))
print(f"\nloaded {len(msgs)} user messages", flush=True)

SYSTEMISH = re.compile(r"^\[(System|IMPORTANT|The user sent|OUT-OF-BAND)", re.I)
seen, real = set(), []
for m in msgs:
    t = m["text"].strip()
    if not (25 <= len(t) <= 1400): continue
    if SYSTEMISH.search(t): continue
    if t in seen: continue
    seen.add(t)
    real.append(m)
print(f"after dedupe + size filter: {len(real)}", flush=True)

# ------------------------------------------------- 3. secret redaction
SECRET_PATS = [
    (re.compile(r"(AccountKey\s*=\s*)[A-Za-z0-9+/=]{16,}", re.I), r"\1[REDACTED]"),
    (re.compile(r"(https?://[^\s:@/]+:)[^\s@/]+(@)"), r"\1[REDACTED]\2"),
    (re.compile(r"\b(sk-[A-Za-z0-9]{12,})\b"), "[REDACTED]"),
    (re.compile(r"\b(ghp_[A-Za-z0-9]{20,})\b"), "[REDACTED]"),
    (re.compile(r"\b(AKIA[0-9A-Z]{16})\b"), "[REDACTED]"),
    (re.compile(r"(Authorization:\s*Bearer\s+)[A-Za-z0-9._-]{12,}", re.I), r"\1[REDACTED]"),
    (re.compile(r"([\"']?(?:password|passwd|secret|token|api_key|apikey)[\"']?\s*[:=]\s*)[\"']?[^\s\"',;]{6,}", re.I),
     r"\1[REDACTED]"),
    (re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"), "[REDACTED-BLOB]"),
]
def redact(s):
    out = s
    for pat, rep in SECRET_PATS:
        out = pat.sub(rep, out)
    return out

redacted_ct = sum(1 for m in real if redact(m["text"]) != m["text"])
print(f"messages containing secrets to redact: {redacted_ct}", flush=True)
for m in real:
    m["text"] = redact(m["text"])

# ------------------------------------------------- 4. categorise
CATS = {
    "lead_client": re.compile(
        r"\b(lead|client|sweta|jnj|johnson|she said|they said|her response|"
        r"my lead|per the (lead|client)|from the (lead|client)|email from)\b", re.I),
    "workflow": re.compile(
        r"\b(approval|approve|before (you|we) (run|start)|smoke (test|check)|"
        r"stage[d]? (it |the |on )?(in |on )?(the )?vm|pranayp|amd.?a100|"
        r"shared (box|vm)|dont (touch|leave)|do not (touch|leave)|"
        r"keep (it |the )?in our local|fresh session|handoff|"
        r"no (internal )?names|to share it with|teams message)\b", re.I),
    "domain_rule": re.compile(
        r"\b(micron gate|gate tag|gated (images|classes)|legacy|split|eda|"
        r"label space|annotation of record|dedup|per class|mAP50|"
        r"fold(s|ed)? into|stratif|seed 42|frozen)\b", re.I),
    "presentation": re.compile(
        r"\b(make (it |the )?(an? )?(excel|table|report|workbook|html|notebook)|"
        r"teams message|keep it (short|simple)|light and dark mode|"
        r"mention|separate them|rather than showing|don't mention|"
        r"call them|rename)\b", re.I),
}
STANDING = re.compile(
    r"\b(we (will|should|always|only|never|dont|have to|must|dont)|"
    r"always|never|only use|dont use|do not use|make sure|note that|"
    r"remember|keep in mind|as (i|we) (have )?(mentioned|said|told)|"
    r"reiterat|again|from now on|going forward|rule|freeze|frozen|lock|"
    r"approval|approve|got it\?|please make note|every ?time|"
    r"we (are|were) (not )?using|we will not|we dont)\b", re.I)

def classify(t):
    hits = [k for k, p in CATS.items() if p.search(t)]
    return hits

cands = [m for m in real if STANDING.search(m["text"])]
print(f"standing-instruction candidates: {len(cands)}", flush=True)

# ------------------------------------------------- 5. coverage scoring
# Method: the typo-tolerance + stemming ablation measured on 2026-11-01
# (research ticket t_f811db8a), reproduced here rather than re-tuned.
# An instruction token counts as matched against a document when it is an
# exact token, when its Snowball (English) stem matches, or when it sits
# within edit distance 1 of a document token of >= 6 chars. Tokens shorter
# than 6 chars match exactly only: an edit-distance hit on a three-letter
# word matches almost everything and would inflate recall.

def edit_within(a, b, k=FUZZY_MAX_EDITS):
    """True if a and b are within k edits (bounded Levenshtein)."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > k:
        return False
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        rowmin = cur[0]
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            rowmin = min(rowmin, cur[j])
        if rowmin > k:
            return False
        prev = cur
    return prev[lb] <= k

def best_docs(mtext, n=3):
    """Top-n documents for one instruction, typo-tolerant and stemmed.

    Each candidate carries content-token recall (the coverage measure) and
    the number of verbatim 3-grams shared with the instruction (the
    "worded the same way" shortcut). Best first.
    """
    ct = content_toks(mtext)
    if len(ct) < 3:
        return []
    cset = set(ct)
    cstem = set(STEM.stemWords(list(ct)))
    clong = [w for w in ct if len(w) >= FUZZY_MIN_LEN]
    words = norm(mtext).split()
    grams = [" ".join(words[i:i + 3]) for i in range(len(words) - 2)]
    grams = [g for g in grams if len(g) > 12]

    scored = []
    for d in corpus:
        if not d["raw"]:
            continue
        hit_raw = len(cset & d["raw"])
        hit_stem = len(cstem & d["stem"])
        hit_fuzzy = 0
        if clong and d["long"]:
            for w in clong:
                if w in d["raw"]:
                    continue              # already counted as an exact hit
                if any(edit_within(w, t) for t in d["long"]):
                    hit_fuzzy += 1
        matched = max(hit_raw, hit_stem + hit_fuzzy)
        recall = matched / len(cset)
        if recall < 0.30:
            continue
        g3 = sum(1 for g in grams if g in d["low"])
        scored.append((recall, g3, d["path"]))
    scored.sort(key=lambda c: (-c[0], -c[1]))   # stable: first max wins
    # recall stays at full precision: the verdict thresholds are applied to it
    # before any rounding, exactly as in the measured ablation.
    return [{"path": p, "recall": r, "trigrams": g}
            for r, g, p in scored[:n]]

def coverage_verdict(tops):
    """COVERED / PARTIAL / GAP from the best candidate's recall and 3-grams."""
    if not tops:
        return "GAP", 0.0
    best = tops[0]
    recall = best["recall"]
    if best["trigrams"] >= 1 or recall >= 0.70:
        return "COVERED", recall
    if recall >= 0.45:
        return "PARTIAL", recall
    return "GAP", recall

rows = []
for i, m in enumerate(cands):
    mtext = m["text"][:500]          # the ablation scored the stored row text
    tops = best_docs(mtext)
    verdict, score = coverage_verdict(tops)
    rows.append({
        "date": m["ts"], "session": m["session"][:16],
        "categories": classify(m["text"]),
        "verdict": verdict, "score": round(score, 3),
        "text": mtext,
        "best": tops[0]["path"] if tops else None,
        "top3": tops,
    })
    if (i + 1) % 50 == 0:
        print(f"  scored {i+1}/{len(cands)}", flush=True)

print(f"\nscored {len(rows)}", flush=True)

v = collections.Counter(r["verdict"] for r in rows)
print(f"  COVERED {v['COVERED']}   PARTIAL {v['PARTIAL']}   GAP {v['GAP']}", flush=True)

# category x verdict
cx = collections.Counter()
for r in rows:
    for c in (r["categories"] or ["uncategorised"]):
        cx[(c, r["verdict"])] += 1
print("\ncategory x verdict:")
for (c, verdict), n in sorted(cx.items()):
    print(f"   {c:<16}{verdict:<10}{n}")

json.dump(rows, open(os.path.join(SCRATCH, "coverage_rows.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nsaved coverage_rows.json", flush=True)
