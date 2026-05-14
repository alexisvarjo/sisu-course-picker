# SISU curriculum design — end-to-end workflow for Claude

Read this file in full before starting. It is the playbook for taking a
user from "I want to plan my Finnish university curriculum" to a
validated, period-by-period `schedule.yaml`. Follow steps in order; do
**not** skip the gotchas — they cost real time when re-discovered.

---

## Prerequisites the user must have done before calling you

1. SISU credentials for at least one Finnish university (Helsinki, Aalto, etc.).
2. `goals.md` filled in (use the existing `goals.md` as the structural example) — be specific about career
   goal, weak-area topics, hard constraints (ECTS/period, deadlines),
   **which universities they have study rights at**, and **which
   faculties / topic areas to exclude**.
3. (Optional but useful) Access to Anthropic API balance — only needed if
   you want to use `tools/rank.py` for batch scoring ~1000s of courses. The
   in-session Haiku-subagent flow below does not need it.

If `goals.md` doesn't exist or contains only the prior user's content,
ask the user to overwrite it with their own. Don't proceed without it
— every downstream decision flows from `goals.md`. In particular, the
**Universities I can take courses at** and **Faculties / topic areas
to exclude** sections drive Steps 2–3 directly.

---

## Step 0: Sanity-check the existing state

```bash
ls data/
```

Look for:
- `data/courses.jsonl` — catalog. If missing, you need to crawl (Step 2).
- `data/transcript.json` — completed courses. If missing, do Step 1.
- `data/courses_filtered.jsonl` — narrowed catalog. Always re-derive
  after re-crawl.
- `goals.md` — user's targets.
- `schedule.yaml` — existing plan. Build on it, don't overwrite blindly.

---

## Step 1: Fetch the transcript (per university the user listed)

**Read `goals.md` → "Universities I can take courses at" first.** Run
`fetch_transcript.py` once per SISU instance the user has study right
at — *not* a hardcoded HY+Aalto list.

University name → SISU domain mapping:

| User says | `--domain` value |
|---|---|
| Helsinki / HY / University of Helsinki | `sisu.helsinki.fi` |
| Aalto / Aalto University | `sisu.aalto.fi` |
| Tampere / TUNI / Tampere University | `sisu.tuni.fi` |
| Jyväskylä / JYU / University of Jyväskylä | `sisu.jyu.fi` |
| LUT / Lappeenranta | `sisu.lut.fi` |
| Hanken / SHH | `sisu.hanken.fi` |
| Arcada | `sisu.arcada.fi` |

```bash
# example: user lists Helsinki + Aalto
python tools/fetch_transcript.py --domain sisu.helsinki.fi
python tools/fetch_transcript.py --domain sisu.aalto.fi
```

This launches Playwright; the user logs in interactively. Output is
merged into `data/transcript.json` keyed by SISU instance. Re-run per
university the user is enrolled at. The transcript is the source of
truth for "what's done" — it suppresses already-completed courses from
recommendations.

---

## Step 2: Crawl the catalog — the hard part

The default `tools/ingest_catalog.py` has two silent failure modes that **will**
cost you the user's most-wanted courses if you don't address them.

### Failure mode 1: API returns empty for high-cardinality queries

The kori `/course-unit-search` endpoint silently returns
`searchResults: []` when `total > ~1000`, even though `total` is reported
correctly. Default 3-char prefixes like `pro`, `sto`, `MAST`, `MAT`,
`ELEC` all hit this cap and return **zero** courses. Without fixing
this, you'll miss MAST31701 (Probability Theory I), MAST31706
(Stochastic Analysis I), MAST32007 (Time Series I), and most of the
HY math MSc curriculum.

**Fix**: use narrow code-prefix queries. A working queries file lives at
`.claude/.claude/queries_hyaalto.txt`. If it doesn't exist, write one with at minimum:

