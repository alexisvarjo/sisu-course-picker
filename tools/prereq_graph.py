#!/usr/bin/env python3
"""
Prerequisite graph from `data/courses.jsonl`.

Edges come from each course's `recommendedFormalPrerequisites` and
`compulsoryFormalPrerequisites` arrays. SISU encodes alternatives as OR-groups
(one inner `prerequisites` list = "any one of these satisfies it"); this script
preserves the OR semantics so you can tell "must do exactly this one" from
"any of {A, B, C}".

Usage:
    python prereq_graph.py before CS-A1140                # ancestors
    python prereq_graph.py after  CS-A1140                # descendants
    python prereq_graph.py chain  CS-A1140 --depth 3      # text tree
    python prereq_graph.py export --format dot > g.dot    # full graph
    python prereq_graph.py orphans                        # courses whose prereq
                                                          #   refs miss our catalog

Edge types: `compulsory` (hard rule on paper) or `recommended` (soft).
Compulsory prereqs are soft in practice at Finnish unis — the system rarely
enforces them at enrolment — but the *content* still assumes them. We surface
both, marked so you can decide.
"""

import argparse
import json
import sys
from collections import defaultdict


def load_catalog(path):
    """Return {groupId: course_record} and a code->groupId lookup."""
    by_group = {}
    code_to_group = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            gid = r.get("groupId")
            if gid:
                by_group[gid] = r
                code = (r.get("code") or "").strip()
                if code:
                    # If duplicate codes (different unis), keep the first; warn quietly.
                    code_to_group.setdefault(code, gid)
    return by_group, code_to_group


def build_edges(by_group):
    """Build forward and backward adjacencies. Each edge has an or_group key.

    forward[prereq_gid] -> list of (course_gid, kind, or_group_id, alternatives)
        kind: 'compulsory' or 'recommended'
        or_group_id: stable id within the course, distinguishes OR-groups
        alternatives: tuple of all groupIds that share this OR-group (so caller
                      can show "or any of these")
    backward[course_gid] -> list of (prereq_gid, kind, or_group_id, alternatives)
    """
    forward = defaultdict(list)
    backward = defaultdict(list)
    skipped_module = 0
    for course_gid, r in by_group.items():
        for kind, key in [("compulsory", "compulsoryFormalPrerequisites"),
                          ("recommended", "recommendedFormalPrerequisites")]:
            for i, entry in enumerate(r.get(key) or []):
                prereqs = entry.get("prerequisites") or []
                cu_prereqs = [p for p in prereqs if p.get("type") == "CourseUnit"]
                # Count module-type prereqs but don't add them as edges (different
                # ID namespace; not in courses.jsonl).
                skipped_module += sum(1 for p in prereqs if p.get("type") == "Module")
                or_group_id = f"{kind}-{i}"
                alts = tuple(p["courseUnitGroupId"] for p in cu_prereqs
                             if p.get("courseUnitGroupId"))
                for p in cu_prereqs:
                    pgid = p.get("courseUnitGroupId")
                    if not pgid:
                        continue
                    forward[pgid].append((course_gid, kind, or_group_id, alts))
                    backward[course_gid].append((pgid, kind, or_group_id, alts))
    return forward, backward, skipped_module


def resolve_target(code_or_gid, by_group, code_to_group):
    """Return the groupId of a course given either its code or its groupId."""
    if code_or_gid in by_group:
        return code_or_gid
    # Case-insensitive code lookup
    for code, gid in code_to_group.items():
        if code.lower() == code_or_gid.lower():
            return gid
    sys.exit(f"  Course '{code_or_gid}' not found by code or groupId.")


def fmt_course(by_group, gid, marker=""):
    r = by_group.get(gid)
    if not r:
        return f"{marker}? {gid}  (NOT IN CATALOG)"
    code = r.get("code") or "?"
    name = (r.get("name") or {}).get("en") or (r.get("name") or {}).get("fi") or "?"
    cr = (r.get("credits") or {}).get("min")
    cr_str = f"{cr}cr" if cr else ""
    return f"{marker}{code:<14} {cr_str:<5} {name}"


def print_chain(gid, neighbours, by_group, max_depth, direction_word,
                indent=0, visited=None):
    if visited is None:
        visited = set()
    if indent == 0:
        print(fmt_course(by_group, gid))
    if indent >= max_depth:
        return
    if gid in visited:
        print("  " * (indent + 1) + "(cycle)")
        return
    visited = visited | {gid}
    # Group by or_group_id so OR-alternatives are listed under one heading
    by_or = defaultdict(list)
    for other_gid, kind, or_id, alts in neighbours.get(gid, []):
        by_or[(kind, or_id, alts)].append(other_gid)

    for (kind, or_id, alts), gids in by_or.items():
        kind_marker = "[C]" if kind == "compulsory" else "[r]"
        if len(alts) > 1:
            print("  " * (indent + 1) + f"{kind_marker} {direction_word} ANY OF:")
            for g in alts:
                print("  " * (indent + 2) + fmt_course(by_group, g))
                print_chain(g, neighbours, by_group, max_depth, direction_word,
                            indent + 2, visited)
        else:
            for g in gids:
                print("  " * (indent + 1) + f"{kind_marker} {fmt_course(by_group, g)}")
                print_chain(g, neighbours, by_group, max_depth, direction_word,
                            indent + 1, visited)


