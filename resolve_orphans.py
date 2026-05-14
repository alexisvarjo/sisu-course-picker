#!/usr/bin/env python3
"""
Fetch the 'orphan' courses whose groupIds are referenced by some course's
formalPrerequisites but don't appear in data/courses.jsonl. These are usually
older or out-of-scope courses that were filtered out (staleness, university
allowlist) but are still cited as prereqs.

Each orphan groupId is looked up via
    GET /kori/api/course-units/by-group-id?universityId=...&groupId=...

The university is inferred from the groupId prefix when possible
(`hy-*` → University of Helsinki, `aalto-*` → Aalto, `jy-*` → JYU, ...).
For globally-prefixed `otm-*` groupIds, we try each known university root
until one returns 200.

Output: data/courses_extra.jsonl (same shape as courses.jsonl). Re-running
the prereq graph on (courses.jsonl + courses_extra.jsonl) closes most of the
622 orphan references.
"""

import argparse
import json
import os
import sys
import threading
import urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Re-use the connection-pooling helpers from the ingester
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ingest_catalog import fetch_json, RateLimiter  # noqa: E402


KNOWN_UNIS = {
    "hy": "hy-university-root-id",
    "aalto": "aalto-university-root-id",
    "jy": "jyu-university-root-id",
    "jyu": "jyu-university-root-id",
    "tuni": "tuni-university-root-id",
    "tut": "tuni-university-root-id",  # legacy Tampere prefix
    "uta": "tuni-university-root-id",
    "lut": "lut-university-root-id",
    "lab": "lab-university-root-id",
    "arc": "arc-university-root-id",
    "ha": "ha-university-root-id",
    "shh": "shh-university-root-id",
}

# Universities to try in order for otm-*-prefixed (universal) groupIds.
OTM_FALLBACK_UNIS = [
    "hy-university-root-id",
    "aalto-university-root-id",
    "jyu-university-root-id",
    "tuni-university-root-id",
    "lut-university-root-id",
    "lab-university-root-id",
    "arc-university-root-id",
    "ha-university-root-id",
    "shh-university-root-id",
]


def load_courses(path):
    by_group = {}
    referenced = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            gid = r.get("groupId")
            if gid:
                by_group[gid] = r
            for key in ("compulsoryFormalPrerequisites", "recommendedFormalPrerequisites"):
                for entry in (r.get(key) or []):
                    for p in (entry.get("prerequisites") or []):
                        if p.get("type") == "CourseUnit" and p.get("courseUnitGroupId"):
                            referenced.add(p["courseUnitGroupId"])
    return by_group, referenced


def candidate_unis(group_id):
    prefix = group_id.split("-")[0]
    if prefix == "otm":
        return OTM_FALLBACK_UNIS
    uni = KNOWN_UNIS.get(prefix)
    return [uni] if uni else OTM_FALLBACK_UNIS  # last-resort fallback


def fetch_by_group(group_id, domain, limiter):
    """Try each candidate university. Return the (university, course-list) on success."""
    limiter.wait()
    for uni in candidate_unis(group_id):
        path = (f"/kori/api/course-units/by-group-id?"
                f"universityId={urllib.parse.quote(uni)}"
                f"&groupId={urllib.parse.quote(group_id)}")
        try:
            data = fetch_json(domain, path)
        except Exception:
            continue
        # API returns a list of versions; we want the most recent ACTIVE one.
        if isinstance(data, list) and data:
            active = [c for c in data if c.get("documentState") == "ACTIVE"]
            picked = (sorted(active or data,
                             key=lambda c: (c.get("validityPeriod") or {}).get("startDate") or "")[-1])
            return uni, picked
    return None, None


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--in", dest="in_path", default="data/courses.jsonl")
    ap.add_argument("--out", default="data/courses_extra.jsonl")
    ap.add_argument("--domain", default="sisu.helsinki.fi",
                    help="SISU host to query (federation returns same data).")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--rps", type=float, default=20.0)
    ap.add_argument("--limit", type=int, default=0,
                    help="Resolve at most N orphans (for testing).")
    args = ap.parse_args()

    by_group, referenced = load_courses(args.in_path)
    orphans = sorted(referenced - set(by_group))
    print(f"Catalog: {len(by_group)} courses, {len(referenced)} unique prereq refs.",
          file=sys.stderr)
    print(f"Orphans (referenced but not in catalog): {len(orphans)}", file=sys.stderr)

    # Skip already-resolved
    already_resolved = set()
    if os.path.exists(args.out):
        with open(args.out, encoding="utf-8") as f:
            for line in f:
                try:
                    already_resolved.add(json.loads(line)["groupId"])
                except (json.JSONDecodeError, KeyError):
                    pass
        orphans = [o for o in orphans if o not in already_resolved]
        print(f"Already resolved in {args.out}: {len(already_resolved)}; remaining: {len(orphans)}",
              file=sys.stderr)

    if args.limit:
        orphans = orphans[:args.limit]

    limiter = RateLimiter(args.rps)
    write_lock = threading.Lock()
    resolved = 0
    not_found = 0
    by_prefix = defaultdict(lambda: [0, 0])  # prefix -> [resolved, not_found]

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "a", encoding="utf-8") as fout, \
         ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(fetch_by_group, gid, args.domain, limiter): gid
                   for gid in orphans}
        for fut in as_completed(futures):
            gid = futures[fut]
            prefix = gid.split("-")[0]
            try:
                uni, course = fut.result()
            except Exception as e:
                print(f"  ERROR {gid}: {e}", file=sys.stderr)
                continue
            if course:
                course["_resolved_via"] = uni
                with write_lock:
                    fout.write(json.dumps(course, ensure_ascii=False) + "\n")
                    fout.flush()
                resolved += 1
                by_prefix[prefix][0] += 1
                if resolved % 50 == 0:
                    print(f"  resolved {resolved}/{len(orphans)}", file=sys.stderr)
            else:
                not_found += 1
                by_prefix[prefix][1] += 1

    print(f"\nDone. Resolved: {resolved}  Not found: {not_found}", file=sys.stderr)
    if by_prefix:
        print("By groupId prefix:", file=sys.stderr)
        for p, (r, nf) in sorted(by_prefix.items()):
            print(f"  {p:<8} resolved={r:<5} not_found={nf}", file=sys.stderr)
    print(f"Output: {args.out}", file=sys.stderr)
    print("\nTo include these in the prereq graph, concatenate the two JSONLs:",
          file=sys.stderr)
    print("  cat data/courses.jsonl data/courses_extra.jsonl > /tmp/full.jsonl",
          file=sys.stderr)
    print("  python prereq_graph.py --in /tmp/full.jsonl orphans", file=sys.stderr)


if __name__ == "__main__":
    main()