```
# HY math/stat/CS/data
MAST3
MAST2
MAT11
MAT12
MAT21
MAT22
MATR3
DATA1
DATA2
TKT1
TKT2

# HY economics
ECOM-

# Aalto math/stat
MS-E1
MS-E2
MS-C1
MS-C2
MS-A0

# Aalto CS/EE
CS-E
CS-A
CS-C
ELEC-C
ELEC-E

# Aalto finance/business
FIN-E
FIN-A
28E
28L
28C
31E
TU-E

# Topic stems missing from defaults
sto
ito
tim
brow
mart
prob
real
funct
optim
hilb
banac
sobol
fourier
bayes
mcmc
kalm
sde
spde
hank
dsge
```

### Failure mode 2: staleness filter drops courses with no activityPeriods

The default `--staleness-cutoff academic-year` (cutoff = Aug 1 of the
current academic year) is too strict in two ways:
1. It drops courses whose `activityPeriods` is missing from the search
   hit (real, currently-offered courses fall into this hole — observed:
   `28L30111` Theoretical Asset Pricing, `28L30211` Empirical Asset
   Pricing).
2. Even an 18-month window (e.g., `2024-11-14`) was empirically too
   strict for some courses the user wanted.

**Fix**: use `--staleness-cutoff none` for the main crawl. The marginal
cost of carrying genuinely-stale courses is small (you'll skip them at
recommendation time anyway), and the cost of dropping a course the user
needs is high (you have to re-ingest later).

### Restrict the crawl to the user's universities

`ingest_catalog.py` defaults to filtering crawl results to HY+Aalto.
**Override based on goals.md**. The flag is `--universities <root-id>...`.
Get the canonical root IDs with:

```bash
python tools/ingest_catalog.py --list-universities
```

The mapping (current as of 2026):

| User says | `--universities` value |
|---|---|
| Helsinki / HY | `hy-university-root-id` |
| Aalto | `aalto-university-root-id` |
| Tampere / TUNI | `tuni-university-root-id` |
| Jyväskylä / JYU | `jyu-university-root-id` |
| LUT | `lut-university-root-id` |
| Hanken / SHH | `shh-university-root-id` |
| Arcada | `arc-university-root-id` |

Pair this with `--domains <sisu-host>...` so the search-side enumeration
runs against an instance the user can reach (one is enough — federation
returns courses from every cooperating university anyway). Default
`--domains sisu.helsinki.fi sisu.aalto.fi`.

```bash
# Example: user lists Helsinki + Aalto
python tools/ingest_catalog.py \
  --queries-file .claude/queries_hyaalto.txt \
  --staleness-cutoff none \
  --universities hy-university-root-id aalto-university-root-id \
  --domains sisu.helsinki.fi sisu.aalto.fi \
  --out data/courses.jsonl \
  --workers 16 --rps 20

# Example: user is at Helsinki + Tampere only
python tools/ingest_catalog.py \
  --queries-file .claude/queries_hyaalto.txt \
  --staleness-cutoff none \
  --universities hy-university-root-id tuni-university-root-id \
  --domains sisu.helsinki.fi sisu.tuni.fi \
  --out data/courses.jsonl \
  --workers 16 --rps 20
```

If the user names a university you don't recognise, run
`--list-universities` and match by name. Don't guess the root ID.

If catalog size becomes a problem (>20k entries), tighten to a 2-3 year
window (`2023-08-01` or similar) — but only after confirming that
hasn't dropped any user-requested courses.

`tools/ingest_catalog.py` is append-only and resumable — re-running with the
same `--out` updates in place. If a specific code goes missing later,
do a targeted re-fetch:

```bash
echo -e "28L\nKTTS4190" > /tmp/missing.txt
python tools/ingest_catalog.py --queries-file /tmp/missing.txt \
  --staleness-cutoff none --out data/courses.jsonl
```

### How to tell if you have a complete-enough catalog

Spot-check by grepping for codes the user mentions or that should
obviously exist:

```bash
python -c "
import json
codes = ['MAST31701','MAST31702','MAST31706','MAST31710','MAST32007','MAST32008']
have = set()
with open('data/courses.jsonl') as f:
    for line in f:
        c = json.loads(line)
        if c['code'] in codes: have.add(c['code'])
print('present:', have)
print('missing:', set(codes) - have)
"
```

