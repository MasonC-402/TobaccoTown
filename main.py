#!/usr/bin/env python3
"""
Cigar Scanner humidor exporter (API edition).

Discovery revealed the app's real data endpoint:

  https://api.cigarscanner.com/api/cigarlogs/listing/<HUMIDOR_ID>
      ?SortDescending=true&skip=0&sortBy=date&take=20

It pages with skip/take (20 at a time), which is exactly why a scroll-based
scrape only saw the first batch. This script talks to that endpoint directly.

The one catch: the endpoint needs your auth. Rather than make you copy tokens
out of DevTools, the script opens a real browser, lets you log in once, and
then reads the Authorization header (and cookies) off a live API call the app
makes. It reuses that to page the listing endpoint from skip=0 upward until a
page comes back empty, collecting every cigar, then writes a CSV.

Usage:
  uv add playwright
  uv run playwright install chromium
  uv run main.py                # writes humidor_export.csv

If you have more than one humidor, pass its id:
  uv run main.py --humidor-id <UUID>
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    sys.exit(
        "Playwright is not installed.\n"
        "  uv add playwright\n"
        "  uv run playwright install chromium\n"
    )

DEFAULT_HUMIDOR_ID = ""
API_BASE = "https://api.cigarscanner.com/api/cigarlogs/listing"
HUMIDOR_URL = "https://www.cigarscanner.com/tabs/my-humidors/{hid}"
LOGIN_URL = "https://www.cigarscanner.com/login"
PAGE_SIZE = 20

# Anchor all paths to the project directory (where this script lives), so the
# script behaves the same no matter what folder you run it from. This matters
# under iCloud Drive (e.g. Tobacco Town/get-humidor/), where the working
# directory may differ from the project directory.
PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"
PROFILE_DIR = PROJECT_DIR / ".cs_profile"
DEBUG_DIR = PROJECT_DIR / "debug"


class AuthSniffer:
    """
    Captures (a) the Authorization header from real API requests, and
    (b) EVERY JSON response from the API along with its body, so we can identify
    which endpoint actually returns the user's cigars (no URL guessing).
    """

    def __init__(self):
        self.authorization = None
        self.seen_api = False
        self.all_responses = []   # every API JSON response: {url, body}
        self.listing_hits = []    # responses that contain a list of records

    def handle_request(self, request):
        try:
            url = request.url
            if "api.cigarscanner.com/api/" not in url:
                return
            self.seen_api = True
            auth = request.headers.get("authorization")
            if auth and not self.authorization:
                self.authorization = auth
        except Exception:
            pass

    def handle_response(self, response):
        try:
            url = response.url
            if "api.cigarscanner.com/api/" not in url:
                return
            ctype = response.headers.get("content-type", "")
            if "application/json" not in ctype:
                return
            body = response.json()
        except Exception:
            return

        # Record every API JSON response.
        self.all_responses.append({"url": url, "body": body})

        # Find a list of record-like dicts anywhere in the body (top level or
        # one level down inside a dict).
        items = _find_record_list(body)
        if items:
            self.listing_hits.append({
                "url": url,
                "count": len(items),
                "sample": items[0],
                "items": items,
            })


def _find_record_list(body):
    """Return the first list-of-dicts found at top level or one level deep."""
    if isinstance(body, list) and body and isinstance(body[0], dict):
        return body
    if isinstance(body, dict):
        for v in body.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
    return None


def launch(p, headless=False):
    return p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=headless,
        viewport={"width": 1280, "height": 900},
    )


def ensure_logged_in_and_authed(page, sniffer, humidor_id):
    """
    Navigate to the humidor, let the USER handle login and any Cloudflare
    challenge by hand, then passively capture auth from the app's own calls.

    This function never clicks the CAPTCHA, never solves a challenge, and never
    reloads in a loop. Cloudflare's check is a bot-detection control; the script
    waits for you to clear it manually and does nothing to the page meanwhile.
    """
    target = HUMIDOR_URL.format(hid=humidor_id)

    # Single navigation attempt. If it fails, we tell the user rather than
    # retrying in a tight loop (loops re-trigger Cloudflare and get you blocked).
    try:
        page.goto(target, wait_until="domcontentloaded", timeout=45000)
    except Exception as e:
        print(f"\nInitial navigation hiccup: {e}")
        print("That's usually a Cloudflare check or a stale session.")

    print("\n" + "=" * 68)
    print("In the browser window:")
    print("  1. If you see a Cloudflare 'verify you are human' check, complete")
    print("     it yourself. The script will NOT touch it and will just wait.")
    print("  2. Log in if prompted.")
    print("  3. Open your humidor and SCROLL through the cigar list once, top")
    print("     to bottom. Scrolling is what makes the app fetch the cigars,")
    print("     which is exactly what this script listens for.")
    print("=" * 68)
    input(">>> When you've scrolled the list and cigars are visible, press ENTER... ")

    # Passive capture only. We do NOT reload. The app makes its own API calls
    # as you browse; if we already saw an Authorization header, great. If not,
    # give it a short, quiet window in case a call is in flight, then proceed.
    if not sniffer.authorization:
        print("Waiting briefly for the app's own API calls (no reloads)...")
        for _ in range(10):
            if sniffer.authorization:
                break
            time.sleep(1)

    if not sniffer.authorization:
        # Cookie-based auth path: the browser fetch will still carry the session
        # via credentials:'include', so this is not necessarily a failure.
        print("No bearer token captured; will rely on your browser session "
              "(cookies) for the API calls instead.")


def _looks_logged_in(page):
    try:
        return "/login" not in page.url
    except Exception:
        return False


def page_endpoint(page, base_url, authorization, start_skip=0):
    """
    Page a listing endpoint that we KNOW returns data (captured from the app).
    We rewrite the skip param and walk until a page returns empty. start_skip
    lets the caller begin partway through (e.g. to top up already-have records).
    """
    from urllib.parse import urlsplit, urlunsplit, parse_qs

    parts = urlsplit(base_url)
    params = parse_qs(parts.query)
    # Normalize: ensure a take, drive skip ourselves.
    take = int(params.get("take", ["20"])[0]) if params.get("take") else PAGE_SIZE
    take = take or PAGE_SIZE

    all_rows = []
    skip = start_skip
    while True:
        q = {k: v[0] for k, v in params.items()}
        q["skip"] = str(skip)
        q["take"] = str(take)
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), ""))

        result = page.evaluate(
            """async ({url, auth}) => {
                const headers = {'Accept': 'application/json'};
                if (auth) headers['Authorization'] = auth;
                const r = await fetch(url, {headers, credentials: 'include'});
                const text = await r.text();
                let body; try { body = JSON.parse(text); } catch { body = null; }
                return {status: r.status, body};
            }""",
            {"url": url, "auth": authorization},
        )

        status = result.get("status")
        body = result.get("body")
        if status != 200:
            print(f"  skip={skip}: HTTP {status} (stopping)")
            break

        items = body if isinstance(body, list) else None
        if items is None and isinstance(body, dict):
            for v in body.values():
                if isinstance(v, list):
                    items = v
                    break
        if not isinstance(items, list):
            print(f"  skip={skip}: unexpected shape (stopping)")
            break
        if len(items) == 0:
            break

        all_rows.extend(items)
        print(f"  skip={skip}: +{len(items)} (total {len(all_rows)})")
        skip += take
        if skip > 10000:
            break
        time.sleep(1.0)

    return all_rows


def flatten(record):
    """
    Flatten one Cigar Scanner inventory record into clean, named columns.

    Top-level fields hold your inventory data (Quantity, Price, Date, your own
    rating). The cigar's attributes live nested under CigarDetails, with further
    nesting for RatingSummary, Prices, and MyRating. We pull the useful ones up
    into flat columns rather than dumping nested JSON blobs.
    """
    d = record.get("CigarDetails") or {}
    rsum = d.get("RatingSummary") or {}
    prices = d.get("Prices") or {}
    # Your personal rating can sit on the record or inside CigarDetails.
    myr = record.get("MyRating") or d.get("MyRating") or {}
    if not isinstance(myr, dict):
        myr = {}

    def g(src, *keys):
        for k in keys:
            v = src.get(k)
            if v is not None:
                return v
        return ""

    flat = {
        "Name": g(d, "Name"),
        "Quantity": g(record, "Quantity"),
        "AvgRating": g(rsum, "AverageRating"),
        "RatingCount": g(rsum, "RatingCount"),
        "MyRating": g(myr, "Rating"),
        "MyNote": g(d, "MyNote") or g(record, "MyNote"),
        "MyComment": g(myr, "Comment"),
        "Length": g(d, "Length"),
        "RingGauge": g(d, "RingGauge"),
        "SinglePriceMin": g(prices, "SinglePriceMin"),
        "SinglePriceMax": g(prices, "SinglePriceMax"),
        "BoxPriceMin": g(prices, "BoxPriceMin"),
        "BoxPriceMax": g(prices, "BoxPriceMax"),
        "MinBoxQty": g(d, "MinBoxQty"),
        "MaxBoxQty": g(d, "MaxBoxQty"),
        "PricePaid": g(record, "Price"),
        "Location": g(record, "Location"),
        "DateAdded": g(record, "Date"),
        "ModifiedOn": g(record, "ModifiedOn"),
        "IsCustom": g(d, "IsCustom"),
        "SmokingTime": g(d, "SmokingTime"),
        "ImageUrl": g(d, "ImageUrl"),
        "ProductId": g(record, "ProductId") or g(d, "ProductId"),
        "LineId": g(record, "LineId") or g(d, "LineId"),
        "EntryId": g(record, "Id"),
    }
    return flat


def write_csv(records, out_path):
    rows = [flatten(r) for r in records]
    # flatten() returns a consistent, sensibly-ordered set of columns.
    keys = list(rows[0].keys()) if rows else []
    # Include any stray keys that somehow differ between rows.
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})


def cmd_discover(args):
    """Open browser, let user log in + scroll, dump EVERY API JSON to debug/."""
    debug = DEBUG_DIR
    debug.mkdir(parents=True, exist_ok=True)

    sniffer = AuthSniffer()
    with sync_playwright() as p:
        ctx = launch(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        ctx.on("request", sniffer.handle_request)
        ctx.on("response", sniffer.handle_response)

        ensure_logged_in_and_authed(page, sniffer, args.humidor_id)

        # Give a moment for any in-flight responses to be recorded.
        time.sleep(1.5)
        ctx.close()

    if not sniffer.all_responses:
        print("\nNo API JSON responses were captured at all.")
        print("That means the app didn't fetch from api.cigarscanner.com while")
        print("the page was open. Make sure you actually SCROLL the cigar list")
        print("before pressing ENTER, then re-run.")
        return

    print(f"\nCaptured {len(sniffer.all_responses)} API JSON responses. "
          f"Saving to {debug}/ ...")
    summary = []
    for i, resp in enumerate(sniffer.all_responses):
        f = debug / f"api_{i}.json"
        f.write_text(json.dumps(resp, indent=2, ensure_ascii=False),
                     encoding="utf-8")
        items = _find_record_list(resp["body"])
        n = len(items) if items else 0
        fields = list(items[0].keys())[:10] if items else []
        # Shorten the URL for readable display.
        short = resp["url"].replace("https://api.cigarscanner.com/api/", "")
        summary.append((i, n, short, fields))

    print("\nResponses that contain a LIST of records (likely your cigars):")
    any_lists = False
    for i, n, short, fields in summary:
        if n > 0:
            any_lists = True
            print(f"  api_{i}.json : {n:>3} records  <- {short}")
            print(f"               fields: {', '.join(fields)}")
    if not any_lists:
        print("  (none found with list data)")

    print("\nAll captured endpoints:")
    for i, n, short, fields in summary:
        print(f"  api_{i}.json : {n:>3} records  {short}")

    print(f"\nLook in {debug}/ for the file whose record count matches your "
          f"cigar total. Send me that file (or tell me which api_N has your "
          f"cigars) and I'll lock the exporter onto it.")


def cmd_export(args):
    sniffer = AuthSniffer()
    with sync_playwright() as p:
        ctx = launch(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        ctx.on("request", sniffer.handle_request)
        ctx.on("response", sniffer.handle_response)

        ensure_logged_in_and_authed(page, sniffer, args.humidor_id)

        hid = args.humidor_id

        # Let any in-flight listing responses land before we read them. The app
        # fires these as you scroll; pressing ENTER can beat them to the finish.
        def have_humidor_hits():
            return any(f"/listing/{hid}".lower() in h["url"].lower()
                       for h in sniffer.listing_hits)

        for _ in range(8):
            if have_humidor_hits():
                break
            time.sleep(1)

        # Still nothing for this humidor? Trigger the app's own fetch with one
        # in-page navigation back to the humidor (safe now that you're past any
        # Cloudflare check and logged in), then wait for it to land.
        if not have_humidor_hits():
            print("No humidor listing captured yet; nudging the app to fetch it...")
            try:
                page.goto(HUMIDOR_URL.format(hid=hid),
                          wait_until="networkidle", timeout=30000)
            except Exception:
                pass
            for _ in range(10):
                if have_humidor_hits():
                    break
                time.sleep(1)

        # Diagnostics: show exactly what we captured, so a 0 result is explainable.
        print(f"\nCaptured {len(sniffer.all_responses)} API responses, "
              f"{len(sniffer.listing_hits)} of them with record lists.")
        for hit in sniffer.listing_hits:
            short = hit["url"].replace("https://api.cigarscanner.com/api/", "")
            print(f"  {hit['count']:>3} records  {short}")

        merged = {}
        for hit in sniffer.listing_hits:
            # Only this humidor's listing endpoint. The "journal" list and other
            # humidors are excluded so we don't mix in unrelated cigars.
            if f"/listing/{hid}".lower() not in hit["url"].lower():
                continue
            for rec in hit["items"]:
                key = rec.get("Id") or json.dumps(rec, sort_keys=True)[:120]
                merged[key] = rec

        records = list(merged.values())
        if records:
            print(f"\nUsing {len(records)} cigars already loaded by the app "
                  f"(from its own listing calls for this humidor).")
            # Top up from the API in case the scroll didn't surface every page.
            # We page from 0; dedup by Id means any overlap is harmless.
            print("Verifying against the API for any missed pages...")
            base = (f"{API_BASE}/{hid}"
                    f"?SortDescending=true&skip=0&sortBy=date&take={PAGE_SIZE}")
            for rec in page_endpoint(page, base, sniffer.authorization):
                key = rec.get("Id") or json.dumps(rec, sort_keys=True)[:120]
                merged[key] = rec
            records = list(merged.values())
        else:
            # Nothing captured for this humidor: fall back to live paging from 0.
            print("\nNo captured records for this humidor; paging the endpoint "
                  "directly...")
            base = (f"{API_BASE}/{hid}"
                    f"?SortDescending=true&skip=0&sortBy=date&take={PAGE_SIZE}")
            records = page_endpoint(page, base, sniffer.authorization)

        ctx.close()

    if not records:
        sys.exit(
            "Got 0 cigars.\n"
            "Run `uv run main.py discover` instead: it saves every API response "
            "to debug/ so we can see exactly which endpoint holds your cigars.\n"
            "Before pressing ENTER, be sure to SCROLL the cigar list so the app "
            "actually fetches the data."
        )

    # Everything goes into the project's output/ folder.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.dump_json:
        raw_path = OUTPUT_DIR / "humidor_raw.json"
        raw_path.write_text(
            json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote {raw_path}")

    # If the user passed an absolute --out, respect it; otherwise put it in output/.
    out_arg = Path(args.out)
    out = out_arg if out_arg.is_absolute() else OUTPUT_DIR / out_arg.name
    write_csv(records, out)
    print(f"\nExported {len(records)} cigars -> {out.resolve()}")
    if records:
        print("Columns:", ", ".join(flatten(records[0]).keys()))


def main():
    ap = argparse.ArgumentParser(description="Export Cigar Scanner humidor via its API.")
    sub = ap.add_subparsers(dest="cmd")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--humidor-id", default=DEFAULT_HUMIDOR_ID)

    d = sub.add_parser("discover", parents=[common],
                       help="Dump every API response to debug/ to find the endpoint.")
    d.set_defaults(func=cmd_discover)

    e = sub.add_parser("export", parents=[common],
                       help="Page the cigar endpoint and write CSV.")
    e.add_argument("--out", default="humidor_export.csv")
    e.add_argument("--dump-json", action="store_true",
                   help="Also write the raw combined JSON to humidor_raw.json.")
    e.set_defaults(func=cmd_export)

    args = ap.parse_args()
    # Default to export when no subcommand given (keeps ./run.sh working).
    if not getattr(args, "cmd", None):
        args.func = cmd_export
        args.out = "humidor_export.csv"
        args.dump_json = True
        args.humidor_id = DEFAULT_HUMIDOR_ID
    args.func(args)


if __name__ == "__main__":
    main()
