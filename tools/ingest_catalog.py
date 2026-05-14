#!/usr/bin/env python3
"""
Crawl the SISU (Funidata `kori`) public course catalog into a JSONL file.

Two phases:
  1. Enumerate course-unit IDs via /kori/api/course-unit-search with text queries.
     The endpoint requires >=3-char fullTextQuery and silently caps pageSize at 20,
     so we issue many small prefix queries and union the results.
  2. Fetch each unique ID's full detail via /kori/api/course-units/{id}.

No auth. Federated: querying sisu.helsinki.fi also returns Aalto cooperation-network
courses, but to be complete we query both Helsinki and Aalto domains and dedupe by ID.

The JSONL is append-only and resumable: re-running skips IDs already written.
"""

import argparse
import http.client
import json
import os
import ssl
import sys
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

DOMAINS = ["sisu.helsinki.fi", "sisu.aalto.fi"]

# Hand-picked 3-char prefixes covering English + Finnish + Swedish course-name stems.
# Add more in a --queries-file for fuller coverage.
DEFAULT_PREFIXES = sorted(set([
    # English stems
    "alg", "ana", "app", "art", "bas", "bio", "bus", "cal", "che", "cli", "cog", "com",
    "con", "cou", "dat", "des", "dev", "eco", "edu", "ele", "eng", "env", "evo", "exp",
    "fin", "fun", "gen", "geo", "glo", "gra", "hea", "his", "hum", "ide", "imm", "ind",
    "inf", "int", "kno", "lab", "lan", "law", "lea", "lib", "lin", "lit", "log", "mac",
    "mar", "mat", "med", "met", "mod", "mol", "nat", "net", "neu", "obj", "ope", "org",
    "par", "phi", "phy", "pol", "pra", "pri", "pro", "psy", "pub", "qua", "rea", "rel",
    "res", "rev", "sci", "sec", "sem", "ser", "sof", "spa", "spe", "sta", "str", "stu",
    "sus", "sys", "tea", "tec", "the", "top", "tra", "uni", "urb", "use", "war", "wel",
    "wor",
    # Finnish stems
    "ait", "arv", "asi", "ela", "elä", "fil", "fys", "geo", "hal", "hen", "ihm", "ilm",
    "joh", "joh", "kas", "kau", "kem", "kie", "kir", "koh", "koe", "kos", "kou", "kul",
    "laa", "lai", "las", "lii", "lin", "luo", "maa", "mat", "met", "muu", "oik", "ope",
    "ota", "pal", "per", "poh", "pol", "puh", "pää", "raj", "rak", "sak", "sis", "sov",
    "suo", "tai", "tal", "tap", "tek", "tie", "tuo", "työ", "uud", "val", "vas", "vie",
    "vir", "yht", "yle", "ymp",
    # Swedish stems
    "all", "and", "arb", "ber", "bes", "bok", "del", "den", "dig", "exa", "fly", "fol",
    "för", "gen", "gru", "han", "hög", "jor", "kom", "kun", "kva", "män", "ord", "ped",
    "per", "pol", "pro", "sam", "ski", "sko", "spr", "ste", "sva", "tea", "tek", "tex",
    "ung", "upp", "utb", "var", "ver", "väg",
]))

REQUEST_TIMEOUT = 30

# Persistent HTTPS connections per (thread, host) — reusing connections takes a
# single request from ~2.7s (cold TLS handshake every call) down to ~175ms.
_tls = threading.local()
_ssl_ctx = ssl.create_default_context()


def _get_conn(host):
    pool = getattr(_tls, "pool", None)
    if pool is None:
        pool = {}
        _tls.pool = pool
    conn = pool.get(host)
    if conn is None:
        conn = http.client.HTTPSConnection(host, context=_ssl_ctx, timeout=REQUEST_TIMEOUT)
        pool[host] = conn
    return conn


class RateLimiter:
    """Simple thread-safe ~N requests/sec gate."""
    def __init__(self, rps):
        self.rps = max(0.1, float(rps))
        self.lock = threading.Lock()
        self.last = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            min_gap = 1.0 / self.rps
            sleep_for = self.last + min_gap - now
            if sleep_for > 0:
                time.sleep(sleep_for)
            self.last = time.monotonic()


HEADERS = {
    "Accept": "application/json",
    "User-Agent": "sisu-curriculum-tool/0.1 (personal study planner)",
    "Connection": "keep-alive",
}