If anything is missing, re-crawl with broader queries / no staleness.

---

## Step 3: Filter the catalog — infer the blacklist, don't ask

`data/courses.jsonl` includes every Finnish university's federated
catalog (~13k+ courses). Narrow it before any candidate scoring.

**Do this without prompting the user.** Read `goals.md` end-to-end.
Their **Career goal** + **Topics to go deep on** + **Topics NOT
interested in** sections already imply 90 % of the faculty exclusions
unambiguously. A quant doesn't need humanities, theology, veterinary,
pharmacy, agriculture, art/design, language centres, etc. — infer
that. Use the explicit **Universities** and **Faculties / topic areas
to exclude** sections (if filled) as overrides and edge-case guidance,
not as the primary input.

The default inference: if the user's goals don't intersect a faculty's
content at all, exclude it. When in doubt about a borderline faculty
(e.g., "should a finance student keep Faculty of Social Sciences for
the Economics programme?"), check the explicit sections. If still
unclear, keep it — over-inclusion is recoverable, over-exclusion costs
a re-crawl.

**Never ask the user "which faculties do you want to exclude?"** That
question is already answered by their goals. Do the inference, run the
filter, and surface what you cut in your reply so they can override if
needed.

### Step 3a: List the org tree first

```bash
python tools/filter_courses.py --list-orgs
```

This dumps every university and faculty/programme with course counts.
Skim it — the names you blacklist must match the actual org names in
the tree (regex, case-sensitive).

### Step 3b: Build the blacklist regex list

Combine three sources of exclusions, all inferred from `goals.md`:

1. **Other universities the user has no study right at.** Read the
   **Universities I can take courses at** section. Top-level names to
   drop: `^Tampere University$`, `^University of Jyväskylä$`,
   `^Lappeenranta-Lahti`, `^Hanken School of Economics$`, `^Arcada`,
   `^LAB University`, `^Åland University`. Drop anything they didn't
   list. (Also drop these as cooperation-network noise unless the
   user explicitly opted them in.)

2. **Irrelevant faculties.** Infer these from the user's career goal,
   topic priorities, and "not interested in" list. A quant's profile
   implies dropping: humanities, law, medicine, dentistry, veterinary,
   pharmacy, theology, education, biology/agriculture/forestry, arts/
   design/architecture, language centres. A bioinformatics student's
   profile would NOT drop biology. A management consultant's would NOT
   drop management studies. Don't ask — infer from goals.

   Within Faculty of Social Sciences specifically, almost all sub-
   programmes are irrelevant to a quant *except* MSc Economics (where
   the ECOM-* macro / econometrics courses live). Drop sub-programmes
   individually by name when needed; keep Economics.

3. **Doctoral programmes**, unless the user explicitly said they have
   doctoral access (rare for MSc students). Pattern: `^Doctoral`,
   `Doctoral Programme`, `Doctoral School`.

### Step 3c: Run the filter

```bash
python tools/filter_courses.py \
  --in data/courses.jsonl \
  --out data/courses_filtered.jsonl \
  --blacklist-org-name <your derived list> \
  --keep-attainment-language en fi
```

If the user said "Finnish OK", include `fi`. English-only users:
`--keep-attainment-language en`.

### Step 3d: Post-filter by `universityOrgIds`

`tools/filter_courses.py` keeps cooperation-network courses hosted *at* user's
universities even if owned by another university. If the user said
"only HY and Aalto", post-filter:

```python
python -c "
import json
keep_unis = {'hy-university-root-id', 'aalto-university-root-id'}  # adjust
kept = []
with open('data/courses_filtered.jsonl') as f:
    for line in f:
        c = json.loads(line)
        ids = set(c.get('universityOrgIds') or [])
        if ids & keep_unis:
            kept.append(line.rstrip())
with open('data/courses_filtered.jsonl','w') as f:
    f.write('\n'.join(kept))
print(f'Kept: {len(kept)}')
"
```

If the user explicitly said cooperation-network courses are fine (e.g.,
"HY + Aalto + anything I can cross-register from Hanken"), skip this
post-filter and instead remove only the universities in their explicit
exclude list.

### Sanity check

Target output size after filter: 500–2000 courses. If much higher, your
faculty blacklist is too lax — list the surviving faculties and add
more. If much lower, you've over-cut — re-read `goals.md`'s exclusion
list and check you're not dropping things the user wants kept (the
"conversely, list anything you'd want kept" sub-bullet of that section).

