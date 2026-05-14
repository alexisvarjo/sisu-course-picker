#!/usr/bin/env python3
"""
Bulk-rank courses in data/courses.jsonl against the user's stated goals in
goals.md, using Anthropic's Messages Batches API (50% cheaper, ~minutes to ~1h
turnaround). Output is written to data/scored_courses.jsonl, one row per
course with score / difficulty / reasoning.

Why batches: the catalog is large (~13k courses). Scoring it synchronously
would take longer and cost more for no UX benefit — you'll come back to look
at results in a separate Claude Code session.

Prompt caching: the system block (goals + scoring instructions) is the same
across every batch request. We tag it `cache_control: ephemeral`. Cache reads
cost ~10% of fresh input — for 13k courses split into ~1300 batch requests,
this is the difference between cheap and not-cheap.

Usage:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...
    python rank.py                          # default: courses.jsonl + goals.md
    python rank.py --batch-size 8           # courses per request
    python rank.py --resume-batch msgbatch_01...
    python rank.py --check-cost-only        # estimate spend before sending
"""

import argparse
import json
import os
import sys
import textwrap
import time
from pathlib import Path

try:
    import anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
except ImportError:
    sys.exit("pip install anthropic")

MODEL = "claude-opus-4-7"
DEFAULT_GOALS = "goals.md"
DEFAULT_IN = "data/courses.jsonl"
DEFAULT_OUT = "data/scored_courses.jsonl"


INSTRUCTIONS = textwrap.dedent("""\
    You are helping the user design a personal study curriculum at Finnish
    universities (Helsinki, Aalto, and others on the SISU federation).

    For every course below, return one JSON object with these fields:

      - "code":      the course code (string, exactly as given)
      - "score":     integer 0..10. How well the course aligns with the goals
                     and interests stated in the user goals section. 0 = no
                     fit. 5 = tangential. 8+ = directly on path.
      - "difficulty": integer 1..5. Estimate from the course content depth and
                     the listed prerequisites:
                       1 = introductory, no prereqs
                       2 = bachelor's, light prereqs
                       3 = upper bachelor / early master's
                       4 = master's level, real prereqs assumed
                       5 = advanced master's / doctoral, strong prereqs
                     Prereqs are SOFT (not enforced at enrolment), but their
                     content reveals the assumed-knowledge ceiling. Example:
                     "probability with measure theory" prereq → grad-level
                     probability course. Same name without that prereq → intro.
      - "reasoning": one to three short sentences. Anchor in the course
                     CONTENT/OUTCOMES, not the name (course names in this
                     system are often vague). Explain what makes it a hit or
                     miss for the user's stated goals. Mention prereqs only
                     if they materially change the level.
      - "language":  one of "en", "fi", "sv", or "mixed", based on the
                     possibleAttainmentLanguages and the course description
                     language.

    Output rules:
      - Return a single JSON array containing one object per input course, in
        the same order.
      - No prose, no markdown, no commentary outside the JSON.
      - If a course has no description at all, set score=0 and reasoning
        explaining that (do not guess).
      - Be honest about misalignment. The user wants signal, not flattery.

    The user goals are below. Read them carefully — they govern every score.
""")


def load_goals(path):
    if not Path(path).exists():
        sys.exit(f"  Missing {path}. Create it (see goals.template.md) and re-run.")
    return Path(path).read_text(encoding="utf-8")


