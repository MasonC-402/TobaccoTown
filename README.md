# TobaccoTown

A desktop GUI app for cigar and pipe tobacco enthusiasts. Built with Python and customtkinter.

## Features

- **Humidor** — browse your cigar collection imported from CigarScanner, with filterable columns (name, brand, size, quantity, rating, price)
- **Pick-a-Stick** — randomly pick a cigar from your humidor with an animated slot-machine reveal; filter by brand or size first
- **Pipe Tobacco** — manage your pipe tobacco collection with blend, type, cut, tin date, quantity, and notes
- **My Pipes** — inventory of your physical smoking pipes (maker, shape, material, finish, condition, price, notes)
- **Journal** — tasting notes for any cigar or tobacco you've smoked
- **Import** — import your humidor from CigarScanner via CSV export

## Requirements

- macOS 13+
- Python 3.12 (managed via `uv`)

## Setup

```bash
# Install uv if you don't have it
curl -Ls https://astral.sh/uv/install.sh | sh

# Install dependencies and pin Python 3.12
uv sync

# Build the .app bundle (copies the Python binary so Finder can launch it)
chmod +x build_app.sh
./build_app.sh
```

Then double-click **TobaccoTown.app** to launch, or run directly:

```bash
uv run app.py
```

## CigarScanner Import

TobaccoTown can import your humidor from a CigarScanner CSV export.

1. Open the **Import** page in the app and click **Open CigarScanner in Terminal**
2. Follow the terminal prompts — a browser will open so you can log in
3. Scroll your humidor list top-to-bottom, then press ENTER in the terminal
4. The CSV is written to `output/humidor_export.csv`
5. Back in the app, click **Choose CSV** and select that file

The exporter works by watching CigarScanner's own API traffic in a real Chromium
browser (via Playwright), so no scraping or reverse-engineering is involved.

### CigarScanner exporter setup (first time only)

```bash
uv run playwright install chromium
```

## Data

All pipe tobacco, smoking pipe, and journal entries are stored locally in
`data/tobaccotown.db` (SQLite). The humidor is loaded fresh from the CSV each
launch — the CSV is the source of truth for your cigar inventory.