---

## Step 4: Haiku-parallel candidate screening

This is the in-session ranking flow that doesn't need API balance
(uses Claude Max).

### Step 4a: Build a slim per-course view + chunk it

```python
import json, os, re
done_group_ids = set()
with open('data/transcript.json') as f:
    t = json.load(f)
for uni, block in t['universities'].items():
    for a in block['attainments']:
        gid = a.get('courseUnitGroupId')
        if gid: done_group_ids.add(gid)

slim = []
with open('data/courses_filtered.jsonl') as f:
    for line in f:
        c = json.loads(line)
        if c.get('groupId') in done_group_ids:
            continue
        s = {
            'code': c['code'],
            'name': (c.get('name') or {}).get('en') or (c.get('name') or {}).get('fi'),
            'credits': c.get('credits', {}),
            'content': (c.get('content') or {}).get('en') if c.get('content') else None,
            'outcomes': (c.get('outcomes') or {}).get('en') if c.get('outcomes') else None,
            'uni': 'HY' if 'hy-university-root-id' in (c.get('universityOrgIds') or []) else 'AALTO',
        }
        for k in ('content','outcomes'):
            if s[k] and len(s[k]) > 800: s[k] = s[k][:800]+'…'
        slim.append(json.dumps(s, ensure_ascii=False))

os.makedirs('/tmp/sisu_chunks', exist_ok=True)
N = 12
size = (len(slim) + N - 1) // N
for i in range(N):
    chunk = slim[i*size:(i+1)*size]
    with open(f'/tmp/sisu_chunks/chunk_{i:02d}.jsonl','w') as f:
        f.write('\n'.join(chunk))
```

### Step 4b: Dispatch one Haiku subagent per chunk in parallel

Use the `Agent` tool with `model: haiku` and `subagent_type:
general-purpose`. Send all chunk-screening agents in **a single message**
so they run concurrently. Per-agent prompt template:

```
You are screening a chunk of Finnish university course descriptions for
relevance to a specific student's goals. Read every course in
`/tmp/sisu_chunks/chunk_NN.jsonl` (one JSON object per line) and return
the top ~20 most relevant.

STUDENT GOALS (paste full content of goals.md here, paraphrased if needed):
- Career: <user's career target>
- Topics they want deep on, in priority order: <list>
- Background: <user's existing knowledge>
- Weak areas: <user's stated gaps>

EXCLUDE:
- Language courses
- Management / leadership / soft business / agile / philosophy of X
- Anything for nurses, lawyers, teachers, social work, theology,
  humanities, arts, education, biology/chemistry/medicine
- Bachelor-level intro courses on topics they already know
- Thesis seminars / methodology filler

PRIORITIZE (anchor judgment in `content`/`outcomes` fields, NOT names):
- <topic-specific bullet list derived from goals>

OUTPUT FORMAT — JSON array, one object per kept course:
[
  {"code": "...", "score": 0-10, "rationale": "one sentence anchored in
   content/outcomes — what the course actually teaches and why it serves
   the student's goal."},
  ...
]

Score 0-10. Only include courses scoring >=6. Aim for ~15-25 keepers per
chunk. Return ONLY the JSON array, nothing else.
```

Why Haiku, not Opus: Haiku is fast/cheap enough to fan out across 12
chunks at ~500 courses each. Opus reads each detailed page and would
cost ~10x more for similar judgment quality on this kind of triage.
Reserve Opus for the synthesis step.

### Step 4c: Synthesize the top picks

After all subagents return, **you** (Opus) read all returned candidates,
de-duplicate, sanity-check codes that look suspicious (some agents
hallucinate codes; verify against `data/courses_filtered.jsonl`), and
produce a top-30 with one-sentence rationales each. Group by topic
priority from `goals.md`.

