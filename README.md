# Cigar Scanner humidor exporter

Exports your Cigar Scanner humidor to a clean CSV by talking to the app's own
data API.

## How it works

Cigar Scanner is a JavaScript single-page app. Its cigar data is not in the page
HTML; the app fetches it from `api.cigarscanner.com` after you log in, paging
20 records at a time. This script:

1. Opens a real Chromium browser (via Playwright).
2. Lets you log in and clear any Cloudflare check **by hand** (the script never
   touches the CAPTCHA and never reloads in a loop).
3. Watches the app's network traffic, captures the listing endpoint that returns
   your cigars, and grabs your session auth.
4. Pages that endpoint (skip=0,20,40...) until it's empty, flattens the nested
   JSON into named columns, and writes the CSV.

## Setup

```bash
uv add playwright
uv run playwright install chromium
```

## Run

Easiest is the runner script:

```bash
chmod +x run.sh
./run.sh            # normal run, keeps you logged in between runs
./run.sh --reset    # wipe the saved login (.cs_profile) and start fresh
```

Or directly with the subcommands:

```bash
uv run main.py export --dump-json   # page the endpoint, write CSV (+ raw JSON)
uv run main.py discover             # dump every API response to debug/ (troubleshooting)
```

When the browser opens:
1. Clear any Cloudflare "verify you are human" check yourself.
2. Log in if prompted.
3. Open your humidor and **scroll the cigar list top to bottom** once. Scrolling
   is what makes the app fetch the cigars, which is what the script listens for.
4. Return to the terminal and press ENTER.

Output: written to the `output/` folder inside the project:
`output/humidor_export.csv` (and `output/humidor_raw.json` with `--dump-json`).

## CSV columns

The API nests cigar attributes under `CigarDetails` (with further nesting for
ratings and prices). The exporter flattens these into:

Name, Quantity, AvgRating, RatingCount, MyRating, MyNote, MyComment, Length,
RingGauge, SinglePriceMin, SinglePriceMax, BoxPriceMin, BoxPriceMax, MinBoxQty,
MaxBoxQty, PricePaid, Location, DateAdded, ModifiedOn, IsCustom, SmokingTime,
ImageUrl, ProductId, LineId, EntryId.

- `Quantity` is how many you have; a smoked-out cigar may show 0.
- `AvgRating` / `RatingCount` are the community rating; `MyRating` / `MyComment`
  are your own review if you left one.
- `PricePaid` is the price recorded on your entry (often blank); the
  Single/Box price columns are reference retail prices.

## Subcommands

- `export` — the normal path. Pages the cigar endpoint and writes CSV.
  - `--out <file>`      custom output filename (default humidor_export.csv)
  - `--dump-json`       also write humidor_raw.json
  - `--humidor-id <id>` use a different humidor
- `discover` — troubleshooting. Saves every API JSON response to `debug/` and
  reports which ones contain record lists, so you can confirm the endpoint.

## Notes

- The project can live anywhere (e.g. `Tobacco Town/get-humidor/` in iCloud
  Drive). All paths (`output/`, `.cs_profile/`, `debug/`) are anchored to the
  script's own folder, and `run.sh` cd's into that folder first, so it works no
  matter where you launch it from.
- Your login is cached in a local `.cs_profile/` folder so you don't re-auth (and
  re-trigger Cloudflare) every run. It holds your session, so keep it private.
  Delete it (or use `./run.sh --reset`) only when the session is broken.
- The script never solves or clicks the Cloudflare challenge. If you get blocked,
  wait a few minutes and confirm the site loads in your normal browser first.
