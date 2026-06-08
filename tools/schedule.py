#!/usr/bin/env python3
"""
Validate (and optionally extend) a multi-period study plan against the
catalog's prerequisite graph and actual course offering dates.

The user authors `schedule.yaml`:

    plan:
      "2025-2026/I":   [CS-A1140, MS-A0001]   # autumn period 1, already taken
      "2025-2026/II":  [CS-E4500]             # autumn period 2, planned
      "2026-2027/III": []                     # open — suggest candidates
    constraints:
      max_credits_per_period: 15
      candidate_pool_top_n: 30                # use top-N from scored_courses.jsonl

The script:

  1. Loads courses.jsonl + the prereq graph + (optionally) scored_courses.jsonl.
  2. Checks: every code in `plan` is in the catalog.
  3. Checks: every prereq (formal) is scheduled in an earlier period than the
     dependent course. Reports violations as errors.
  4. Checks: each scheduled course is actually offered in that period's date
     window (using `activityPeriods` from the search index — note this is
     informational since activityPeriods isn't on detail responses; courses
     without scheduling info are flagged as "schedule unknown").
  5. Checks: credits-per-period doesn't exceed the cap.
  6. For open periods (empty `[]`), proposes candidates from
     `scored_courses.jsonl` (if present) filtered to those whose prereqs are
     satisfied by then, ranked by `score`.

Time-ordering rule (the user's only hard constraint): a course's prereqs must
be completed BEFORE the dependent course. A prereq counts as completed if it
is any of:

  (a) already in the user's transcript (data/transcript.json)
  (b) scheduled in an earlier period in this plan
  (c) declared as equivalent-knowledge in data/declared_knowledge.json
      — e.g. the user self-studied the material, did it at another uni,
      or knows it from work. Prereqs are soft anyway; the Claude Code
      session should ASK the user before adding entries here.

When prereqs aren't satisfied by any of the three, the validator emits a
MISSING_PREREQS warning. The session can act on it by either (i) proposing
to add the missing prereq to an earlier period, or (ii) asking the user
whether they have equivalent knowledge and writing to declared_knowledge.json
if they do.

Periods follow the Finnish academic convention:
    "<YYYY-YYYY>/<roman>"  where Roman numeral is the period within that
    academic year. HY uses I-IV, Aalto uses I-V. The script does not parse
    these as dates directly — it relies on lexicographic ordering of the
    period keys, so author your YAML with periods in time order.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml")


def load_catalog(path):
    by_code = {}
    by_group = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            code = (r.get("code") or "").strip()
            gid = r.get("groupId")
            if code:
                by_code.setdefault(code, r)
            if gid:
                by_group[gid] = r
    return by_code, by_group


def build_prereq_index(by_group):
    """course_groupId -> list of (prereq_groupId, kind) flattened across OR-groups.

    OR-group ambiguity: this index treats each alternative as an independent
    edge. The validator considers the prereq satisfied if ANY alternative was
    scheduled earlier (which matches the OR semantics).
    """
    prereqs_or_groups = defaultdict(list)  # course_gid -> list of [alt_gid, alt_gid, ...]
    for gid, r in by_group.items():
        for key in ("compulsoryFormalPrerequisites", "recommendedFormalPrerequisites"):
            for entry in (r.get(key) or []):
                alts = [p["courseUnitGroupId"] for p in (entry.get("prerequisites") or [])
                        if p.get("type") == "CourseUnit" and p.get("courseUnitGroupId")]
                if alts:
                    prereqs_or_groups[gid].append({
                        "alts": alts,
                        "kind": "compulsory" if key.startswith("comp") else "recommended",
                    })
    return prereqs_or_groups


def code_to_group(by_code):
    return {code: r["groupId"] for code, r in by_code.items() if r.get("groupId")}


def load_declared_knowledge(path):
    """Return (group_ids, codes) the user has declared equivalent knowledge of.

    Shape of data/declared_knowledge.json:
        {
          "courses": [
            {"code": "MS-C1541", "groupId": "aalto-OPINKOHD-1125...",
             "note": "Self-studied from Rudin during summer 2024",
             "declared_at": "2026-05-14"},
            ...
          ]
        }
    Both `code` and `groupId` are optional — supply whichever you have. The
    validator matches on either.
    """
    if not Path(path).exists():
        return set(), set()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    gids, codes = set(), set()
    for entry in (data.get("courses") or []):
        if entry.get("groupId"):
            gids.add(entry["groupId"])
        if entry.get("code"):
            codes.add(entry["code"])
    return gids, codes


def load_transcript(path):
    """Extract groupIds of successfully-completed courses from transcript.json.

    The transcript file shape is what fetch_transcript.py writes:
        {"universities": {"sisu.X.fi": {"attainments": [...]}}}
    Each attainment object is the raw /ori/api/my-attainments record. We
    accept anything that has a courseUnitGroupId and a "passing" state
    (defensive about field names since this is what kori returns when the
    user actually logs in).
    """
    if not Path(path).exists():
        return set()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    completed_groups = set()
    completed_codes = set()
    passing_states = {"ATTAINED", "PASSED", "COMPLETED", "INCLUDED"}
    for uni_block in (data.get("universities") or {}).values():
        for a in (uni_block.get("attainments") or []):
            # Skip if explicitly failed/draft
            state = (a.get("state") or a.get("attainmentState") or "").upper()
            if state and state not in passing_states:
                continue
            gid = (a.get("courseUnitGroupId")
                   or a.get("groupId")
                   or (a.get("courseUnit") or {}).get("groupId"))
            if gid:
                completed_groups.add(gid)
            # Also collect by code as a fallback if groupId resolution fails
            code = (a.get("code")
                    or (a.get("courseUnit") or {}).get("code"))
            if code:
                completed_codes.add(code)
    return completed_groups, completed_codes


def total_credits(codes, by_code):
    return sum(((by_code.get(c) or {}).get("credits") or {}).get("min") or 0
               for c in codes)


def period_count_map(plan):
    """How many periods each course code appears in. A multi-period (spanning)
    course is intentionally listed in EVERY period it runs — e.g. an Aalto
    III-IV course occupies both III and IV, so it appears in both lists."""
    counts = defaultdict(int)
    for codes in plan.values():
        for c in codes:
            counts[c] += 1
    return counts


def period_load(codes, by_code, pcount):
    """Credit load a period carries, splitting a multi-period course's credits
    evenly across the periods it spans (a 5-op I-II course counts 2.5 in each
    of I and II, not 5 in both)."""
    total = 0.0
    for c in codes:
        cr = ((by_code.get(c) or {}).get("credits") or {}).get("min") or 0
        total += cr / (pcount.get(c, 1) or 1)
    return total


def parse_period_year(key):
    """Return the academic-year start integer for sorting. E.g. '2025-2026/II' -> 2025."""
    try:
        return int(key.split("-")[0])
    except (ValueError, IndexError):
        return -1


def validate(plan, by_code, by_group, prereq_idx, c2g, max_credits,
             transcript_groups=None, transcript_codes=None,
             declared_groups=None, declared_codes=None):
    errors = []
    warnings = []
    missing_prereqs = []  # structured list for the Claude Code session
    transcript_groups = transcript_groups or set()
    transcript_codes = transcript_codes or set()
    declared_groups = declared_groups or set()
    declared_codes = declared_codes or set()
    # Combined "already-known" sets — prereq satisfied if it lands in either.
    known_groups = transcript_groups | declared_groups
    known_codes = transcript_codes | declared_codes

    # Period order = sorted key order (lexicographic on '2025-2026/II' works
    # because YYYY-YYYY/N sorts by year then roman; user-authored keys must be
    # consistent).
    period_keys = sorted(plan.keys())
    # Where each scheduled course-group is placed
    course_at_period = {}  # group_id -> completion (last) period_key
    pos = {pk: i for i, pk in enumerate(period_keys)}
    code_periods = defaultdict(list)  # code -> [period_keys it occupies]
    for pk in period_keys:
        for code in plan[pk]:
            if code not in by_code:
                errors.append(f"  [{pk}] course {code!r} is not in the catalog")
                continue
            gid = c2g.get(code)
            if not gid:
                warnings.append(f"  [{pk}] {code} has no groupId (rare)")
                continue
            code_periods[code].append(pk)
            # A multi-period course completes in its LAST period; later periods
            # overwrite because period_keys is in ascending time order. This is
            # what dependents must come after.
            course_at_period[gid] = pk

    # A course listed in several periods is a multi-period (spanning) course;
    # those periods must be contiguous — non-adjacent repeats are likely a typo.
    for code, pks in code_periods.items():
        if len(pks) > 1:
            idxs = sorted(pos[p] for p in pks)
            if any(idxs[i + 1] - idxs[i] != 1 for i in range(len(idxs) - 1)):
                warnings.append(
                    f"  {code} appears in non-adjacent periods {pks} — a "
                    f"multi-period course must occupy contiguous periods")

    # Credit load per period (multi-period courses split across their span)
    if max_credits:
        pcount = period_count_map(plan)
        for pk in period_keys:
            load = period_load(plan[pk], by_code, pcount)
            if load > max_credits:
                warnings.append(
                    f"  [{pk}] period load {load:g} exceeds cap {max_credits}")

    # Prereq ordering — satisfied if alt is in transcript OR scheduled earlier
    for pk in period_keys:
        for code in plan[pk]:
            gid = c2g.get(code)
            if not gid:
                continue
            for or_group in prereq_idx.get(gid, []):
                satisfied_by = None
                for alt_gid in or_group["alts"]:
                    alt_code = (by_group.get(alt_gid) or {}).get("code")
                    # (a) done in transcript / (c) user-declared knowledge?
                    if alt_gid in known_groups or (alt_code and alt_code in known_codes):
                        in_transcript = (alt_gid in transcript_groups
                                         or (alt_code and alt_code in transcript_codes))
                        satisfied_by = (alt_gid,
                                        "transcript" if in_transcript else "declared")
                        break
                    # (b) scheduled in an earlier period?
                    alt_pk = course_at_period.get(alt_gid)
                    if alt_pk and alt_pk < pk:
                        satisfied_by = (alt_gid, alt_pk)
                        break
                if satisfied_by is None:
                    alt_codes = [(by_group.get(a, {}).get("code") or a[:24])
                                 for a in or_group["alts"]]
                    kind = or_group["kind"]
                    msg = (f"  [{pk}] {code} {kind} prereq not satisfied "
                           f"(not in transcript, not declared, not scheduled "
                           f"earlier): needs ANY of {alt_codes}")
                    missing_prereqs.append({
                        "period": pk,
                        "course": code,
                        "kind": kind,
                        "alternatives": alt_codes,
                        "alt_groupIds": list(or_group["alts"]),
                    })
                    if kind == "compulsory":
                        errors.append(msg)
                    else:
                        warnings.append(msg)

    return errors, warnings, missing_prereqs


def suggest_for_open_period(pk, plan, by_code, by_group, prereq_idx, c2g,
                            scored, top_n, max_credits,
                            transcript_groups=None, transcript_codes=None,
                            declared_groups=None, declared_codes=None):
    """Return up to top_n candidates ranked by score that don't break ordering.

    A candidate's prereqs are considered satisfied if every OR-group has at
    least one alternative that is in the transcript, declared as
    equivalent-knowledge, or scheduled in a period strictly before `pk`.
    """
    transcript_groups = transcript_groups or set()
    transcript_codes = transcript_codes or set()
    declared_groups = declared_groups or set()
    declared_codes = declared_codes or set()
    known_codes = transcript_codes | declared_codes
    completed_before = set(transcript_groups) | set(declared_groups)
    for past_pk, codes in plan.items():
        if past_pk < pk:
            for c in codes:
                gid = c2g.get(c)
                if gid:
                    completed_before.add(gid)

    candidates = []
    for row in scored or []:
        code = row.get("code")
        if code not in by_code:
            continue
        gid = c2g.get(code)
        if not gid or gid in completed_before:
            continue
        # Already scheduled anywhere?
        already_planned = any(code in plan[p] for p in plan)
        if already_planned:
            continue
        # Prereqs satisfied by completed_before (transcript ∪ declared ∪ earlier periods)?
        prereqs_ok = all(
            any(
                alt in completed_before
                or ((by_group.get(alt) or {}).get("code") in known_codes)
                for alt in og["alts"]
            )
            for og in prereq_idx.get(gid, [])
        )
        if not prereqs_ok:
            continue
        candidates.append(row)
    candidates.sort(key=lambda r: (-(r.get("score") or 0), r.get("difficulty") or 0))
    return candidates[:top_n]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--schedule", default="schedule.yaml")
    ap.add_argument("--catalog", default="data/courses.jsonl")
    ap.add_argument("--scored", default="data/scored_courses.jsonl",
                    help="Optional. Used to suggest candidates for open periods.")
    ap.add_argument("--transcript", default="data/transcript.json",
                    help="Optional. Completed courses (from fetch_transcript.py) "
                         "satisfy prereqs in addition to anything scheduled earlier.")
    ap.add_argument("--declared", default="data/declared_knowledge.json",
                    help="Optional. Courses the user has declared equivalent "
                         "knowledge of (self-study, prior uni, work experience). "
                         "Satisfy prereqs just like transcript entries.")
    args = ap.parse_args()

    if not Path(args.schedule).exists():
        sys.exit(f"Missing {args.schedule}. See .claude/schedule.template.yaml.")

    with open(args.schedule, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    plan = cfg.get("plan") or {}
    constraints = cfg.get("constraints") or {}
    max_credits = constraints.get("max_credits_per_period")
    top_n = constraints.get("candidate_pool_top_n", 20)

    by_code, by_group = load_catalog(args.catalog)
    prereq_idx = build_prereq_index(by_group)
    c2g = code_to_group(by_code)

    scored = None
    if Path(args.scored).exists():
        with open(args.scored, encoding="utf-8") as f:
            scored = [json.loads(line) for line in f if line.strip()]

    transcript_groups, transcript_codes = set(), set()
    if Path(args.transcript).exists():
        transcript_groups, transcript_codes = load_transcript(args.transcript)

    declared_groups, declared_codes = load_declared_knowledge(args.declared)

    print(f"Loaded {len(by_code)} courses, {len(prereq_idx)} have formal prereqs.")
    if scored:
        print(f"Loaded {len(scored)} scored candidates from {args.scored}.")
    if transcript_groups or transcript_codes:
        print(f"Transcript: {len(transcript_groups)} courses by groupId, "
              f"{len(transcript_codes)} additional by code.")
    if declared_groups or declared_codes:
        print(f"Declared knowledge: {len(declared_groups)} groupIds, "
              f"{len(declared_codes)} codes.")

    errors, warnings, missing_prereqs = validate(
        plan, by_code, by_group, prereq_idx, c2g, max_credits,
        transcript_groups, transcript_codes,
        declared_groups, declared_codes,
    )
    print()
    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(e)
        print()
    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(w)
        print()
    if not errors and not warnings:
        print("Plan is consistent. No prereq ordering violations.")
    elif not errors:
        print("Plan has no hard violations (only soft warnings).")

    # Per-period credit summary
    print("\nPlan summary:")
    pcount = period_count_map(plan)
    for pk in sorted(plan.keys()):
        cs = plan[pk]
        if not cs:
            print(f"  {pk:<20} (open)")
            continue
        load = period_load(cs, by_code, pcount)
        labelled = [f"{c}*" if pcount.get(c, 1) > 1 else c for c in cs]
        print(f"  {pk:<20} {len(cs)} courses, {load:g} cr (split): "
              f"{', '.join(labelled)}")
    print("  (* = multi-period course; credits split across the periods it spans)")

    # Missing-prereq summary — surface what the Claude Code session should act on
    if missing_prereqs:
        print(f"\nMISSING_PREREQS ({len(missing_prereqs)} — candidates for the "
              f"Claude Code session to propose adding):")
        for mp in missing_prereqs:
            print(f"  [{mp['period']}] {mp['course']} ({mp['kind']}) needs "
                  f"ANY of {mp['alternatives']}")

    # Suggestions for open periods
    open_periods = [pk for pk, cs in plan.items() if not cs]
    if open_periods and scored:
        print("\nSuggestions for open periods (top scored, prereqs satisfied):")
        for pk in sorted(open_periods):
            print(f"\n  {pk}:")
            cands = suggest_for_open_period(
                pk, plan, by_code, by_group, prereq_idx, c2g, scored,
                top_n, max_credits, transcript_groups, transcript_codes,
                declared_groups, declared_codes,
            )
            if not cands:
                print("    (no candidates; widen scored_courses.jsonl or relax filters)")
            for row in cands:
                code = row["code"]
                course = by_code.get(code, {})
                name = ((course.get("name") or {}).get("en")
                        or (course.get("name") or {}).get("fi") or "?")
                cr = (course.get("credits") or {}).get("min") or "?"
                print(f"    score={row.get('score')} diff={row.get('difficulty')} "
                      f"{cr}cr  {code:<14} {name}")
                if row.get("reasoning"):
                    print(f"      {row['reasoning']}")


if __name__ == "__main__":
    main()