def cmd_before(args, by_group, code_to_group, forward, backward):
    gid = resolve_target(args.code, by_group, code_to_group)
    print_chain(gid, backward, by_group, args.depth, "needs")


def cmd_after(args, by_group, code_to_group, forward, backward):
    gid = resolve_target(args.code, by_group, code_to_group)
    print_chain(gid, forward, by_group, args.depth, "unlocks")


def cmd_chain(args, by_group, code_to_group, forward, backward):
    # Show both directions
    gid = resolve_target(args.code, by_group, code_to_group)
    if backward.get(gid):
        print("=== Prerequisites (what to do first) ===")
        print_chain(gid, backward, by_group, args.depth, "needs")
    else:
        print(f"=== {fmt_course(by_group, gid)} ===")
        print("(no formal prerequisites listed)")
    if forward.get(gid):
        print()
        print("=== Unlocks (what this is a prereq for) ===")
        print_chain(gid, forward, by_group, args.depth, "unlocks")


def cmd_orphans(args, by_group, code_to_group, forward, backward):
    """List courses whose listed prereqs are not in our catalog."""
    bad = []
    for gid, edges in backward.items():
        missing = [pgid for pgid, *_ in edges if pgid not in by_group]
        if missing:
            bad.append((gid, missing))
    print(f"Found {len(bad)} courses with at least one prereq not in courses.jsonl.")
    print("(Likely: prereq lives at a non-HY/Aalto uni, was filtered as stale, "
          "or was discontinued.)\n")
    for gid, missing in bad[:args.limit]:
        print(fmt_course(by_group, gid))
        for pgid in missing:
            print(f"    missing: {pgid}")
    if len(bad) > args.limit:
        print(f"\n... and {len(bad) - args.limit} more (raise --limit to see all)")


def cmd_export(args, by_group, code_to_group, forward, backward):
    nodes_used = set()
    edges = []  # (src_gid, dst_gid, kind, or_group)
    for course_gid, prereqs in backward.items():
        for pgid, kind, or_id, alts in prereqs:
            edges.append((pgid, course_gid, kind, or_id))
            nodes_used.add(course_gid)
            nodes_used.add(pgid)

    if args.format == "json":
        out = {"nodes": [], "edges": []}
        for gid in nodes_used:
            r = by_group.get(gid, {})
            out["nodes"].append({
                "groupId": gid,
                "code": r.get("code"),
                "name": (r.get("name") or {}).get("en") or (r.get("name") or {}).get("fi"),
                "credits": (r.get("credits") or {}).get("min"),
                "in_catalog": gid in by_group,
            })
        for src, dst, kind, or_id in edges:
            out["edges"].append({"from": src, "to": dst, "kind": kind, "or_group": or_id})
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        print()
    elif args.format == "dot":
        print("digraph prereq {")
        print('  rankdir=LR; node [shape=box, fontname="Helvetica"];')
        for gid in nodes_used:
            r = by_group.get(gid, {})
            code = r.get("code") or "?"
            label = code if r else f"{code}\\n(not in catalog)"
            style = "" if r else ', style=dashed, color=gray'
            print(f'  "{gid}" [label="{label}"{style}];')
        for src, dst, kind, _ in edges:
            style = "" if kind == "compulsory" else ', style=dashed'
            print(f'  "{src}" -> "{dst}" [color={"black" if kind=="compulsory" else "gray"}'
                  f'{style}];')
        print("}")
    else:
        sys.exit(f"Unknown --format {args.format!r}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="in_path", default="data/courses.jsonl",
                    help="Input JSONL from ingest_catalog.py")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_before = sub.add_parser("before", help="Show prereq chain (what comes first)")
    p_before.add_argument("code")
    p_before.add_argument("--depth", type=int, default=4)
    p_before.set_defaults(func=cmd_before)

    p_after = sub.add_parser("after", help="Show descendants (what this unlocks)")
    p_after.add_argument("code")
    p_after.add_argument("--depth", type=int, default=4)
    p_after.set_defaults(func=cmd_after)

    p_chain = sub.add_parser("chain", help="Show both directions in one view")
    p_chain.add_argument("code")
    p_chain.add_argument("--depth", type=int, default=3)
    p_chain.set_defaults(func=cmd_chain)

    p_orph = sub.add_parser("orphans",
                             help="Courses whose prereqs reference IDs not in catalog")
    p_orph.add_argument("--limit", type=int, default=30)
    p_orph.set_defaults(func=cmd_orphans)

    p_exp = sub.add_parser("export", help="Dump the whole graph")
    p_exp.add_argument("--format", choices=["dot", "json"], default="json")
    p_exp.set_defaults(func=cmd_export)

    args = ap.parse_args()
    by_group, code_to_group = load_catalog(args.in_path)
    forward, backward, skipped_module = build_edges(by_group)
    print(f"Loaded {len(by_group)} courses; "
          f"{sum(len(v) for v in backward.values())} prereq edges; "
          f"{skipped_module} module-type prereqs skipped.\n",
          file=sys.stderr)
    args.func(args, by_group, code_to_group, forward, backward)


if __name__ == "__main__":
    main()
