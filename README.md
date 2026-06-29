# TobaccoTown

A desktop GUI app for cigar and pipe tobacco enthusiasts. Use it to catalog your collection and review cigars and blends. Built with Python and customtkinter.

## Features

- **Humidor** — browse your cigar collection, add, edit, or remove cigars from your virtual humidor. 
- **Pick-a-Stick** — randomly pick a cigar from your humidor with an animated slot-machine reveal; filter by brand or size first
- **Pipe Tobacco** — manage your pipe tobacco collection with blend, type, cut, tin date, quantity, and notes
- **My Pipes** — inventory of your physical smoking pipes (maker, shape, material, finish, condition, price, notes)
- **Journal** — tasting notes for any cigar or tobacco you've smoked
- **Import** — import your humidor from CigarScanner.

## Requirements

- macOS 13+, Windows 10+, or Linux
- Python 3.12 (managed automatically via `uv`)

## Setup

**1. Install uv**

macOS / Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows (PowerShell):
```powershell
winget install astral-sh.uv
# or: irm https://astral.sh/uv/install.ps1 | iex
```

**2. Install dependencies**

```bash
uv sync
```

**3. Run the app**

```bash
uv run app.py
```

### macOS — optional .app bundle

If you'd like to launch from Finder or Spotlight, build the app bundle:

```bash
chmod +x build_app.sh
./build_app.sh
```

Then double-click **TobaccoTown.app** to launch. This is macOS-only.

## CigarScanner Import

TobaccoTown can import your humidor from CigarScanner automatically.

1. Open the **Import** page in the app and click **Open Exporter**
2. A terminal window opens and runs the exporter — complete any Cloudflare check and log in if prompted
3. Scroll your humidor list top-to-bottom, then press ENTER in the terminal
4. The CSV is written to `output/humidor_export.csv`
5. Click **Reload Humidor** in the app to load the new data

The exporter works by watching CigarScanner's own API traffic in a real Chromium
browser (via Playwright), so no scraping or reverse-engineering is involved.

The app launches `run.sh` on macOS/Linux and `run.bat` on Windows automatically.

### First-time Chromium setup

The exporter will install Chromium automatically on first run. You can also do it manually:

```bash
uv run playwright install chromium
```

### Resetting your saved login session

```bash
# macOS / Linux
./run.sh --reset

# Windows
run.bat --reset
```

## Data

All pipe tobacco, smoking pipe, and journal entries are stored locally in
`data/tobaccotown.db` (SQLite). The humidor is loaded fresh from the CSV each
launch — the CSV is the source of truth for your cigar inventory.
