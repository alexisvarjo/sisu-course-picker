# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

# Project: SISU Curriculum Designer

A personal study-curriculum planner over the Finnish SISU university federation
(University of Helsinki + Aalto by default; ~9 universities reachable). The
goal is to pick high-value courses against the user's stated goals, sequence
them respecting prerequisites, and lay them out across academic periods.

## Data files (keep these in mind when the user asks anything)

| Path | What | When it exists |
|---|---|---|
| `data/courses.jsonl` | Full catalog crawled from `kori` API. One full course-unit detail per line. The authoritative source for course content, outcomes, prereqs, credits, organisations. | After `python tools/ingest_catalog.py` |
| `data/courses.jsonl.gz` | Compressed shipping copy (~15 MB). | Optional |
| `data/courses_extra.jsonl` | Courses resolved from orphan prereq references (older versions, out-of-scope universities). Same schema as `courses.jsonl`. | After `python tools/resolve_orphans.py` |
| `data/transcript.json` | User's completed courses, keyed by university (one block per SISU instance). | After `python tools/fetch_transcript.py --domain X` |
| `data/declared_knowledge.json` | User-declared equivalent-knowledge courses (self-study, work, prior uni). Satisfies prereqs without re-taking. | User-curated; see `.claude/declared_knowledge.template.json` |
| `data/scored_courses.jsonl` | LLM-scored subset. One row per course: `{code, score, difficulty, reasoning, language}`. | After `python tools/rank.py` |
| `data/_orgs.json` | Cached `/kori/api/organisations` tree (for `tools/filter_courses.py`). | Auto-cached |
| `goals.md` | User-authored: career goal, interest areas, things to avoid, current level, constraints. | User writes; treat the existing `goals.md` as the structural example |
| `schedule.yaml` | Period-by-period plan. The validator enforces ONE rule: prereqs scheduled before dependents. | User writes (see `.claude/schedule.template.yaml`) |

## Helper scripts available

- `tools/ingest_catalog.py` — refresh the catalog. Defaults to HY + Aalto with academic-year staleness filter.
- `tools/filter_courses.py --list-orgs --root <uni-id>` — browse the org tree with course counts.
- `tools/filter_courses.py --blacklist-org-name "law" "medicine" --out data/filtered.jsonl` — drop branches you don't care about.
- `tools/prereq_graph.py before|after|chain <CODE>` — show prereq chain for a course.
- `tools/prereq_graph.py orphans` — list courses whose prereqs reference IDs not in catalog (~600). Run `tools/resolve_orphans.py` to fix.
- `tools/fetch_transcript.py --domain sisu.helsinki.fi` — Playwright login → pull completed courses. Re-run per university.
- `tools/rank.py` — **OPTIONAL.** Bulk LLM scoring via Anthropic Batches API. Requires `ANTHROPIC_API_KEY` and API balance (separate from Claude Max subscription). Not part of the default workflow — ranking normally happens in-session.
- `tools/schedule.py` — validate `schedule.yaml`. Reports prereq ordering violations and credits-per-period issues. Suggests candidates for empty periods from `scored_courses.jsonl`.
- `tools/resolve_orphans.py` — fetch missing-prereq courses from SISU and write to `data/courses_extra.jsonl`.

## Ranking and curriculum design (in-session)

**The user runs on Claude Max alone — no separate API balance.** That means ranking does NOT happen via `tools/rank.py` by default (`tools/rank.py` bills against API credits, not the Max subscription). Instead, ranking happens through *this* Claude Code session.

**Don't try to score all ~13k courses.** That's wasteful even on Max. The intended workflow:

1. **Pre-filter the catalog first.** Before any scoring, narrow `data/courses.jsonl` down to a manageable candidate set using `tools/filter_courses.py`:
   - Drop irrelevant faculties (`--blacklist-org-name "law" "medicine" ...`)
   - Restrict by language (`--keep-attainment-language en`)
   - Restrict by code prefix if the user has strong domain focus
   - Target output size: ~500–2,000 courses.