def fetch_json(host, path, retries=3):
    """GET https://{host}{path} with thread-local connection reuse. Raises on persistent failure."""
    last_err = None
    for attempt in range(retries):
        try:
            conn = _get_conn(host)
            conn.request("GET", path, headers=HEADERS)
            resp = conn.getresponse()
            body = resp.read()
            if resp.status in (429, 503):
                last_err = http.client.HTTPException(f"HTTP {resp.status}")
                time.sleep(2 ** attempt)
                continue
            if resp.status >= 400:
                # Drop the connection; some servers leave the socket in a bad state after errors.
                conn.close()
                _tls.pool.pop(host, None)
                raise http.client.HTTPException(
                    f"HTTP {resp.status} for {path}: {body[:200]!r}")
            return json.loads(body)
        except (http.client.HTTPException, ConnectionError, TimeoutError, OSError) as e:
            last_err = e
            # Connection may be in a bad state — drop and let the next attempt re-open.
            pool = getattr(_tls, "pool", None)
            if pool:
                c = pool.pop(host, None)
                if c is not None:
                    try: c.close()
                    except Exception: pass
            time.sleep(2 ** attempt)
    raise last_err


def search_page(domain, query, start, page_size, limiter):
    limiter.wait()
    qs = urllib.parse.urlencode({
        "fullTextQuery": query,
        "pageSize": page_size,
        "start": start,
    })
    return fetch_json(domain, f"/kori/api/course-unit-search?{qs}")


def _enumerate_one_query(domain, q, limiter):
    """Paginate one prefix query, return list of search-result rows."""
    page_size = 20  # API caps pageSize at 20 regardless of what we ask
    out = []
    start = 0
    while True:
        try:
            page = search_page(domain, q, start, page_size, limiter)
        except Exception as e:
            print(f"  [{domain}] '{q}' start={start} ERROR: {e}", file=sys.stderr)
            break
        results = page.get("searchResults", [])
        out.extend(results)
        total = page.get("total", 0)
        start += page_size
        if start >= total or not results:
            break
    return q, out


def enumerate_ids(domain, queries, limiter, workers=16):
    """Return dict id -> light search-result row (first occurrence wins).

    Runs prefix queries concurrently. The shared RateLimiter still caps total
    request rate; workers controls how many query streams paginate in parallel.
    """
    found = {}
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_enumerate_one_query, domain, q, limiter): q for q in queries}
        for fut in as_completed(futures):
            q, rows = fut.result()
            for r in rows:
                cid = r["id"]
                if cid not in found:
                    found[cid] = r
            done += 1
            print(f"  [{domain}] '{q}' -> {len(rows)} hits  "
                  f"(progress {done}/{len(queries)}, unique: {len(found)})",
                  file=sys.stderr)
    return found


def fetch_course_detail(domain, course_id, limiter):
    limiter.wait()
    return fetch_json(domain, f"/kori/api/course-units/{urllib.parse.quote(course_id)}")


def _latest_activity_end(search_hit):
    """Return the latest activityPeriod end date string, or None if no periods."""
    aps = search_hit.get("activityPeriods") or []
    ends = [ap.get("endDate") for ap in aps if ap.get("endDate")]
    return max(ends) if ends else None


def _resolve_staleness_cutoff(spec):
    """Convert --staleness-cutoff value into an ISO date string or None."""
    if not spec or spec == "none":
        return None
    if spec == "academic-year":
        today = date.today()
        # Finnish academic year starts ~Aug 1. Anything ending before the *current*
        # academic year's start (whether that was last year or this year's Aug) is
        # considered stale.
        ay_start_year = today.year if today.month >= 8 else today.year - 1
        return f"{ay_start_year}-08-01"
    # Otherwise assume ISO date
    date.fromisoformat(spec)  # validate
    return spec


def list_universities(domain):
    """Print active university root organisations from /kori/api/organisations/roots."""
    print(f"Fetching https://{domain}/kori/api/organisations/roots ...", file=sys.stderr)
    data = fetch_json(domain, "/kori/api/organisations/roots")
    rows = []
    for org in data:
        if org.get("status") != "ACTIVE":
            continue
        # The "universities" are typically the ones whose id ends in -university-root-id
        if not org.get("universityOrgId", "").endswith("-university-root-id"):
            continue
        if org.get("id") != org.get("universityOrgId"):
            continue
        rows.append((org["id"], (org.get("name") or {}).get("en")
                     or (org.get("name") or {}).get("fi") or "?"))
    rows.sort()
    print(f"\n{len(rows)} Finnish SISU universities:\n")
    for uid, name in rows:
        print(f"  {uid:<40}  {name}")
    print("\nUse with: --universities <id1> <id2> ...  (or 'all' to keep every uni).")


