#!/usr/bin/env python3
"""
Narrow down `data/courses.jsonl` by organisation blacklist, keyword, code prefix,
language, etc. — *before* feeding the catalog to the LLM ranker, so we don't
spend tokens on stuff the student already knows is irrelevant.

Two modes:

  1. --list-orgs : print a hierarchical tree of organisations with course
     counts. Use to find the IDs (or name patterns) to blacklist.

  2. (default)   : read `--in` JSONL, drop courses matching any blacklist,
     write `--out` JSONL. Blacklists are unions: a course is dropped if
     *any* filter matches. Within --blacklist-org, descendants of listed
     org IDs are also blacklisted (so blacklisting a faculty drops every
     programme/department under it).

Examples:

  # See HY's org tree with course counts
  python filter_courses.py --list-orgs --root hy-university-root-id

  # Search org names for "law" or "medicine"
  python filter_courses.py --list-orgs --search "law|medic"

  # Drop everything organised by the HY Faculty of Law and the HY Faculty
  # of Medicine, plus anything whose code starts with PROV (pharmacy):
  python filter_courses.py \\
      --blacklist-org hy-org-116720455 hy-org-... \\
      --blacklist-code-prefix PROV \\
      --out data/courses_filtered.jsonl
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
from collections import Counter, defaultdict
from typing import Iterable

# Re-use the http-client helpers from the ingester so we don't open a fresh TLS
# session per request.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ingest_catalog import fetch_json  # noqa: E402


ORGS_CACHE = "data/_orgs.json"
DEFAULT_DOMAIN = "sisu.helsinki.fi"


def load_orgs(domain=DEFAULT_DOMAIN, force_refresh=False):
    """Return the full list of organisations (cached on disk after first fetch)."""
    if not force_refresh and os.path.exists(ORGS_CACHE):
        with open(ORGS_CACHE, encoding="utf-8") as f:
            return json.load(f)
    print(f"Fetching org tree from https://{domain}/kori/api/organisations ...",
          file=sys.stderr)
    data = fetch_json(domain, "/kori/api/organisations")
    os.makedirs(os.path.dirname(ORGS_CACHE) or ".", exist_ok=True)
    with open(ORGS_CACHE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"Cached {len(data)} orgs to {ORGS_CACHE}", file=sys.stderr)
    return data


def build_tree(orgs):
    by_id = {o["id"]: o for o in orgs}
    children = defaultdict(list)
    for o in orgs:
        children[o.get("parentId")].append(o["id"])
    return by_id, children


def descendants(root_id, children):
    seen = {root_id}
    stack = [root_id]
    while stack:
        for c in children.get(stack.pop(), []):
            if c not in seen:
                seen.add(c)
                stack.append(c)
    return seen


def course_org_counts(jsonl_path):
    counts = Counter()
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            for entry in r.get("organisations") or []:
                oid = entry.get("organisationId") if isinstance(entry, dict) else entry
                if oid:
                    counts[oid] += 1
    return counts


def org_label(org, lang_order=("en", "fi", "sv")):
    name = org.get("name") or {}
    for lang in lang_order:
        if name.get(lang):
            return name[lang]
    return "?"


def print_tree(roots, children, by_id, counts, search_re=None, depth=0,
               include_zero=False):
    """Recursive tree print, sorted by descendant course count.

    If search_re is set, every node is shown but matching nodes are highlighted.
    Otherwise zero-count branches are pruned (unless --include-zero).
    """
    def desc_count(oid):
        return sum(counts.get(d, 0) for d in descendants(oid, children))

    for oid in sorted(roots, key=lambda x: -desc_count(x)):
        org = by_id.get(oid)
        if not org:
            continue
        label = org_label(org)
        sub_total = desc_count(oid)
        own = counts.get(oid, 0)
        match = bool(search_re and search_re.search(label))
        if not include_zero and sub_total == 0 and not match:
            continue
        marker = "*" if match else " "
        prefix = "  " * depth
        print(f"{marker} [{sub_total:>5} | own:{own:>4}] {prefix}{oid:<42}  {label}")
        print_tree(children.get(oid, []), children, by_id, counts,
                   search_re=search_re, depth=depth + 1, include_zero=include_zero)


def list_orgs_cmd(args):
    orgs = load_orgs(force_refresh=args.refresh_orgs)
    by_id, children = build_tree(orgs)
    counts = course_org_counts(args.in_path) if os.path.exists(args.in_path) \
             else Counter()
    if not counts:
        print(f"(No courses.jsonl at {args.in_path}; showing tree without counts.)",
              file=sys.stderr)
    search_re = re.compile(args.search, re.IGNORECASE) if args.search else None

    # Roots: either user-supplied --root values or all top-level orgs (parent=None)
    roots = args.root or children.get(None, [])
    print("\nLegend: [descendant-course-total | own-course-total] org-id  name\n"
          "(zero-count branches hidden unless --include-zero; '*' = matched --search)\n",
          file=sys.stderr)
    print_tree(roots, children, by_id, counts,
               search_re=search_re, include_zero=args.include_zero)


def filter_cmd(args):
    by_id, children = (None, None)
    blacklist_org_ids: set = set()
    if args.blacklist_org or args.blacklist_org_name:
        orgs = load_orgs(force_refresh=args.refresh_orgs)
        by_id, children = build_tree(orgs)
        for oid in args.blacklist_org:
            if oid not in by_id:
                print(f"WARN: --blacklist-org '{oid}' is not a known org id", file=sys.stderr)
            blacklist_org_ids |= descendants(oid, children)
        if args.blacklist_org_name:
            pat = re.compile("|".join(args.blacklist_org_name), re.IGNORECASE)
            for oid, o in by_id.items():
                if pat.search(org_label(o)):
                    blacklist_org_ids |= descendants(oid, children)
        print(f"Blacklist resolves to {len(blacklist_org_ids)} org IDs "
              f"(including descendants).", file=sys.stderr)

    code_prefixes = tuple(args.blacklist_code_prefix) if args.blacklist_code_prefix else ()
    keep_languages = set(args.keep_attainment_language) if args.keep_attainment_language else None

    kept = 0
    dropped = {"org": 0, "code": 0, "language": 0}
    if not args.out:
        sys.exit("--out is required when applying filters (or use --list-orgs).")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.in_path, encoding="utf-8") as fin, \
         open(args.out, "w", encoding="utf-8") as fout:
        for line in fin:
            r = json.loads(line)

            # Org filter
            if blacklist_org_ids:
                course_orgs = {
                    e.get("organisationId") for e in (r.get("organisations") or [])
                    if isinstance(e, dict)
                }
                if course_orgs & blacklist_org_ids:
                    dropped["org"] += 1
                    continue

            # Code-prefix filter
            code = r.get("code") or ""
            if code_prefixes and code.startswith(code_prefixes):
                dropped["code"] += 1
                continue

            # Language filter (attainment languages — URN format)
            if keep_languages:
                langs = {urn.rsplit(":", 1)[-1] for urn in
                         (r.get("possibleAttainmentLanguages") or [])}
                if langs and not (langs & keep_languages):
                    dropped["language"] += 1
                    continue

            fout.write(line)
            kept += 1

    print(f"\nKept   : {kept}")
    print(f"Dropped: org={dropped['org']}  code={dropped['code']}  "
          f"language={dropped['language']}")
    print(f"Wrote  : {args.out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="in_path", default="data/courses.jsonl",
                    help="Input JSONL from ingest_catalog.py")
    ap.add_argument("--out", help="Output JSONL (required for filter mode)")
    ap.add_argument("--refresh-orgs", action="store_true",
                    help="Re-fetch organisation tree (default: use cache).")

    g_list = ap.add_argument_group("list-orgs mode")
    g_list.add_argument("--list-orgs", action="store_true",
                        help="Print org tree with course counts and exit.")
    g_list.add_argument("--root", nargs="*", default=None,
                        help="Org IDs to use as tree roots. Default: all top-level "
                             "(university roots).")
    g_list.add_argument("--search",
                        help="Highlight orgs whose name matches this regex "
                             "(e.g. 'law|medic'). Doesn't prune the tree.")
    g_list.add_argument("--include-zero", action="store_true",
                        help="Show branches with zero courses (default: hide).")

    g_filter = ap.add_argument_group("filter mode")
    g_filter.add_argument("--blacklist-org", nargs="*", default=[],
                          help="Org IDs to drop, including all their descendants.")
    g_filter.add_argument("--blacklist-org-name", nargs="*", default=[],
                          help="Regex patterns; orgs whose name matches any pattern "
                               "(and their descendants) are blacklisted. Useful when "
                               "you don't have the ID handy.")
    g_filter.add_argument("--blacklist-code-prefix", nargs="*", default=[],
                          help="Drop courses whose `code` starts with any of these "
                               "(e.g. PROV LL).")
    g_filter.add_argument("--keep-attainment-language", nargs="*", default=[],
                          help="If set, keep only courses whose "
                               "possibleAttainmentLanguages includes one of these "
                               "(e.g. en fi).")

    args = ap.parse_args()
    if args.list_orgs:
        list_orgs_cmd(args)
    else:
        filter_cmd(args)


if __name__ == "__main__":
    main()