2. **Semantic browse, not exhaustive scoring.** Read `goals.md`. Pull out the key concepts. Use `grep` over the filtered JSONL to find courses whose `content` / `outcomes` mention those concepts. Read the top ~50–100 matches in detail (full `Read` of their entry).

3. **Score the candidates that survive.** For each course you actually read, write a row to `data/scored_courses.jsonl` with `{code, score (0–10), difficulty (1–5), reasoning, language}`. Anchor reasoning in the description, not the name.

4. **Iterate with the user.** Show top candidates, ask which directions resonate, refine. Use `prereq_graph.py before <code>` to map prereq chains.

When the user has the patience and budget for a comprehensive score-everything pass, point them at `tools/rank.py` — but flag that it requires `ANTHROPIC_API_KEY` and an API balance.

## Helping the user iterate on their curriculum

When the user opens a Claude Code session here, expect requests like:

- *"What are the top 30 from scored_courses.jsonl that I haven't done yet?"*
  → Read `data/scored_courses.jsonl` and `data/transcript.json`, filter, sort by score.
- *"Why is CS-E4500 scored so low?"*
  → Grep `data/scored_courses.jsonl` for the code; show the `reasoning` field. Cross-check against the course's `content` in `data/courses.jsonl`.
- *"Add MS-A0001 to autumn 2025 period I"*
  → Edit `schedule.yaml`, then run `python tools/schedule.py` to validate.
- *"What does CS-E4500 need beforehand?"*
  → Run `python tools/prereq_graph.py before CS-E4500`. Cross-reference results against the user's transcript and `data/declared_knowledge.json`.
- *"Build me a 4-period plan that gets me toward goal X"*
  → Read goals + scored + prereq graph. Propose a plan as YAML diff. Don't write to disk until the user confirms.

### When `tools/schedule.py` reports MISSING_PREREQS

Don't treat it as a hard failure — prereqs are SOFT. Walk the user through each missing prereq:

1. **Look up what the prereq actually covers** — read its `content` and `outcomes` fields from `data/courses.jsonl`. Don't rely on the code or name alone.
2. **Ask the user, in concrete terms**: "Course X needs [topic] as a prereq. Have you covered this — through self-study, prior coursework not in your SISU transcript, work experience, MOOCs, etc.?" Be specific about what knowledge the prereq actually represents.
3. **If they say yes**: add an entry to `data/declared_knowledge.json` with the prereq's `code`, `groupId`, a one-line `note` capturing how/when they learned it, and `declared_at` (today's date). Read the existing file first; append, don't overwrite.
4. **If they say no, but want to learn it**: propose adding the prereq to an earlier period in `schedule.yaml`. Check the prereq's own prereqs (recursively) before doing this — you might be uncovering a chain.
5. **If they say no and don't want to take it**: leave the warning as-is. The course goes on the plan without the prereq; the user knows what they're doing.

Never silently add to `declared_knowledge.json` based on inference. Always ASK.

## Important rules from earlier conversations

- **Description fields matter most.** Course names are often vague ("Special Course in X"). Always anchor rationale in `content`, `outcomes`, `prerequisites` — not the name.
- **Prereqs are SOFT.** SISU doesn't enforce them at enrolment. Treat them as (a) sequencing signal, (b) difficulty signal ("probability with measure theory" prereq → grad-level), and (c) a conversation starter: when validation flags a missing prereq, ASK the user whether they have equivalent knowledge from outside SISU before assuming it's a gap. Never use prereqs to hide courses from the user.
- **Don't gatekeep by eligibility.** The user knows best whether they can take a course. Surface options; don't filter by their current programme.
- **Multi-uni is real.** A student can be enrolled at HY and Aalto simultaneously. Transcript merges; the catalog is federated.
- **Schedule constraint = ordering only.** The only hard rule the user has stated: a prereq must complete in an earlier period than its dependent. No credit cap, no language filter, nothing else is enforced by default.
- **Don't write files to `data/` unless the user asks.** Especially: don't overwrite `goals.md` or `schedule.yaml` based on inferred preferences. Propose diffs first.