def _has_any_description(detail):
    """True if any of content/outcomes/prerequisites is non-empty in any language."""
    for field in ("content", "outcomes", "prerequisites"):
        loc = detail.get(field) or {}
        for v in loc.values():
            if v and v.strip():
                return True
    return False


def is_in_catalog(detail):
    """Course is part of the live catalog.

    Keep a course if its definition is ACTIVE and its validityPeriod has not
    ended. We do NOT filter by whether it's being offered *right now* — a
    course taught in autumn is still kept when we crawl in spring, since the
    student can register for it later. Only genuinely discontinued courses
    (validityPeriod.endDate in the past, or documentState != ACTIVE) are
    dropped.
    """
    if detail.get("documentState") != "ACTIVE":
        return False
    vp = detail.get("validityPeriod") or {}
    end = vp.get("endDate")
    if end and end < date.today().isoformat():
        return False
    return True


def pick_domain_for_id(course_id, available_domains):
    """Prefer the home university's own domain for fetching details."""
    if course_id.startswith("hy-") and "sisu.helsinki.fi" in available_domains:
        return "sisu.helsinki.fi"
    if course_id.startswith("aalto-") and "sisu.aalto.fi" in available_domains:
        return "sisu.aalto.fi"
    return available_domains[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--domains", nargs="+", default=DOMAINS,
                    help=f"SISU hostnames. Default: {' '.join(DOMAINS)}. "
                         "Detail fetch goes to the course's home domain when possible.")
    ap.add_argument("--search-domain", default=None,
                    help="If set, only this domain is used for phase-1 enumeration "
                         "(federation returns courses from all cooperation-network "
                         "universities anyway). Defaults to the first --domains entry.")
    ap.add_argument("--queries-file",
                    help="Path to a file with one prefix per line (>=3 chars). "
                         "Defaults to a built-in list.")
    ap.add_argument("--out", default="data/courses.jsonl",
                    help="Output JSONL path (append-only, resumable).")
    ap.add_argument("--rps", type=float, default=30.0,
                    help="Max requests per second (shared by both phases).")
    ap.add_argument("--workers", type=int, default=16,
                    help="Concurrent workers for phase 1 (one per prefix query) "
                         "and phase 2 (one per detail fetch).")
    ap.add_argument("--list-universities", action="store_true",
                    help="Print the known Finnish SISU university root IDs and exit. "
                         "Use the IDs with --universities.")
    ap.add_argument("--limit", type=int, default=0,
                    help="Stop after writing N courses (for testing).")
    ap.add_argument("--include-inactive", action="store_true",
                    help="Keep courses whose documentState != ACTIVE or whose "
                         "validityPeriod has ended.")
    ap.add_argument("--universities", nargs="+",
                    default=["hy-university-root-id", "aalto-university-root-id"],
                    help="Only keep courses whose universityOrgIds intersect this set. "
                         "Federation returns courses from ~10 Finnish unis; default "
                         "restricts to Helsinki + Aalto. Pass 'all' to keep everything.")
    ap.add_argument("--staleness-cutoff", default="academic-year",
                    help='Drop courses whose newest activityPeriod ended before the '
                         'cutoff. Two forms: "academic-year" (the default — anything '
                         'ending before the current Finnish academic year started, '
                         'i.e. Aug 1 of the current or previous calendar year) or an '
                         'ISO date like 2024-08-01. Use "none" to disable.')
    ap.add_argument("--phase1-only", action="store_true",
                    help="Only enumerate IDs; skip detail fetch.")
    args = ap.parse_args()

    if args.list_universities:
        list_universities(args.domains[0])
        return

    if args.queries_file:
        with open(args.queries_file) as f:
            queries = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    else:
        queries = DEFAULT_PREFIXES

    short = [q for q in queries if len(q) < 3]
    if short:
        print(f"WARNING: {len(short)} queries are <3 chars and will return no results: "
              f"{short[:5]}{'...' if len(short) > 5 else ''}", file=sys.stderr)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    # Resume: skip IDs already in the output file
    already_written = set()
    if os.path.exists(args.out):
        with open(args.out) as f:
            for line in f:
                try:
                    already_written.add(json.loads(line)["id"])
                except Exception:
                    pass
        print(f"Resume: {len(already_written)} courses already in {args.out}",
              file=sys.stderr)

    limiter = RateLimiter(args.rps)

    # Phase 1: enumerate. Federation means one domain is usually enough.
    search_domain = args.search_domain or args.domains[0]
    print(f"\nPhase 1: enumerating IDs via {len(queries)} queries at {search_domain} "
          f"(federated) at <= {args.rps} rps, {args.workers} workers...",
          file=sys.stderr)
    t0 = time.monotonic()
    all_found = enumerate_ids(search_domain, queries, limiter, workers=args.workers)
    print(f"Phase 1 done: {len(all_found)} unique IDs in {time.monotonic()-t0:.1f}s.",
          file=sys.stderr)

    # Apply university filter at phase 1 — search results carry universityOrgIds, so
    # we can drop out-of-scope IDs before paying for their detail fetches.
    uni_filter = None if (args.universities == ["all"] or "all" in args.universities) \
                 else set(args.universities)
    if uni_filter:
        before = len(all_found)
        all_found = {
            cid: hit for cid, hit in all_found.items()
            if set(hit.get("universityOrgIds") or []) & uni_filter
        }
        print(f"  Filtered to {len(all_found)} IDs in {sorted(uni_filter)} "
              f"(dropped {before - len(all_found)} from other universities).",
              file=sys.stderr)

    # Drop courses whose newest scheduled offering is too far in the past with
    # nothing forward. The search hit's `activityPeriods` is what we need.
    cutoff = _resolve_staleness_cutoff(args.staleness_cutoff)
    if cutoff:
        before = len(all_found)
        all_found = {
            cid: hit for cid, hit in all_found.items()
            if _latest_activity_end(hit) and _latest_activity_end(hit) >= cutoff
        }
        print(f"  Filtered to {len(all_found)} IDs with offerings ending >= {cutoff} "
              f"(dropped {before - len(all_found)} stale or never-offered courses).",
              file=sys.stderr)

    if args.phase1_only:
        ids_path = args.out.replace(".jsonl", ".ids.txt")
        with open(ids_path, "w") as f:
            for cid in sorted(all_found):
                f.write(cid + "\n")
        print(f"Wrote {len(all_found)} IDs to {ids_path}", file=sys.stderr)
        return

    # Phase 2: details
    to_fetch = [(cid, pick_domain_for_id(cid, args.domains))
                for cid in all_found if cid not in already_written]
    print(f"\nPhase 2: fetching details for {len(to_fetch)} new courses "
          f"({len(already_written)} cached) with {args.workers} workers...",
          file=sys.stderr)

    written = 0
    skipped_inactive = 0
    skipped_university = 0  # courses that slipped past phase-1 filter (rare; defensive)
    failed = 0
    missing_desc = []  # IDs that were ACTIVE but have no description in any language

    write_lock = threading.Lock()
    with open(args.out, "a", encoding="utf-8") as fout, \
         ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(fetch_course_detail, dom, cid, limiter): (cid, dom)
                   for cid, dom in to_fetch}
        for fut in as_completed(futures):
            cid, dom = futures[fut]
            try:
                detail = fut.result()
            except Exception as e:
                failed += 1
                print(f"  detail FAIL {cid} ({dom}): {e}", file=sys.stderr)
                continue
            if not args.include_inactive and not is_in_catalog(detail):
                skipped_inactive += 1
                continue
            if uni_filter and not (set(detail.get("universityOrgIds") or []) & uni_filter):
                skipped_university += 1
                continue
            detail["_fetchedFrom"] = dom
            if not _has_any_description(detail):
                missing_desc.append((detail.get("code"), cid))
            with write_lock:
                fout.write(json.dumps(detail, ensure_ascii=False) + "\n")
                fout.flush()
                written += 1
                if written % 50 == 0:
                    print(f"  written={written} skipped_inactive={skipped_inactive} "
                          f"failed={failed} missing_desc={len(missing_desc)}",
                          file=sys.stderr)
            if args.limit and written >= args.limit:
                print("  --limit reached, stopping.", file=sys.stderr)
                for f2 in futures:
                    f2.cancel()
                break

    print(f"\nDone. Written: {written}  Skipped inactive: {skipped_inactive}  "
          f"Skipped (other university): {skipped_university}  Failed: {failed}",
          file=sys.stderr)
    print(f"Output: {args.out}", file=sys.stderr)
    if missing_desc:
        miss_path = args.out.replace(".jsonl", ".missing_description.txt")
        with open(miss_path, "w") as mf:
            for code, cid in missing_desc:
                mf.write(f"{code}\t{cid}\n")
        print(f"\n{len(missing_desc)} ACTIVE courses had no description in any language.",
              file=sys.stderr)
        print(f"  List written to {miss_path}", file=sys.stderr)
        print(f"  These were kept in the JSONL (user policy: surface, don't drop).",
              file=sys.stderr)


if __name__ == "__main__":
    main()