def load_catalog(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def existing_scored(path):
    seen = set()
    if not os.path.exists(path):
        return seen
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                seen.add(json.loads(line)["code"])
            except (json.JSONDecodeError, KeyError):
                pass
    return seen


def compact_course_text(c):
    """Render one course as a compact block for the prompt.

    We strip HTML tags from the i18n fields (kori serves descriptions as HTML)
    and prefer English, falling back to Finnish then Swedish.
    """
    def pick(loc, *keys):
        for k in keys:
            v = (loc or {}).get(k)
            if v:
                return v.strip()
        return ""

    def strip_html(s):
        # Cheap tag stripper — these descriptions are short and well-formed.
        import re
        s = re.sub(r"<br\s*/?>", "\n", s)
        s = re.sub(r"</p>\s*<p>", "\n\n", s)
        s = re.sub(r"<[^>]+>", "", s)
        return s.strip()

    name = pick(c.get("name"), "en", "fi", "sv") or "(no name)"
    content = strip_html(pick(c.get("content"), "en", "fi", "sv"))
    outcomes = strip_html(pick(c.get("outcomes"), "en", "fi", "sv"))
    prereqs = strip_html(pick(c.get("prerequisites"), "en", "fi", "sv"))
    credits = (c.get("credits") or {}).get("min")
    langs = ",".join(urn.rsplit(":", 1)[-1]
                     for urn in (c.get("possibleAttainmentLanguages") or []))

    parts = [f"code: {c.get('code')}", f"name: {name}"]
    if credits:
        parts.append(f"credits: {credits}")
    if langs:
        parts.append(f"languages: {langs}")
    if content:
        parts.append(f"content:\n{content}")
    if outcomes:
        parts.append(f"outcomes:\n{outcomes}")
    if prereqs:
        parts.append(f"prerequisites:\n{prereqs}")
    return "\n".join(parts)


def build_batch_requests(courses, goals_text, batch_size):
    system_blocks = [
        {"type": "text", "text": INSTRUCTIONS},
        {"type": "text",
         "text": "# User goals\n\n" + goals_text,
         "cache_control": {"type": "ephemeral"}},
    ]

    requests = []
    for i in range(0, len(courses), batch_size):
        chunk = courses[i:i + batch_size]
        user_text = (
            f"Score these {len(chunk)} courses. Return one JSON array.\n\n"
            + "\n\n---\n\n".join(compact_course_text(c) for c in chunk)
        )
        requests.append(Request(
            custom_id=f"chunk-{i//batch_size:05d}",
            params=MessageCreateParamsNonStreaming(
                model=MODEL,
                max_tokens=4096,
                system=system_blocks,
                messages=[{"role": "user", "content": user_text}],
            ),
        ))
    return requests


def estimate_cost(client, requests):
    """Crude token-count estimate using count_tokens on the first request."""
    if not requests:
        return None
    sample = requests[0].params
    try:
        ct = client.messages.count_tokens(
            model=sample["model"],
            system=sample["system"],
            messages=sample["messages"],
        )
        input_per_request = ct.input_tokens
    except Exception as e:
        return f"Couldn't count tokens: {e}"
    cached = sum(len(b.get("text", "")) // 4 for b in sample["system"]
                 if b.get("cache_control"))
    fresh = max(input_per_request - cached, 0)

    # Batch pricing = 50% off list. Opus 4.7: $5/M input, $25/M output, $0.50/M cache read.
    opus = {"in": 5.0, "out": 25.0, "cache_read": 0.50, "cache_write": 6.25}
    n = len(requests)
    write_once = cached * opus["cache_write"] / 1_000_000 * 0.5
    read_each = cached * opus["cache_read"] / 1_000_000 * 0.5
    fresh_each = fresh * opus["in"] / 1_000_000 * 0.5
    out_each = 800 * opus["out"] / 1_000_000 * 0.5  # ~800 output tokens guess
    per_req = read_each + fresh_each + out_each
    total = write_once + per_req * n
    return (f"{n} requests | per-request ~{int(input_per_request)} input tokens "
            f"(~{int(cached)} cached, ~{int(fresh)} fresh) | "
            f"estimated batch cost: ~${total:.2f} (Opus 4.7, 50% batch discount)")


def parse_response(response_message):
    """Extract the JSON array from one batch result message."""
    text = "".join(b.text for b in response_message.content if b.type == "text").strip()
    # Tolerate models that wrap in ```json
    if text.startswith("```"):
        text = text.strip("`")
        text = text.lstrip("json").lstrip("\n")
        text = text.rstrip("`").strip()
    return json.loads(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--goals", default=DEFAULT_GOALS)
    ap.add_argument("--in", dest="in_path", default=DEFAULT_IN)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--batch-size", type=int, default=8,
                    help="Courses per API request. Smaller = more reliable parsing, "
                         "more requests; larger = cheaper, slightly riskier.")
    ap.add_argument("--limit", type=int, default=0,
                    help="Stop after N courses (for testing).")
    ap.add_argument("--check-cost-only", action="store_true",
                    help="Print cost estimate and exit without creating a batch.")
    ap.add_argument("--resume-batch",
                    help="Retrieve results for an existing msgbatch_... id and "
                         "write to --out. Skips batch creation.")
    ap.add_argument("--poll-interval", type=int, default=30,
                    help="Seconds between status polls.")
    args = ap.parse_args()

    client = anthropic.Anthropic()
    goals_text = load_goals(args.goals)
    courses = load_catalog(args.in_path)
    already_done = existing_scored(args.out)
    if already_done:
        before = len(courses)
        courses = [c for c in courses if c.get("code") not in already_done]
        print(f"Resume: skipping {before - len(courses)} courses already in {args.out}",
              file=sys.stderr)
    if args.limit:
        courses = courses[:args.limit]
    if not courses and not args.resume_batch:
        print("Nothing to do — every course is already scored.", file=sys.stderr)
        return

    if args.resume_batch:
        batch_id = args.resume_batch
    else:
        requests = build_batch_requests(courses, goals_text, args.batch_size)
        print(estimate_cost(client, requests), file=sys.stderr)
        if args.check_cost_only:
            return
        confirm = input(f"\nCreate batch with {len(requests)} requests? [y/N] ")
        if confirm.lower() not in ("y", "yes"):
            print("Aborted.", file=sys.stderr)
            return
        batch = client.messages.batches.create(requests=requests)
        batch_id = batch.id
        print(f"\nCreated batch {batch_id}. Status: {batch.processing_status}",
              file=sys.stderr)
        print(f"Re-run with --resume-batch {batch_id} if this script dies.",
              file=sys.stderr)

    # Poll
    print(f"\nPolling {batch_id} every {args.poll_interval}s...", file=sys.stderr)
    while True:
        b = client.messages.batches.retrieve(batch_id)
        rc = b.request_counts
        print(f"  status={b.processing_status} "
              f"processing={rc.processing} succeeded={rc.succeeded} "
              f"errored={rc.errored} cancelled={rc.canceled} expired={rc.expired}",
              file=sys.stderr)
        if b.processing_status == "ended":
            break
        time.sleep(args.poll_interval)

    # Stream results
    written = 0
    parse_failures = 0
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "a", encoding="utf-8") as fout:
        for result in client.messages.batches.results(batch_id):
            if result.result.type != "succeeded":
                print(f"  [{result.custom_id}] {result.result.type}", file=sys.stderr)
                continue
            try:
                rows = parse_response(result.result.message)
            except Exception as e:
                parse_failures += 1
                print(f"  [{result.custom_id}] parse failed: {e}", file=sys.stderr)
                continue
            for row in rows:
                fout.write(json.dumps(row, ensure_ascii=False) + "\n")
                written += 1

    print(f"\nWrote {written} rows to {args.out}. Parse failures: {parse_failures}",
          file=sys.stderr)
    print("\nNext: run `claude` in this directory to iterate on the curriculum "
          "with the scored results.", file=sys.stderr)


if __name__ == "__main__":
    main()
