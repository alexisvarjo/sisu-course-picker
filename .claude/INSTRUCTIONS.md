# SISU Curriculum Designer — Operating Manual

A personal tool to design a study curriculum across the Finnish SISU
university federation (Helsinki, Aalto, and ~7 others). Workflow:

1. Pull the live course catalog (one-time; already done — 12,983 courses in
   `data/courses.jsonl`).
2. Pull your completed courses from each SISU you're enrolled at.
3. Write `goals.md` saying what you want to learn.
4. Open a Claude Code session, let it browse the catalog against your goals
   and propose a multi-period plan.
5. Iterate. Validate the plan with `tools/schedule.py`. Repeat.

It runs **on a Claude Max subscription alone** — no separate Anthropic API
balance is required. (One script, `tools/rank.py`, *is* API-based but is fully
optional and only useful if you want a one-shot score-everything pass.)

---

## Table of contents

1. [Prerequisites](#prerequisites)
2. [Setup](#setup)
3. [Step 1 — Fetch your transcripts](#step-1--fetch-your-transcripts)
4. [Step 2 — Write `goals.md`](#step-2--write-goalsmd)
5. [Step 3 — Pre-filter the catalog](#step-3--pre-filter-the-catalog-recommended)
6. [Step 4 — Design the curriculum in a Claude Code session](#step-4--design-the-curriculum-in-a-claude-code-session)
7. [Step 5 — Validate your plan with `tools/schedule.py`](#step-5--validate-your-plan)
8. [How prerequisites work](#how-prerequisites-work-the-three-tier-model)
9. [Script reference](#script-reference)
10. [File reference](#file-reference)
11. [Troubleshooting](#troubleshooting)
12. [FAQ](#faq)

---

## Prerequisites

- Python 3.10+
- An active Claude Code installation (`claude` on your `$PATH`) with a Max
  subscription. The Max subscription is what pays for the curriculum-design
  session — no API key needed for the default workflow.
- A SISU account at one or more Finnish universities. The transcript fetcher
  knows the following hosts:

  | Host | University |
  | --- | --- |
  | `sisu.helsinki.fi` | University of Helsinki |
  | `sisu.aalto.fi` | Aalto University |
  | `sisu.jyu.fi` | University of Jyväskylä |
  | `sisu.tuni.fi` | Tampere University |
  | `sisu.lut.fi` | LUT |
  | `sisu.hanken.fi` | Hanken |
  | `sisu.arcada.fi` | Arcada UAS |
  | `sisu.lab.fi` | LAB UAS |
  | `sisu.ha.ax` | Åland UAS |

---

## Setup

```bash
cd /home/alexis/Desktop/sisu
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium     # one-time browser download (~150 MB)
```

`requirements.txt` already lists everything you need:
- `playwright` — for the transcript fetcher
- `pyyaml` — for `schedule.yaml` parsing
- `anthropic` — only used by the optional `tools/rank.py`

You can skip `anthropic` if you're sure you'll never run `tools/rank.py`.

The catalog (`data/courses.jsonl`) is already present — 12,983 currently-active
courses, last refreshed by `tools/ingest_catalog.py`. You don't need to re-crawl
unless courses have meaningfully changed (start of each academic year is a
reasonable cadence).

---

## Step 1 — Fetch your transcripts

This grabs the list of courses you've already completed at each SISU instance,
which is essential for ranking ("don't suggest things I've done") and for
prerequisite satisfaction.

```bash
python tools/fetch_transcript.py --domain sisu.helsinki.fi
```

A Chromium window will open at `https://sisu.helsinki.fi/student/`. Log in
via your university's Shibboleth (the script doesn't see your credentials —
it only spies on the API requests once you're authenticated). **Wait until
the dashboard is fully visible (you see your name in the top-right)**, then
return to the terminal and press Enter.

Repeat for every SISU instance you have an account at:

```bash
python tools/fetch_transcript.py --domain sisu.aalto.fi
```

Each run merges into a single file at `data/transcript.json`, keyed by
domain. Re-running for the same domain refreshes that block.

**What it returns:** the raw `/ori/api/my-attainments` response from SISU.
Roughly a JSON list with one entry per completed course, including the
course code, group ID, credits, grade, and attainment date. Schema is whatever
SISU returns — we just persist it.

> If you see `HTTP 401`, see [Troubleshooting](#troubleshooting).

---

## Step 2 — Write `goals.md`

This is the most important file in the project. Everything downstream
(LLM ranking, curriculum proposals) reads `goals.md` to score relevance.
Spend 10–20 minutes on it.

```bash
# Edit the existing goals.md — treat it as the structural example
$EDITOR goals.md       # or open in your IDE
```

The template has six sections:

1. **Career goal** — concrete enough to distinguish two paths
2. **Topics I want to go deep on** — 5–10, in priority order
3. **Topics I'm not interested in** — concrete drops (languages, management, …)
4. **Current level** — your math/CS/domain background; strong and weak spots
5. **Practical constraints** — language preference, max credits/period, deadlines
6. **Anything else** — anything else useful

Write in full sentences when nuance matters. Vague answers → noisy scoring.

---

## Step 3 — Pre-filter the catalog (recommended)

13,000 courses is too many to score thoroughly even with Claude Max.
Filtering first to a few hundred candidates keeps the in-session ranking
crisp and well within your subscription budget.

### Browse the org tree

Discover which faculties / departments / programmes exist at each university:

```bash
python tools/filter_courses.py --list-orgs --root hy-university-root-id
python tools/filter_courses.py --list-orgs --root aalto-university-root-id
```

Output is a tree: `[descendant-courses | own-courses]  org-id  Name`.

You can search for branches by name:

```bash
python tools/filter_courses.py --list-orgs --root hy-university-root-id --search "law|medic|pharm"
```

Matching nodes get a `*` marker but the tree isn't pruned, so you can see
context.

### Apply filters → `courses_filtered.jsonl`

```bash
python tools/filter_courses.py \
    --blacklist-org-name "law" "medicine" "pharmacy" "veterinary" \
    --keep-attainment-language en \
    --out data/courses_filtered.jsonl
```

Common flags:

| Flag | What |
| --- | --- |
| `--blacklist-org NAME ID …` | Drop courses whose `organisations` include any of these org IDs (descendants included). |
| `--blacklist-org-name PATTERN …` | Same, but match org names by regex. Easier when you don't have IDs. |
| `--blacklist-code-prefix PROV LL …` | Drop by course code prefix. |
| `--keep-attainment-language en fi sv` | Keep only courses attainable in these languages. |
| `--refresh-orgs` | Re-fetch the org tree (default: use cache at `data/_orgs.json`). |

Re-run with different filters until `wc -l data/courses_filtered.jsonl`
shows something in the 500–2000 range.

---

## Step 4 — Design the curriculum in a Claude Code session

```bash
claude
```

On startup, Claude Code reads `CLAUDE.md` which tells it about every file
and the recommended workflow. Open with something concrete:

> *"Read `goals.md`, then browse `data/courses_filtered.jsonl`. Give me the
> top 30 candidate courses with a one-sentence rationale each. Anchor your
> rationale in the course content, not the name. Skip anything I've already
> completed (check `data/transcript.json`)."*

The session will:

1. Read `goals.md` and `data/transcript.json`
2. Grep `courses_filtered.jsonl` for concepts from your goals
3. Read the most promising matches in detail
4. Produce a ranked shortlist with reasoning
5. Optionally write `data/scored_courses.jsonl` so subsequent prompts can
   reuse the work

Other prompts that work well:

| You ask | What it does |
| --- | --- |
| *"Why did you score CS-E4500 so low?"* | Re-reads its description and explains. Be wary of subjective scoring — push back. |
| *"What does CS-E4500 need beforehand?"* | Runs `prereq_graph.py before CS-E4500`, cross-references your transcript and `declared_knowledge.json`. |
| *"Build me a 4-period plan starting autumn 2025, focused on probabilistic ML."* | Proposes a `schedule.yaml`. Doesn't write to disk until you confirm. |
| *"Add MS-A0001 to autumn 2025 period I."* | Edits `schedule.yaml`, runs `tools/schedule.py`, reports any violations. |
| *"Replace the missing prereqs with what I actually know"* | For each `MISSING_PREREQS` warning, asks you whether you have equivalent knowledge from outside SISU. If yes, appends to `data/declared_knowledge.json`. |

**Iterate freely.** Claude isn't authoritative — push back, change goals,
re-rank. The point of doing this in a session is conversation, not batch
processing.

---

## Step 5 — Validate your plan

Once you have a `schedule.yaml`:

```bash
python tools/schedule.py
```

This:

- Verifies every course code exists in the catalog
- Reports prerequisite-ordering violations (with the three-tier model below)
- Warns on credits-per-period overruns
- For open (empty `[]`) periods, suggests candidates ranked by score that
  satisfy prereqs by that point

Re-run after every edit to `schedule.yaml`. Wire it into your in-session
loop — after Claude proposes a change, validate, show errors, refine.

---

## How prerequisites work — the three-tier model

SISU prerequisites are **soft** — the system doesn't enforce them at
enrolment. But they're still useful as:

1. A **sequencing signal**: do A before B.
2. A **difficulty signal**: a probability course with "measure theory" listed
   as a prereq is grad-level; the same course with no prereqs is intro-level.

`tools/schedule.py` considers a prerequisite **satisfied** if any one of these
three is true:

| Tier | Source | Authored by |
| --- | --- | --- |
| 1. Completed in transcript | `data/transcript.json` | `tools/fetch_transcript.py` (auto) |
| 2. Scheduled in an earlier period | `schedule.yaml` | You |
| 3. Declared equivalent knowledge | `data/declared_knowledge.json` | You, after the session asks |

### Declared knowledge

If a prereq isn't in your transcript but you *do* know the material — from
self-study, MOOCs, work, a previous degree, an exchange semester — declare
it.

The Claude Code session will ask before adding entries. **Never silently
infer** — it should always ask whether you have equivalent knowledge before
treating something as satisfied.

Template at `.claude/declared_knowledge.template.json`. Real shape:

```json
{
  "courses": [
    {
      "code": "MS-C1541",
      "groupId": "aalto-OPINKOHD-1125…",
      "note": "Self-studied from Rudin during summer 2024.",
      "declared_at": "2026-05-14"
    }
  ]
}
```

`code` and `groupId` are both optional — supply whichever you have. The
validator matches on either.

---

## Script reference

### `tools/ingest_catalog.py` — refresh the catalog

```bash
python tools/ingest_catalog.py                              # default: HY + Aalto, current academic year
python tools/ingest_catalog.py --universities all           # all 9 federated universities
python tools/ingest_catalog.py --list-universities          # print the known list
python tools/ingest_catalog.py --staleness-cutoff none      # include older courses
```

Two-phase crawl: enumerates course IDs via `/kori/api/course-unit-search`
with prefix queries, then concurrently fetches each detail via
`/kori/api/course-units/{id}`. Resumable — re-running skips IDs already in
the output JSONL. Federation-aware (one domain query returns courses from
across all participating universities). Default takes 5–10 minutes for a
full crawl with HY+Aalto.

### `tools/fetch_transcript.py` — pull your completed courses

```bash
python tools/fetch_transcript.py --domain sisu.helsinki.fi
python tools/fetch_transcript.py --domain sisu.aalto.fi --out data/transcript.json
```

Opens Chromium, you log in via Shibboleth, the script captures the SISU
SPA's bearer token (by spying on its outbound `/ori/api/*` requests) and
reuses it to call `/ori/api/my-attainments`. Multi-domain: re-run with a
different `--domain` and it merges.

### `tools/filter_courses.py` — discover + filter

```bash
# Discovery
python tools/filter_courses.py --list-orgs --root hy-university-root-id --search "law"

# Filter to a smaller working set
python tools/filter_courses.py --blacklist-org-name "law" "medicine" \
    --keep-attainment-language en \
    --out data/courses_filtered.jsonl
```

### `tools/prereq_graph.py` — explore the prereq DAG

```bash
python tools/prereq_graph.py before CS-E4500           # ancestors (what to take first)
python tools/prereq_graph.py after  CS-A1140           # descendants (what this unlocks)
python tools/prereq_graph.py chain  CS-E4500           # both directions
python tools/prereq_graph.py orphans                   # prereqs referenced but not in catalog
python tools/prereq_graph.py export --format dot       # whole graph, Graphviz-renderable
```

`[C]` markers are compulsory prereqs (still soft, but more on-paper); `[r]`
is recommended. "needs ANY OF" headings show OR-groups (alternatives).

### `tools/resolve_orphans.py` — fix dangling prereq refs

```bash
python tools/resolve_orphans.py                        # all orphans
python tools/resolve_orphans.py --limit 50             # smoke test
```

About 600–700 prereqs reference course group IDs not in `courses.jsonl`
(usually older versions or out-of-scope universities). This script looks
them up via `/kori/api/course-units/by-group-id` and writes them to
`data/courses_extra.jsonl`. Concatenate the two files to get a fuller
prereq graph:

```bash
cat data/courses.jsonl data/courses_extra.jsonl > /tmp/full.jsonl
python tools/prereq_graph.py --in /tmp/full.jsonl orphans
```

### `tools/schedule.py` — validate your plan

```bash
python tools/schedule.py                              # uses schedule.yaml + auto-discovers transcript + declared
python tools/schedule.py --schedule alt.yaml          # try a different plan file
```

Errors halt; warnings are informational. `MISSING_PREREQS` is the structured
list of things the Claude Code session can act on (propose adding the prereq
to an earlier period, or ask about equivalent knowledge).

### `tools/rank.py` — **OPTIONAL**, requires API balance

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python tools/rank.py --check-cost-only                # estimate spend
python tools/rank.py
```

Uses the Anthropic **Batches API** to score every course in
`data/courses.jsonl` against `goals.md` with Opus 4.7 + prompt caching. Bills
against your Anthropic API balance, **not** your Claude Max subscription.
If you don't have API credits, skip this entirely — the default workflow does
ranking in-session.

---

## File reference

| Path | What | Authored by |
| --- | --- | --- |
| `CLAUDE.md` | Project guide loaded by Claude Code on startup. | Maintainer |
| `INSTRUCTIONS.md` | This file. | Maintainer |
| `requirements.txt` | Python deps. | Maintainer |
| `goals.md` (existing) | Your study goals, free-form markdown. | **You** |
| `.claude/schedule.template.yaml` → `schedule.yaml` | Period-by-period plan. | **You** (via session) |
| `.claude/declared_knowledge.template.json` → `data/declared_knowledge.json` | Courses you know but didn't take. | **You** (via session prompts) |
| `data/courses.jsonl` | The catalog. One full course detail per line. | `tools/ingest_catalog.py` |
| `data/courses.jsonl.gz` | Compressed shipping copy (~15 MB). | Manual |
| `data/courses_extra.jsonl` | Orphan-resolved supplementary courses. | `tools/resolve_orphans.py` |
| `data/courses_filtered.jsonl` | Narrowed candidate pool. | `tools/filter_courses.py` |
| `data/transcript.json` | Your completed courses per university. | `tools/fetch_transcript.py` |
| `data/scored_courses.jsonl` | LLM-scored shortlist with reasoning. | Claude Code session or `tools/rank.py` |
| `data/_orgs.json` | Cached organisation tree. | `tools/filter_courses.py` |

---

## Troubleshooting

### `tools/fetch_transcript.py` returns HTTP 401

The script needs to capture the SISU SPA's bearer token. That happens
automatically as long as you wait until the dashboard is *fully loaded*
before pressing Enter. Visible signal: your name appears in the top-right.

If 401 persists:

1. Re-run with the browser visible (`--headless` is off by default — keep it
   that way for debugging).
2. After login, click around the SISU app a bit before pressing Enter — the
   SPA will make `/ori/api/*` calls naturally and the script will grab the
   token from one of them.
3. If still failing, your Shibboleth session may have a path scope issue.
   File a bug; we can dig into the network trace.

### `tools/schedule.py` says "course CODE is not in the catalog"

The code in your `schedule.yaml` doesn't match any code in
`data/courses.jsonl`. Case matters (it's matched exactly). Re-check the code,
and if the course is currently offered, confirm it wasn't filtered out by
`tools/ingest_catalog.py`'s staleness rule (default keeps anything with offerings
ending after the current academic year started).

### `tools/schedule.py` warns about an orphan prereq groupId

Run `tools/resolve_orphans.py` to fetch missing prereq courses, then concatenate:

```bash
python tools/resolve_orphans.py
cat data/courses.jsonl data/courses_extra.jsonl > /tmp/full.jsonl
python tools/schedule.py --catalog /tmp/full.jsonl
```

### My Claude Code session is burning through Max budget

Pre-filter more aggressively in Step 3. Aim for 500–1000 candidates rather
than 2000+. Use `--keep-attainment-language en` to drop any course that
isn't offered in a language you'll attain in, and `--blacklist-org-name` to
remove whole faculties.

### `tools/rank.py` says my goals don't make sense

It probably read the template placeholders. Make sure `goals.md` has real
content, not `(write here)` placeholders.

---

## FAQ

**Q: Do I need to re-crawl the catalog often?**
A: Maybe once at the start of each academic year. Course content doesn't
shift week to week.

**Q: Can I use this for a university not in the list?**
A: If the university runs the Funidata SISU stack (most Finnish
universities do), `ingest_catalog.py --universities all` should already
include it — check `--list-universities`. For other student-info systems,
no.

**Q: How fresh is the prerequisite data?**
A: As fresh as the catalog. Note that SISU only encodes *formal* prereqs
in the structured fields. Many courses describe prereqs only in free-text
`prerequisites.en`; we capture that field too but the prereq graph is built
from the structured side only.

**Q: I'm enrolled at HY *and* Aalto. Does anything break?**
A: No. Run `tools/fetch_transcript.py` once per SISU and the transcripts merge.
The catalog is federated so courses from both unis are already in
`data/courses.jsonl`.

**Q: Are scores reproducible?**
A: No — Claude is non-deterministic. Scores from the in-session workflow
will vary run-to-run. If you need a frozen snapshot, write the session's
output to `data/scored_courses.jsonl` and reuse it.

**Q: What if I disagree with the model's ranking?**
A: Tell it. The whole point of doing this in a Claude Code session is
that you can argue. *"You scored CS-E4500 a 9 but I think it's a 4 because
X"* — and the model will revise.

**Q: Can the tool actually enrol me in courses?**
A: No. SISU's enrolment endpoints require auth scopes we don't touch and
are easy to misuse. You enrol manually through the SISU UI once you've
decided what to take.