**Sanity-check trap to avoid**: Haiku sometimes returns codes from
cooperation-network courses (e.g., Hanken's "17017", Jyväskylä's
"MATS256", LUT's "BM20A*", Tampere's "DATA.ML.*") that *appear* in
the HY/Aalto SISU but are owned by other universities. Verify with
`universityOrgIds` against the HY/Aalto root IDs before recommending.

---

## Step 5: User iteration

Present the top-30 to the user. Expect rounds of:

1. "Drop X, it's redundant with what I already have." — verify against
   transcript + already-locked courses, then remove.
2. "What about Y?" — query the catalog, report content, decide together.
3. "Replace Z with W." — recompute ECTS budget, ensure the swap fits.

Maintain a running `course_picks.md` with:
- Each chosen course as a row in a table grouped by topic priority.
- Rationale anchored in `content`/`outcomes`, not the name.
- A "decisions made this round" section noting why courses were dropped.
- An "alternates / swap pool" table for things the user reconsidered.
- Open issues: prereqs to confirm, cross-faculty registration to
  arrange, etc.

Don't mark anything as "done" without explicit user agreement.

---

## Step 6: Quant-macro vs broader-quant variants

If the user says "I want quant macro" and HY MSc Math doesn't have
explicit macro courses, dig into HY MSc Economics (`hy-org-116735902`):
codes prefixed `ECOM-`. These are MSc-level (not doctoral — the
doctoral codes are `DPE-*`). Cross-faculty registration is normal at
HY but requires advisor approval.

For applied-math finance, the key HY math sequence is:

```
MAST31701 (Prob Th I)  →  MAST31702 (Prob Th II)
                                    ↓
                       MAST31706 (Stoch Anal I — Itô)
                                    ↓
                       MAST31710 (Stoch Anal II — SDEs)
                                    ↓
                       MAST31908 (Quant Finance — interest-rate models)
```

For the bayesian / state-space toolkit (DSGE estimation, online filtering),
`ELEC-E8106` (Aalto Bayesian Filtering and Smoothing) is the highest-leverage
single course. Pair with HY's MAT22005 (Bayesian inference) → MAST32004
(Adv Bayesian) → MAST32001 (Computational stats).

---

## Step 7: Build `schedule.yaml`

Use `.claude/schedule.template.yaml` as the format reference. Key conventions:

- Period keys: `"YYYY-YYYY/I"` through `/IV` (HY) or `/V` (Aalto). The
  validator orders periods lexicographically.
- Past completed periods can be omitted — the `--transcript` flag
  populates them from `data/transcript.json`.
- `constraints.max_credits_per_period: 30` for users who self-pace
  intensely; `15` for typical Finnish full-time load (≈25h/wk).
- Aalto period I/II = autumn, III/IV = spring. Some Aalto courses are
  autumn-period-I-only or autumn-period-II-only — when the user tells
  you a course is offered in a specific period, schedule it there
  exactly.

Sequence courses respecting:
- Formal SISU prereqs (rare; check via `python tools/prereq_graph.py before
  <CODE>`).
- Content prereqs (frequent; e.g., MAT22005 → MAST32004 even if SISU
  doesn't enforce).
- Math finance pipeline (above).
- Economics pipeline: `ECOM-411 → ECOM-412`.
- Time series: `MAST32007 → MAST32008`.
- Heavy theses last; user-stated deadline matters.

---

## Step 8: Validate

```bash
python tools/schedule.py \
  --schedule schedule.yaml \
  --catalog data/courses.jsonl \
  --transcript data/transcript.json
```

You're looking for:
- "Plan is consistent. No prereq ordering violations." — good.
- Per-period credit totals within the user's stated range (24-30 for
  this user).
- Any "course X is not in the catalog" errors — fix by targeted
  re-fetch (Step 2 fallback).
- Any MISSING_PREREQS warnings — soft, walk through with the user per
  CLAUDE.md guidance (ask if they have equivalent knowledge from
  outside SISU; if yes, append to `data/declared_knowledge.json`).

