#!/usr/bin/env python3
"""
Fetch the logged-in user's completed-course attainments from one or more SISU
instances. Opens a real Chromium window via Playwright, the user logs in via
their university's Shibboleth, and after they press Enter in the terminal the
script calls /ori/api/my-attainments using the captured session.

Supports multiple SISU instances — a student enrolled at both HY and Aalto can
run this once per domain and the results merge into a single transcript file.

Usage:
    pip install playwright
    playwright install chromium      # one-time; downloads the browser
    python fetch_transcript.py --domain sisu.helsinki.fi
    python fetch_transcript.py --domain sisu.aalto.fi   # adds Aalto too

Output: data/transcript.json with shape
    {
      "universities": {
        "sisu.helsinki.fi": {
          "fetched_at": "2026-...",
          "attainments": [ ...raw /ori/api/my-attainments payload... ]
        },
        "sisu.aalto.fi": { ... }
      }
    }
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit(
        "Playwright is not installed. Run:\n"
        "    pip install playwright\n"
        "    playwright install chromium\n"
    )


KNOWN_DOMAINS = {
    "sisu.helsinki.fi": "University of Helsinki",
    "sisu.aalto.fi": "Aalto University",
    "sisu.jyu.fi": "University of Jyväskylä",
    "sisu.tuni.fi": "Tampere University",
    "sisu.lut.fi": "LUT University",
    "sisu.hanken.fi": "Hanken School of Economics",
    "sisu.arcada.fi": "Arcada UAS",
    "sisu.lab.fi": "LAB UAS",
    "sisu.ha.ax": "Åland UAS",
}


def fetch_attainments(domain, headless=False):
    """Open a browser to {domain}/student/, wait for user login, return JSON list.

    SISU's /ori/api/* endpoints are NOT cookie-authenticated — they require
    `Authorization: Bearer <jwt>` where the JWT is vended via /ori/preauth
    after a successful Shibboleth login. The SPA fetches this token on
    bootstrap and uses it for every authenticated API call.

    Our strategy: spy on the SPA's own outbound requests, grab the
    Authorization header from any /ori/api/* call it makes during normal
    dashboard load, then reuse that token for /ori/api/my-attainments.
    """
    target_url = f"https://{domain}/student/"
    api_url = f"https://{domain}/ori/api/my-attainments"

    bearer = {"value": None}

    def _capture(request):
        # SPA hits /ori/api/* with the Bearer; first one wins.
        if "/ori/api/" in request.url and bearer["value"] is None:
            auth = request.headers.get("authorization")
            if auth and auth.lower().startswith("bearer "):
                bearer["value"] = auth.split(" ", 1)[1]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.on("request", _capture)
        page.goto(target_url)

        print(f"\n  A browser window has opened to {domain}.")
        print(f"  Please complete the Shibboleth login.")
        print(f"  Once you see the SISU dashboard (Etusivu / Front page),")
        try:
            input("  press Enter here to fetch your attainments... ")
        except (EOFError, KeyboardInterrupt):
            browser.close()
            raise SystemExit("\n  Aborted.")

        # If no Bearer was seen yet, nudge the SPA by navigating to a page that
        # is guaranteed to hit /ori/. The attainment listing page does this.
        if bearer["value"] is None:
            print("  No Bearer token seen yet; navigating to attainments page to "
                  "force the SPA to fetch one...")
            try:
                page.goto(f"{target_url}profile/attainments", timeout=15000)
                # Give the SPA a moment to bootstrap its HTTP requests.
                page.wait_for_timeout(3000)
            except Exception:
                pass

        # Last resort: try /ori/preauth directly via the page's context, which
        # carries the Shibboleth session cookie.
        if bearer["value"] is None:
            print("  Still no Bearer; trying /ori/preauth directly...")
            try:
                pre = ctx.request.get(f"https://{domain}/ori/preauth",
                                       headers={"Accept": "application/json"})
                if pre.status == 200:
                    try:
                        data = pre.json()
                        bearer["value"] = (data.get("accessToken")
                                           or data.get("token")
                                           or data.get("jwt"))
                    except Exception:
                        # Sometimes /ori/preauth returns plain text JWT
                        bearer["value"] = pre.text().strip().strip('"') or None
            except Exception as e:
                print(f"  /ori/preauth failed: {e}")

        if bearer["value"] is None:
            browser.close()
            raise SystemExit(
                "  Could not capture a Bearer token. Are you fully logged in? "
                "The dashboard should show your name in the top-right before "
                "you press Enter."
            )

        # Now call the real endpoint with the captured token.
        resp = ctx.request.get(
            api_url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {bearer['value']}",
            },
        )
        status = resp.status
        body = resp.body()
        browser.close()

    if status == 401:
        raise SystemExit(
            f"  Still got HTTP 401 with a captured Bearer. The token may have "
            f"expired or be scoped wrong. Try again."
        )
    if status != 200:
        raise SystemExit(
            f"  Got HTTP {status} from {api_url}.\n"
            f"  Body (truncated): {body[:500]!r}"
        )
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise SystemExit(f"  Response was not JSON: {e}\n  First bytes: {body[:200]!r}")


def merge_into_transcript(path, domain, attainments):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"universities": {}}

    data.setdefault("universities", {})
    data["universities"][domain] = {
        "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "count": len(attainments) if isinstance(attainments, list) else None,
        "attainments": attainments,
    }

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def summarise(attainments):
    """Print a short summary so the user can sanity-check what was fetched."""
    if not isinstance(attainments, list):
        print(f"  Response was not a list (got {type(attainments).__name__}). "
              f"Saved raw response anyway.")
        return
    print(f"\n  Fetched {len(attainments)} attainment record(s).")
    # Show a few credits-bearing course attainments
    courses = [a for a in attainments
               if a.get("type") == "CourseUnitAttainment"
               or a.get("attainmentType") == "CourseUnitAttainment"]
    print(f"  Of which CourseUnitAttainment: {len(courses)}")
    for a in courses[:5]:
        name = (a.get("name") or {})
        name_str = name.get("en") or name.get("fi") or a.get("courseUnitGroupId") or "?"
        credits = a.get("credits")
        grade = a.get("gradeId")
        date_ = a.get("attainmentDate") or a.get("registrationDate")
        print(f"    - {date_}  {credits}cr  grade={grade}  {name_str}")
    if len(courses) > 5:
        print(f"    ... and {len(courses) - 5} more")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--domain", required=True,
                    help=f"SISU hostname. Known: {', '.join(KNOWN_DOMAINS)}")
    ap.add_argument("--out", default="data/transcript.json",
                    help="Output JSON path. Re-running with a different --domain merges.")
    ap.add_argument("--headless", action="store_true",
                    help="Run browser headless (not useful for interactive Shibboleth).")
    args = ap.parse_args()

    if args.domain not in KNOWN_DOMAINS:
        print(f"  Note: '{args.domain}' is not in the known-domains list, but "
              f"continuing anyway. Known: {', '.join(KNOWN_DOMAINS)}",
              file=sys.stderr)

    print(f"  Fetching transcript from {args.domain} "
          f"({KNOWN_DOMAINS.get(args.domain, '?')})")
    attainments = fetch_attainments(args.domain, headless=args.headless)
    merge_into_transcript(args.out, args.domain, attainments)
    summarise(attainments)
    print(f"\n  Saved -> {args.out}")


if __name__ == "__main__":
    main()
