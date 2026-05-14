# SISU Curriculum Designer

A Claude-driven planner for your Finnish university studies. Pulls courses
from SISU (Helsinki, Aalto, others), filters them against your goals,
ranks the candidates, and lays out a period-by-period plan you can
validate.

Designed for a one-shot conversation: tell Claude to read the workflow,
fill in a few inputs, get a plan.

---

## What you'll see in this directory

| File | What it is | Who edits it |
|---|---|---|
| `goals.md` | Your career goal, topic priorities, weak areas, constraints, universities you have study rights at, and faculties to exclude. | **You** |
| `course_picks.md` | Claude's curated course selection with rationale, alternates, and trade-offs. | Claude |
| `schedule.yaml` | Period-by-period plan, validated against prerequisites and your ECTS-per-period limit. | Claude |
| `data/` | Raw catalog + transcript artifacts. Don't touch unless asked. | Tools |
| `tools/` | Python scripts that crawl SISU, filter the catalog, validate schedules. Claude runs these. | — |
| `.claude/` | Internal docs and templates Claude reads. Hidden by default. | — |

---

## How to use it

### One-time setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium     # for SISU login
```

### The flow

1. **Edit `goals.md`** — be specific. Career, topic priorities, what you
   already know, what you don't want to study, which universities you can
   register at, and faculties to exclude. The more concrete, the better
   the plan. The `goals.md` shipped with this repo is a real, filled-in
   example — read it for structure, then overwrite the content with your
   own. Don't worry about staying brief: the model reads the whole file.

2. **Open Claude Code in this directory**:
   ```
   cd /path/to/this/repo
   claude
   ```

3. **Tell Claude one thing**:
   ```
   Read .claude/WORKFLOW.md and run the SISU curriculum design flow for me.
   ```

4. **Log in to SISU when prompted.** Claude will launch a browser
   window for each university you have study rights at and ask you to
   sign in. The transcript fetch happens once per university.

5. **Iterate on the picks.** Claude will produce a top-30 candidate
   list and an initial plan in `course_picks.md`. Push back, swap
   courses in/out, ask for justifications. Claude has the full catalog
   in context.

6. **Lock the schedule.** When you're happy with the picks, Claude
   writes `schedule.yaml` and validates it (prereq ordering, credit
   load per period). Edit `schedule.yaml` by hand later if you want.

### Re-running

You can re-open the conversation later — Claude reads `goals.md`,
`course_picks.md`, and `schedule.yaml` and picks up where you left
off. To re-rank from scratch (e.g., your goals changed materially),
ask Claude to re-run from Step 4 of the workflow.

---

## What Claude is allowed to do

- Read every file in this repo.
- Write to `course_picks.md`, `schedule.yaml`, and `data/`.
- Run any script in `tools/`.
- Launch Playwright via `tools/fetch_transcript.py` (the SISU login
  flow).
- Spawn parallel Claude Haiku subagents for the candidate-screening
  step (this is in-session compute, not Anthropic API billing).

It will **not** edit `goals.md` based on inferred preferences — that
file is yours. If your goals change, edit it yourself, then ask Claude
to re-plan.

---

## Common questions

**"Do I need an Anthropic API key?"** No, for the default flow. The
candidate ranking uses in-session Haiku subagents (counts against your
Claude Max usage). If you want to do a comprehensive batch-score over
the whole catalog, `tools/rank.py` uses the Anthropic Batches API and
needs an API key + balance — but that's optional and rarely needed.

**"Can I plan across multiple universities?"** Yes. List them in
`goals.md` under "Universities I can take courses at." Claude restricts
the catalog to those and respects cross-faculty / cross-degree
registration rules you describe.

**"Why aren't all my courses showing up in the catalog?"** The SISU
search API has some silent-failure modes. The workflow already works
around the known ones (narrow code prefixes, no staleness filter), but
if a specific course is missing, tell Claude the code and it'll do a
targeted re-fetch.

**"Can I edit `schedule.yaml` by hand?"** Yes. After any edit, run:
```bash
python tools/schedule.py
```
to revalidate.