---

## Step 9: Commit the artifacts

The user typically wants three things at the end:

1. `course_picks.md` — human-readable rationale + alternates pool +
   sequencing notes + open issues for advisors.
2. `schedule.yaml` — the validated period-by-period plan.
3. (Optional) A summary of changes if iterating on an existing plan.

Don't write to `data/` unless explicitly asked. Don't overwrite
`goals.md` based on inferred preferences.

---

## Quick command reference

```bash
# List the canonical SISU university root IDs (use to build --universities)
python tools/ingest_catalog.py --list-universities

# Fetch transcripts — one per SISU instance from goals.md "Universities..."
python tools/fetch_transcript.py --domain sisu.helsinki.fi
python tools/fetch_transcript.py --domain sisu.aalto.fi
# (substitute / add domains based on goals.md)

# Crawl catalog — substitute --universities + --domains for goals.md set
python tools/ingest_catalog.py --queries-file .claude/queries_hyaalto.txt \
  --staleness-cutoff none \
  --universities hy-university-root-id aalto-university-root-id \
  --domains sisu.helsinki.fi sisu.aalto.fi \
  --out data/courses.jsonl \
  --workers 16 --rps 20

# Targeted re-fetch for missing codes
python tools/ingest_catalog.py --queries-file /tmp/missing.txt \
  --staleness-cutoff none --out data/courses.jsonl

# Filter
python tools/filter_courses.py --in data/courses.jsonl \
  --out data/courses_filtered.jsonl \
  --blacklist-org-name "..." \
  --keep-attainment-language en fi

# Browse the org tree (use this to find new things to blacklist)
python tools/filter_courses.py --list-orgs

# Prereq inspection
python tools/prereq_graph.py before <CODE>
python tools/prereq_graph.py after <CODE>
python tools/prereq_graph.py chain <CODE>
python tools/prereq_graph.py orphans

# Schedule validation
python tools/schedule.py --schedule schedule.yaml \
  --catalog data/courses.jsonl --transcript data/transcript.json
```

---

## Common pitfalls — re-read these before believing you're stuck

- **"Course X doesn't exist in the catalog"**: probably the API silent-empty
  bug or the staleness filter. Try targeted re-fetch with
  `--staleness-cutoff none`. If you used a non-`none` staleness for the
  main crawl, consider re-doing the main crawl with `none` too — even
  18 months has been observed to drop user-needed courses.
- **"This 'HY' course is from Jyväskylä"**: the catalog includes
  cooperation-network courses. Always check `universityOrgIds`, not
  `_fetchedFrom`.
- **"User says course is mandatory but it's not in catalog"**: trust the
  user. Then re-crawl with a narrower query that targets the code
  prefix, e.g., `MAST317` for Stochastic Analysis sequence.
- **"`MATS*` is HY math"**: it's not. `MAST*` is HY, `MATS*` is
  Jyväskylä. Easy to miss.
- **"Doctoral courses look perfect"**: the user almost always cannot
  enrol in another faculty's doctoral programme as an MSc student.
  Check the org name (e.g., "Doctoral Programme in Economics" → the
  user can take the MSc-level `ECOM-*` analogue, not the `DPE-*`
  doctoral version).
- **"PDE I has empty prereqs"**: the SISU prereq field is sparse. ODE
  prereqs are typically required de facto (Differentiaaliyhtälöt I+II)
  — surface the 20-ECTS hidden cost to the user before scheduling
  PDE I.
- **"`MS-C1350` Partial Differential Equations"**: Aalto's BSc-level PDE
  has only multivariable calculus as recommended prereq; lighter than
  HY's PDE chain. Good "just enough PDE for applications" pick.
- **"Add hardware/HFT course"**: Aalto's `CS-E4690` Programming Parallel
  Supercomputers is general HPC/MPI, not actually HFT-specific. Real
  HFT (kernel bypass, FPGAs, lock-free) isn't taught in Finnish
  university coursework. Warn the user before they spend a slot on it.
