#!/usr/bin/env python3
"""TobaccoTown — cigar & pipe tobacco companion app."""

from __future__ import annotations

import math
import platform
import random
import re
import subprocess
import sys
import tkinter as tk
from datetime import date as _today
from pathlib import Path
from tkinter import messagebox, ttk

_OS = platform.system()  # "Darwin", "Windows", "Linux"

try:
    import customtkinter as ctk
except ImportError:
    sys.exit("Run:  uv add customtkinter  then restart the app.")

try:
    import pandas as pd
except ImportError:
    pd = None

PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
import db

HUMIDOR_CSV = PROJECT_DIR / "output" / "humidor_export.csv"

# ── Cross-platform fonts ─────────────────────────────────────────────
if _OS == "Darwin":
    FONT_DISPLAY = "SF Pro Display"
    FONT_TEXT    = "SF Pro Text"
elif _OS == "Windows":
    FONT_DISPLAY = "Segoe UI"
    FONT_TEXT    = "Segoe UI"
else:
    FONT_DISPLAY = "Ubuntu"
    FONT_TEXT    = "Ubuntu"

# ── Color palette ────────────────────────────────────────────────────
BG          = "#1a1917"
SIDEBAR_BG  = "#201d1a"
CARD        = "#2d2926"
ACCENT      = "#C47A2E"
ACCENT_HOV  = "#A36020"
ACCENT_DIM  = "#4A3218"
TEXT        = "#E8DCC8"
TEXT_DIM    = "#6E6055"
TREE_BG     = "#211e1b"
TREE_SEL    = "#3D2F1A"
DANGER      = "#7A2E2E"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


# ── Utilities ────────────────────────────────────────────────────────

def _style_treeview(root: tk.Misc) -> None:
    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure("TT.Treeview",
        background=TREE_BG, foreground=TEXT,
        fieldbackground=TREE_BG, rowheight=30,
        font=(FONT_TEXT, 12), borderwidth=0, relief="flat")
    s.configure("TT.Treeview.Heading",
        background=SIDEBAR_BG, foreground=ACCENT,
        font=(FONT_TEXT, 11, "bold"), relief="flat", padding=(6, 8))
    s.map("TT.Treeview",
        background=[("selected", TREE_SEL)],
        foreground=[("selected", TEXT)])
    s.configure("Vertical.TScrollbar",
        background=CARD, troughcolor=TREE_BG,
        arrowcolor=TEXT_DIM, bordercolor=TREE_BG)


def _sf(v) -> float | None:
    """Safe float — returns None for missing, empty, or NaN."""
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _parse_length(s: str) -> float | None:
    """Parse '4"7/8' → 4.875  or  '6"' → 6.0  or  '' → None."""
    if not s:
        return None
    m = re.match(r'^(\d+)"(?:(\d+)/(\d+))?$', str(s).strip())
    if not m:
        return None
    whole = int(m.group(1))
    frac = int(m.group(2)) / int(m.group(3)) if m.group(2) else 0.0
    return whole + frac


def _load_humidor_csv() -> list[dict]:
    if not HUMIDOR_CSV.exists() or pd is None:
        return []
    try:
        df = pd.read_csv(HUMIDOR_CSV)
        df = df[df["Name"].notna()].copy()
        return df.to_dict("records")
    except Exception:
        return []


def _load_humidor() -> list[dict]:
    rows = db.humidor_all()
    if not rows:
        # First-run migration: pull existing CSV data into the db automatically.
        csv_rows = _load_humidor_csv()
        if csv_rows:
            db.humidor_upsert_from_csv(csv_rows)
            rows = db.humidor_all()
    return rows


def _make_tree(
    parent: tk.Misc,
    columns: list[tuple[str, str, int]],
) -> tuple[ttk.Treeview, tk.Frame]:
    """Dark-styled Treeview with scrollbar. First column stretches."""
    frame = tk.Frame(parent, bg=TREE_BG, bd=0)
    tree = ttk.Treeview(
        frame,
        columns=[c[0] for c in columns],
        show="headings",
        style="TT.Treeview",
        selectmode="browse",
    )
    first_col = columns[0][0]
    for col_id, heading, width in columns:
        tree.heading(col_id, text=heading)
        tree.column(col_id, width=width, minwidth=40,
                    stretch=(col_id == first_col))
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)
    return tree, frame


# ── Pages ────────────────────────────────────────────────────────────

class HumidorPage(ctk.CTkFrame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._data: list[dict] = []

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top, text="🚬  Humidor",
                     font=(FONT_DISPLAY, 20, "bold"),
                     text_color=TEXT).grid(row=0, column=0, sticky="w")

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        ctk.CTkEntry(top, textvariable=self._search_var,
                     placeholder_text="Search cigars…",
                     fg_color=CARD, border_color=ACCENT_DIM,
                     text_color=TEXT, width=240, height=34,
                     ).grid(row=0, column=1, sticky="e", padx=(10, 0))

        ctk.CTkButton(top, text="+ Add", width=90, height=34,
                      fg_color=ACCENT, hover_color=ACCENT_HOV,
                      text_color="#1a1917", font=(FONT_TEXT, 13, "bold"),
                      command=self._add,
                      ).grid(row=0, column=2, sticky="e", padx=(8, 0))

        ctk.CTkButton(top, text="Edit", width=76, height=34,
                      fg_color=CARD, hover_color=ACCENT_DIM,
                      text_color=ACCENT, command=self._edit,
                      ).grid(row=0, column=3, sticky="e", padx=(6, 0))

        ctk.CTkButton(top, text="Delete", width=76, height=34,
                      fg_color=CARD, hover_color=DANGER,
                      text_color=TEXT, command=self._delete,
                      ).grid(row=0, column=4, sticky="e", padx=(6, 0))

        ctk.CTkButton(top, text="⟳", width=40, height=34,
                      fg_color=CARD, hover_color=ACCENT_DIM,
                      text_color=ACCENT, command=self._load,
                      ).grid(row=0, column=5, sticky="e", padx=(6, 0))

        cols = [
            ("name",  "Cigar Name",   320),
            ("qty",   "Qty",           50),
            ("avg",   "Avg ★",         68),
            ("mine",  "Mine ★",        68),
            ("len",   "Length",        80),
            ("ring",  "Ring",          50),
            ("smoke", "Smoke (min)",   90),
            ("price", "Price Paid",    80),
        ]
        self._tree, tree_frame = _make_tree(self, cols)
        self._tree.bind("<Double-1>", lambda _e: self._edit())
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 8))

        self._status = ctk.CTkLabel(self, text="",
                                    font=(FONT_TEXT, 11),
                                    text_color=TEXT_DIM)
        self._status.grid(row=2, column=0, sticky="w", padx=22, pady=(0, 10))

        self._load()

    def _load(self) -> None:
        self._data = _load_humidor()
        self._render(self._data)

    def _render(self, rows: list[dict]) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)
        for r in rows:
            lv = _parse_length(str(r.get("length") or ""))
            avg = _sf(r.get("avg_rating"))
            mine = _sf(r.get("my_rating"))
            qty = _sf(r.get("quantity"))
            ring = _sf(r.get("ring_gauge"))
            smoke = _sf(r.get("smoking_time"))
            price = _sf(r.get("price_paid"))
            self._tree.insert("", "end", iid=str(r["id"]), values=(
                r.get("name", ""),
                str(int(qty)) if qty is not None else "0",
                f"{avg:.2f}" if avg is not None else "",
                str(int(mine)) if mine is not None else "",
                f'{lv:.2f}"' if lv else str(r.get("length") or ""),
                str(int(ring)) if ring is not None else "",
                str(int(smoke)) if smoke is not None else "",
                f"${price:.2f}" if price is not None else "",
            ))
        n, total = len(rows), len(self._data)
        if n < total:
            self._status.configure(text=f"Showing {n} of {total} cigars")
        else:
            self._status.configure(
                text=f"{total} cigar{'s' if total != 1 else ''} in humidor")

    def _on_search(self, *_) -> None:
        q = self._search_var.get().lower().strip()
        self._render(self._data if not q else [
            r for r in self._data
            if q in str(r.get("name", "")).lower()
        ])

    def _add(self) -> None:
        _CigarDialog(self.winfo_toplevel(), on_save=self._load)

    def _edit(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a cigar to edit.")
            return
        row_id = int(sel[0])
        record = next((r for r in self._data if r["id"] == row_id), None)
        if record:
            _CigarDialog(self.winfo_toplevel(), on_save=self._load, record=record)

    def _delete(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a cigar to delete.")
            return
        if messagebox.askyesno("Confirm", "Delete selected cigar?"):
            db.humidor_delete(int(sel[0]))
            self._load()


class PickAStickPage(ctk.CTkFrame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="🎲  Pick-a-Stick",
                     font=(FONT_DISPLAY, 20, "bold"),
                     text_color=TEXT,
                     ).grid(row=0, column=0, pady=(20, 0), padx=20, sticky="w")

        # ── Filter bar ──
        bar = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        bar.grid(row=1, column=0, sticky="ew", padx=20, pady=14)
        bar.grid_columnconfigure((0, 1, 2, 3), weight=1)

        def _lbl(text: str, col: int) -> None:
            ctk.CTkLabel(bar, text=text, font=(FONT_TEXT, 11),
                         text_color=TEXT_DIM,
                         ).grid(row=0, column=col, padx=16, pady=(10, 2), sticky="w")

        def _opt(values: list[str], col: int) -> ctk.CTkOptionMenu:
            w = ctk.CTkOptionMenu(bar, values=values,
                                  fg_color=SIDEBAR_BG, button_color=ACCENT_DIM,
                                  button_hover_color=ACCENT, text_color=TEXT,
                                  dropdown_fg_color=CARD, dropdown_text_color=TEXT,
                                  font=(FONT_TEXT, 12), width=160)
            w.set(values[0])
            w.grid(row=1, column=col, padx=16, pady=(2, 14), sticky="w")
            return w

        _lbl("Min Rating", 0)
        self._f_rating = _opt(["Any", "3.5+", "4.0+", "4.5+"], 0)

        _lbl("Ring Gauge", 1)
        self._f_ring = _opt(["Any", "Small (<50)", "Medium (50–54)", "Large (55+)"], 1)

        _lbl("In Stock Only", 2)
        self._f_stock = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(bar, text="", variable=self._f_stock,
                        checkmark_color=ACCENT, fg_color=ACCENT_DIM,
                        border_color=ACCENT_DIM, width=28,
                        ).grid(row=1, column=2, padx=16, pady=(2, 14), sticky="w")

        ctk.CTkButton(bar, text="🎲  Pick a Stick",
                      fg_color=ACCENT, hover_color=ACCENT_HOV,
                      text_color="#1a1917", font=(FONT_DISPLAY, 14, "bold"),
                      height=42, command=self._pick,
                      ).grid(row=0, column=3, rowspan=2, padx=(0, 16), pady=10, sticky="e")

        # ── Result area ──
        self._card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=16)
        self._card.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self._card.grid_columnconfigure(0, weight=1)
        self._card.grid_rowconfigure(0, weight=1)

        self._empty = ctk.CTkLabel(
            self._card,
            text="Set your filters and press 🎲 Pick a Stick",
            font=(FONT_DISPLAY, 16), text_color=TEXT_DIM)
        self._empty.grid(row=0, column=0)

        # Result widgets (placed later on first pick)
        self._result = ctk.CTkFrame(self._card, fg_color="transparent")
        self._r_name = ctk.CTkLabel(self._result, text="",
                                    font=(FONT_DISPLAY, 22, "bold"),
                                    text_color=ACCENT, wraplength=700)
        self._r_name.pack(pady=(36, 6))
        self._r_details = ctk.CTkLabel(self._result, text="",
                                       font=(FONT_TEXT, 14),
                                       text_color=TEXT_DIM)
        self._r_details.pack(pady=(0, 8))
        self._r_ratings = ctk.CTkLabel(self._result, text="",
                                       font=(FONT_DISPLAY, 18),
                                       text_color=TEXT)
        self._r_ratings.pack(pady=(0, 10))
        self._r_notes = ctk.CTkLabel(self._result, text="",
                                     font=(FONT_TEXT, 13),
                                     text_color=TEXT_DIM, wraplength=620)
        self._r_notes.pack(pady=(0, 18))
        ctk.CTkButton(self._result, text="Pick Again",
                      fg_color=ACCENT_DIM, hover_color=ACCENT_HOV,
                      text_color=ACCENT, font=(FONT_TEXT, 13),
                      command=self._pick).pack(pady=(0, 28))

    def _pick(self) -> None:
        pool = _load_humidor()
        if not pool:
            messagebox.showinfo("No Data",
                "No humidor data found.\nGo to Import to export from CigarScanner.")
            return

        if self._f_stock.get():
            pool = [c for c in pool if (c.get("quantity") or 0) > 0]

        rf = self._f_rating.get()
        if rf != "Any":
            threshold = float(rf.rstrip("+"))
            pool = [c for c in pool
                    if _sf(c.get("my_rating")) is not None
                    and _sf(c.get("my_rating")) >= threshold]  # type: ignore[operator]

        ring_f = self._f_ring.get()
        if ring_f != "Any":
            def _ring_ok(c: dict) -> bool:
                r = _sf(c.get("ring_gauge"))
                if r is None:
                    return True
                if "Small" in ring_f:
                    return r < 50
                if "Medium" in ring_f:
                    return 50 <= r <= 54
                return r >= 55
            pool = [c for c in pool if _ring_ok(c)]

        if not pool:
            messagebox.showinfo("No Matches",
                "No cigars matched those filters.\nTry loosening the criteria.")
            return

        weights = [max(1, int(c.get("quantity") or 1)) for c in pool]
        winner = random.choices(pool, weights=weights, k=1)[0]
        self._spin(pool, winner)

    def _spin(self, pool: list[dict], winner: dict) -> None:
        self._empty.grid_remove()
        self._result.grid(row=0, column=0, sticky="n", pady=10)
        names = [c["Name"] for c in pool]
        steps = 14

        def _step(i: int) -> None:
            if i < steps:
                self._r_name.configure(text=random.choice(names))
                self._r_details.configure(text="")
                self._r_ratings.configure(text="")
                self._r_notes.configure(text="")
                self.after(60 + i * 18, lambda: _step(i + 1))
            else:
                self._show(winner)

        _step(0)

    def _show(self, c: dict) -> None:
        self._r_name.configure(text=c.get("name", ""))

        lv = _parse_length(str(c.get("length") or ""))
        ring = _sf(c.get("ring_gauge"))
        smoke_f = _sf(c.get("smoking_time"))
        parts = []
        if lv:
            parts.append(f'{lv:.2f}"')
        if ring:
            parts.append(f"Ring {int(ring)}")
        if smoke_f is not None:
            parts.append(f"~{int(smoke_f)} min")
        self._r_details.configure(text="  ·  ".join(parts))

        avg = _sf(c.get("avg_rating"))
        mine = _sf(c.get("my_rating"))
        qty = c.get("quantity")
        rparts = []
        if avg is not None:
            rparts.append(f"★ {avg:.2f} avg")
        if mine is not None:
            rparts.append(f"★ {int(mine)} mine")
        if qty not in (None, ""):
            rparts.append(f"× {int(qty)} in humidor")
        self._r_ratings.configure(text="   ".join(rparts))

        note = str(c.get("notes") or "").strip()
        self._r_notes.configure(text=note)


class PipeTobaccoPage(ctk.CTkFrame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(top, text="🌿  Pipe Tobacco",
                     font=(FONT_DISPLAY, 20, "bold"),
                     text_color=TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(top, text="+ Add", width=90, height=34,
                      fg_color=ACCENT, hover_color=ACCENT_HOV,
                      text_color="#1a1917", font=(FONT_TEXT, 13, "bold"),
                      command=self._add,
                      ).grid(row=0, column=1, sticky="e")
        ctk.CTkButton(top, text="Delete", width=80, height=34,
                      fg_color=CARD, hover_color=DANGER,
                      text_color=TEXT, command=self._delete,
                      ).grid(row=0, column=2, sticky="e", padx=(8, 0))

        cols = [
            ("name",  "Name",     240),
            ("brand", "Brand",    130),
            ("blend", "Blend",    130),
            ("cut",   "Cut",      100),
            ("str",   "Strength", 100),
            ("qty",   "Qty (oz)",  75),
            ("rate",  "Rating",    65),
        ]
        self._tree, tree_frame = _make_tree(self, cols)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self._load()

    def _load(self) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)
        for r in db.pipe_all():
            qty = _sf(r.get("qty_oz"))
            self._tree.insert("", "end", iid=str(r["id"]), values=(
                r.get("name", ""),
                r.get("brand", ""),
                r.get("blend_type", ""),
                r.get("cut", ""),
                r.get("strength", ""),
                f"{qty:.1f}" if qty is not None else "",
                str(r.get("rating") or ""),
            ))

    def _add(self) -> None:
        _TobaccoDialog(self.winfo_toplevel(), on_save=self._load)

    def _delete(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a row to delete.")
            return
        if messagebox.askyesno("Confirm", "Delete selected tobacco?"):
            db.pipe_delete(int(sel[0]))
            self._load()


class JournalPage(ctk.CTkFrame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(top, text="📖  Smoke Journal",
                     font=(FONT_DISPLAY, 20, "bold"),
                     text_color=TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(top, text="+ Log", width=90, height=34,
                      fg_color=ACCENT, hover_color=ACCENT_HOV,
                      text_color="#1a1917", font=(FONT_TEXT, 13, "bold"),
                      command=self._add,
                      ).grid(row=0, column=1, sticky="e")
        ctk.CTkButton(top, text="Delete", width=80, height=34,
                      fg_color=CARD, hover_color=DANGER,
                      text_color=TEXT, command=self._delete,
                      ).grid(row=0, column=2, sticky="e", padx=(8, 0))

        cols = [
            ("date",    "Date",     90),
            ("type",    "Type",     60),
            ("name",    "Name",    240),
            ("rating",  "★",        40),
            ("min",     "Min",      40),
            ("pairing", "Pairing", 130),
            ("draw",    "Draw",     90),
            ("flavor",  "Flavors", 160),
            ("notes",   "Notes",   220),
        ]
        self._tree, tree_frame = _make_tree(self, cols)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self._load()

    def _load(self) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)
        for r in db.journal_all():
            notes = str(r.get("notes") or "")
            self._tree.insert("", "end", iid=str(r["id"]), values=(
                r.get("date", ""),
                r.get("type", "").capitalize(),
                r.get("name", ""),
                str(r.get("rating") or ""),
                str(r.get("duration") or ""),
                r.get("pairing", ""),
                r.get("draw", ""),
                r.get("flavor", ""),
                notes[:60] + ("…" if len(notes) > 60 else ""),
            ))

    def _add(self) -> None:
        _JournalDialog(self.winfo_toplevel(), on_save=self._load)

    def _delete(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a row to delete.")
            return
        if messagebox.askyesno("Confirm", "Delete this journal entry?"):
            db.journal_delete(int(sel[0]))
            self._load()


class ImportPage(ctk.CTkFrame):
    def __init__(self, parent: tk.Misc, on_imported) -> None:
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self._on_imported = on_imported
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text="📥  Import from CigarScanner",
                     font=(FONT_DISPLAY, 20, "bold"),
                     text_color=TEXT,
                     ).grid(row=0, column=0, pady=(20, 0), padx=20, sticky="w")

        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=16)
        card.grid(row=1, column=0, padx=80, pady=40, sticky="")

        ctk.CTkLabel(card, text="How it works",
                     font=(FONT_DISPLAY, 16, "bold"),
                     text_color=ACCENT).pack(pady=(28, 10))

        ctk.CTkLabel(card,
            text=(
                "1. Click  Open Exporter  — a Terminal window opens and runs\n"
                "   the CigarScanner browser automatically.\n\n"
                "2. Complete any Cloudflare check, then log in if prompted.\n\n"
                "3. Open your humidor and scroll the cigar list top-to-bottom.\n\n"
                "4. Press Enter in the Terminal when the full list is visible.\n\n"
                "5. The script exports  humidor_export.csv  into the output/ folder.\n\n"
                "6. Click  Reload Humidor  below to refresh the app with new data."
            ),
            font=(FONT_TEXT, 13), text_color=TEXT_DIM,
            justify="left", anchor="w",
            ).pack(padx=32, pady=(0, 28))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(pady=(0, 10))

        ctk.CTkButton(btn_row, text="Open Exporter",
                      fg_color=ACCENT, hover_color=ACCENT_HOV,
                      text_color="#1a1917", font=(FONT_DISPLAY, 13, "bold"),
                      height=42, width=190, command=self._open_terminal,
                      ).grid(row=0, column=0, padx=8)

        ctk.CTkButton(btn_row, text="⟳  Reload Humidor",
                      fg_color=CARD, hover_color=ACCENT_DIM,
                      text_color=ACCENT, font=(FONT_TEXT, 13),
                      height=42, width=170, command=self._reload,
                      ).grid(row=0, column=1, padx=8)

        self._status = ctk.CTkLabel(card, text="",
                                    font=(FONT_TEXT, 12),
                                    text_color=TEXT_DIM)
        self._status.pack(pady=(4, 28))

    def _open_terminal(self) -> None:
        run_script = PROJECT_DIR / ("run.bat" if _OS == "Windows" else "run.sh")
        try:
            if _OS == "Darwin":
                escaped = str(run_script).replace("\\", "\\\\").replace('"', '\\"')
                subprocess.Popen([
                    "osascript", "-e",
                    f'tell application "Terminal" to do script "bash \\"{escaped}\\""',
                ])
            elif _OS == "Windows":
                subprocess.Popen(["cmd.exe", "/c", "start", "cmd.exe", "/k", str(run_script)])
            else:
                launched = False
                for term, flag in [
                    ("x-terminal-emulator", "-e"),
                    ("gnome-terminal", "--"),
                    ("xterm", "-e"),
                    ("konsole", "-e"),
                ]:
                    try:
                        subprocess.Popen([term, flag, "bash", str(run_script)])
                        launched = True
                        break
                    except FileNotFoundError:
                        continue
                if not launched:
                    messagebox.showerror("Error",
                        "No terminal emulator found.\nRun run.sh manually.")
                    return
            self._status.configure(
                text="Terminal opened — follow the steps above, then click Reload.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open Terminal:\n{e}")

    def _reload(self) -> None:
        csv_rows = _load_humidor_csv()
        if csv_rows:
            db.humidor_upsert_from_csv(csv_rows)
        self._on_imported()
        count = len(db.humidor_all())
        self._status.configure(text=f"Reloaded — {count} cigars now in humidor.")


# ── Dialogs ──────────────────────────────────────────────────────────

class _BaseDialog(ctk.CTkToplevel):
    """Shared plumbing for modal entry dialogs."""

    def __init__(self, parent: tk.Misc, title: str, size: str) -> None:
        super().__init__(parent)
        self.title(title)
        self.geometry(size)
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.grab_set()
        self.lift()
        self.after(50, self.focus)

    # ── Widget factories ──
    def _entry(self, parent: tk.Misc) -> ctk.CTkEntry:
        return ctk.CTkEntry(parent, fg_color=CARD, border_color=ACCENT_DIM,
                            text_color=TEXT)

    def _opt(self, parent: tk.Misc, values: list[str]) -> ctk.CTkOptionMenu:
        w = ctk.CTkOptionMenu(parent, values=values,
                              fg_color=CARD, button_color=ACCENT_DIM,
                              button_hover_color=ACCENT, text_color=TEXT,
                              dropdown_fg_color=CARD, dropdown_text_color=TEXT)
        w.set(values[0])
        return w

    def _textbox(self, parent: tk.Misc, height: int = 80) -> ctk.CTkTextbox:
        return ctk.CTkTextbox(parent, height=height, fg_color=CARD,
                              border_color=ACCENT_DIM, text_color=TEXT)

    def _lbl(self, parent: tk.Misc, text: str) -> None:
        ctk.CTkLabel(parent, text=text, font=(FONT_TEXT, 12),
                     text_color=TEXT_DIM, anchor="w").pack(fill="x", pady=(8, 2))

    # ── Value extractors ──
    def _v(self, w: tk.Misc) -> str:
        if isinstance(w, ctk.CTkEntry):
            return w.get().strip()
        if isinstance(w, ctk.CTkOptionMenu):
            v = w.get()
            return "" if v == "—" else v
        if isinstance(w, ctk.CTkTextbox):
            return w.get("1.0", "end").strip()
        return ""

    def _fi(self, w: tk.Misc) -> int | None:
        try:
            return int(self._v(w))
        except (ValueError, TypeError):
            return None

    def _ff(self, w: tk.Misc) -> float | None:
        try:
            return float(self._v(w))
        except (ValueError, TypeError):
            return None

    def _btn_row(self, on_save) -> None:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=14)
        row.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(row, text="Cancel", fg_color=CARD,
                      hover_color=DANGER, text_color=TEXT,
                      command=self.destroy,
                      ).grid(row=0, column=0, padx=(0, 6), sticky="ew")
        ctk.CTkButton(row, text="Save", fg_color=ACCENT,
                      hover_color=ACCENT_HOV, text_color="#1a1917",
                      command=on_save,
                      ).grid(row=0, column=1, padx=(6, 0), sticky="ew")


class _CigarDialog(_BaseDialog):
    def __init__(self, parent: tk.Misc, on_save, record: dict | None = None) -> None:
        super().__init__(parent, "Edit Cigar" if record else "Add Cigar", "480x620")
        self._cb = on_save
        self._record = record

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=10)

        def _prefill(w: ctk.CTkEntry, key: str) -> None:
            if record and record.get(key) is not None:
                w.insert(0, str(record[key]))

        def _prefill_int(w: ctk.CTkEntry, key: str) -> None:
            if record:
                v = _sf(record.get(key))
                if v is not None:
                    w.insert(0, str(int(v)))

        self._lbl(body, "Name *")
        self.e_name = self._entry(body)
        _prefill(self.e_name, "name")
        self.e_name.pack(fill="x")

        self._lbl(body, "Brand")
        self.e_brand = self._entry(body)
        _prefill(self.e_brand, "brand")
        self.e_brand.pack(fill="x")

        self._lbl(body, "Quantity")
        self.e_qty = self._entry(body)
        _prefill_int(self.e_qty, "quantity")
        self.e_qty.pack(fill="x")

        self._lbl(body, "My Rating (1–100)")
        self.e_rating = self._entry(body)
        _prefill_int(self.e_rating, "my_rating")
        self.e_rating.pack(fill="x")

        self._lbl(body, 'Length  (e.g.  6"  or  4"7/8)')
        self.e_len = self._entry(body)
        _prefill(self.e_len, "length")
        self.e_len.pack(fill="x")

        self._lbl(body, "Ring Gauge")
        self.e_ring = self._entry(body)
        _prefill_int(self.e_ring, "ring_gauge")
        self.e_ring.pack(fill="x")

        self._lbl(body, "Smoking Time (minutes)")
        self.e_smoke = self._entry(body)
        _prefill_int(self.e_smoke, "smoking_time")
        self.e_smoke.pack(fill="x")

        self._lbl(body, "Price Paid ($)")
        self.e_price = self._entry(body)
        if record and _sf(record.get("price_paid")) is not None:
            self.e_price.insert(0, f"{_sf(record['price_paid']):.2f}")
        self.e_price.pack(fill="x")

        self._lbl(body, "Notes")
        self.e_notes = self._textbox(body)
        if record and record.get("notes"):
            self.e_notes.insert("1.0", record["notes"])
        self.e_notes.pack(fill="x")

        self._btn_row(self._save)

    def _save(self) -> None:
        name = self._v(self.e_name)
        if not name:
            messagebox.showwarning("Required", "Name is required.", parent=self)
            return
        args = (
            name,
            self._v(self.e_brand),
            self._fi(self.e_qty),
            self._fi(self.e_rating),
            self._v(self.e_len),
            self._fi(self.e_ring),
            self._fi(self.e_smoke),
            self._ff(self.e_price),
            self._v(self.e_notes),
        )
        if self._record:
            db.humidor_update(self._record["id"], *args)
        else:
            db.humidor_add(*args)
        self._cb()
        self.destroy()


class _TobaccoDialog(_BaseDialog):
    def __init__(self, parent: tk.Misc, on_save) -> None:
        super().__init__(parent, "Add Pipe Tobacco", "480x640")
        self._cb = on_save

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=10)

        self._lbl(body, "Name *")
        self.e_name = self._entry(body)
        self.e_name.pack(fill="x")

        self._lbl(body, "Brand")
        self.e_brand = self._entry(body)
        self.e_brand.pack(fill="x")

        self._lbl(body, "Blend Type")
        self.e_blend = self._opt(body, [
            "—", "Virginia", "Burley", "Aromatic", "English/Balkan",
            "Virginia/Burley", "Latakia", "Perique Blend", "Maryland",
        ])
        self.e_blend.pack(fill="x")

        self._lbl(body, "Cut")
        self.e_cut = self._opt(body, [
            "—", "Ribbon", "Flake", "Plug", "Shag",
            "Crumble Cake", "Cube Cut", "Ready Rubbed",
        ])
        self.e_cut.pack(fill="x")

        self._lbl(body, "Strength")
        self.e_str = self._opt(body, [
            "—", "Mild", "Mild-Medium", "Medium", "Medium-Full", "Full",
        ])
        self.e_str.pack(fill="x")

        self._lbl(body, "Tin Size (oz)")
        self.e_tin = self._entry(body)
        self.e_tin.pack(fill="x")

        self._lbl(body, "Qty Remaining (oz)")
        self.e_qty = self._entry(body)
        self.e_qty.pack(fill="x")

        self._lbl(body, "Price Paid ($)")
        self.e_price = self._entry(body)
        self.e_price.pack(fill="x")

        self._lbl(body, "Rating (1–100)")
        self.e_rating = self._entry(body)
        self.e_rating.pack(fill="x")

        self._lbl(body, "Notes")
        self.e_notes = self._textbox(body)
        self.e_notes.pack(fill="x")

        self._btn_row(self._save)

    def _save(self) -> None:
        name = self._v(self.e_name)
        if not name:
            messagebox.showwarning("Required", "Name is required.", parent=self)
            return
        db.pipe_add(name, self._v(self.e_brand), self._v(self.e_blend),
                    self._v(self.e_cut), self._v(self.e_str),
                    self._ff(self.e_tin), self._ff(self.e_qty),
                    self._ff(self.e_price), self._fi(self.e_rating),
                    self._v(self.e_notes))
        self._cb()
        self.destroy()


class _JournalDialog(_BaseDialog):
    def __init__(self, parent: tk.Misc, on_save) -> None:
        super().__init__(parent, "Log Smoke Session", "480x700")
        self._cb = on_save

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=10)

        self._lbl(body, "Date")
        self.e_date = self._entry(body)
        self.e_date.insert(0, str(_today.today()))
        self.e_date.pack(fill="x")

        self._lbl(body, "Type")
        self.e_type = self._opt(body, ["Cigar", "Pipe"])
        self.e_type.pack(fill="x")

        self._lbl(body, "Name *")
        self.e_name = self._entry(body)
        self.e_name.pack(fill="x")

        self._lbl(body, "Rating (1–100)")
        self.e_rating = self._entry(body)
        self.e_rating.pack(fill="x")

        self._lbl(body, "Duration (minutes)")
        self.e_dur = self._entry(body)
        self.e_dur.pack(fill="x")

        self._lbl(body, "Pairing (drink / food)")
        self.e_pair = self._entry(body)
        self.e_pair.pack(fill="x")

        self._lbl(body, "Draw")
        self.e_draw = self._opt(body, [
            "—", "Easy", "Perfect", "Slightly Tight", "Tight",
        ])
        self.e_draw.pack(fill="x")

        self._lbl(body, "Burn")
        self.e_burn = self._opt(body, [
            "—", "Even", "Slight Touch-Up", "Needed Relighting",
        ])
        self.e_burn.pack(fill="x")

        self._lbl(body, "Flavor Notes")
        self.e_flavor = self._entry(body)
        self.e_flavor.pack(fill="x")

        self._lbl(body, "Overall Notes")
        self.e_notes = self._textbox(body, height=90)
        self.e_notes.pack(fill="x", pady=(0, 6))

        self._btn_row(self._save)

    def _save(self) -> None:
        name = self._v(self.e_name)
        if not name:
            messagebox.showwarning("Required", "Name is required.", parent=self)
            return
        db.journal_add(
            self._v(self.e_date),
            self._v(self.e_type).lower(),
            name,
            self._fi(self.e_rating),
            self._fi(self.e_dur),
            self._v(self.e_pair),
            self._v(self.e_draw),
            self._v(self.e_burn),
            self._v(self.e_flavor),
            self._v(self.e_notes),
        )
        self._cb()
        self.destroy()


class SmokingPipesPage(ctk.CTkFrame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(top, text="🪵  My Pipes",
                     font=(FONT_DISPLAY, 20, "bold"),
                     text_color=TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(top, text="+ Add", width=90, height=34,
                      fg_color=ACCENT, hover_color=ACCENT_HOV,
                      text_color="#1a1917", font=(FONT_TEXT, 13, "bold"),
                      command=self._add,
                      ).grid(row=0, column=1, sticky="e")
        ctk.CTkButton(top, text="Delete", width=80, height=34,
                      fg_color=CARD, hover_color=DANGER,
                      text_color=TEXT, command=self._delete,
                      ).grid(row=0, column=2, sticky="e", padx=(8, 0))

        cols = [
            ("name",      "Name / Model",  220),
            ("maker",     "Maker",         140),
            ("shape",     "Shape",         110),
            ("material",  "Material",      110),
            ("finish",    "Finish",        100),
            ("condition", "Condition",     110),
            ("date_acq",  "Acquired",       90),
            ("price",     "Price",          70),
        ]
        self._tree, tree_frame = _make_tree(self, cols)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self._load()

    def _load(self) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)
        for r in db.spipe_all():
            price = _sf(r.get("price"))
            self._tree.insert("", "end", iid=str(r["id"]), values=(
                r.get("name", ""),
                r.get("maker", ""),
                r.get("shape", ""),
                r.get("material", ""),
                r.get("finish", ""),
                r.get("condition", ""),
                r.get("date_acq", ""),
                f"${price:.2f}" if price is not None else "",
            ))

    def _add(self) -> None:
        _SmokingPipeDialog(self.winfo_toplevel(), on_save=self._load)

    def _delete(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a pipe to delete.")
            return
        if messagebox.askyesno("Confirm", "Delete this pipe?"):
            db.spipe_delete(int(sel[0]))
            self._load()


class _SmokingPipeDialog(_BaseDialog):
    def __init__(self, parent: tk.Misc, on_save) -> None:
        super().__init__(parent, "Add Smoking Pipe", "480x620")
        self._cb = on_save

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=10)

        self._lbl(body, "Name / Model *")
        self.e_name = self._entry(body)
        self.e_name.pack(fill="x")

        self._lbl(body, "Maker / Brand")
        self.e_maker = self._entry(body)
        self.e_maker.pack(fill="x")

        self._lbl(body, "Shape")
        self.e_shape = self._opt(body, [
            "—", "Billiard", "Bent", "Dublin", "Bulldog", "Churchwarden",
            "Brandy / Apple", "Egg", "Volcano", "Poker", "Calabash",
            "Rhodesian", "Canadian", "Lovat", "Prince", "Freehand",
        ])
        self.e_shape.pack(fill="x")

        self._lbl(body, "Material")
        self.e_material = self._opt(body, [
            "—", "Briar", "Meerschaum", "Corncob", "Clay",
            "Morta (Bog Oak)", "Cherrywood", "Rosewood", "Other",
        ])
        self.e_material.pack(fill="x")

        self._lbl(body, "Finish")
        self.e_finish = self._opt(body, [
            "—", "Smooth", "Sandblasted", "Rusticated", "Carved", "Natural",
        ])
        self.e_finish.pack(fill="x")

        self._lbl(body, "Condition")
        self.e_condition = self._opt(body, [
            "—", "New", "Excellent", "Good", "Fair", "Estate / Restoration",
        ])
        self.e_condition.pack(fill="x")

        self._lbl(body, "Date Acquired")
        self.e_date = self._entry(body)
        self.e_date.pack(fill="x")

        self._lbl(body, "Price Paid ($)")
        self.e_price = self._entry(body)
        self.e_price.pack(fill="x")

        self._lbl(body, "Notes")
        self.e_notes = self._textbox(body, height=80)
        self.e_notes.pack(fill="x", pady=(0, 6))

        self._btn_row(self._save)

    def _save(self) -> None:
        name = self._v(self.e_name)
        if not name:
            messagebox.showwarning("Required", "Name is required.", parent=self)
            return
        db.spipe_add(
            name,
            self._v(self.e_maker),
            self._v(self.e_shape),
            self._v(self.e_material),
            self._v(self.e_finish),
            self._v(self.e_condition),
            self._v(self.e_date),
            self._ff(self.e_price),
            self._v(self.e_notes),
        )
        self._cb()
        self.destroy()


# ── Sidebar navigation button ────────────────────────────────────────

class _NavBtn(ctk.CTkButton):
    def __init__(self, parent: tk.Misc, text: str, command) -> None:
        super().__init__(parent, text=text, command=command,
                         anchor="w", fg_color="transparent",
                         text_color=TEXT_DIM, hover_color=CARD,
                         font=(FONT_DISPLAY, 13),
                         corner_radius=8, height=44)

    def set_active(self, active: bool) -> None:
        if active:
            self.configure(fg_color=ACCENT_DIM, text_color=ACCENT)
        else:
            self.configure(fg_color="transparent", text_color=TEXT_DIM)


# ── Main window ──────────────────────────────────────────────────────

class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("TobaccoTown")
        self.geometry("1240x760")
        self.minsize(900, 600)
        self.configure(fg_color=BG)
        self.tk.call("tk", "appname", "TobaccoTown")

        _style_treeview(self)
        db.init()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ── Sidebar ──
        sb = ctk.CTkFrame(self, width=195, fg_color=SIDEBAR_BG, corner_radius=0)
        sb.grid(row=0, column=0, sticky="ns")
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)
        sb.grid_rowconfigure(10, weight=1)

        ctk.CTkLabel(sb, text="🚬",
                     font=(FONT_DISPLAY, 34),
                     text_color=ACCENT).grid(row=0, column=0, pady=(30, 4))
        ctk.CTkLabel(sb, text="TobaccoTown",
                     font=(FONT_DISPLAY, 14, "bold"),
                     text_color=TEXT).grid(row=1, column=0, pady=(0, 26))

        nav = [
            ("humidor",  "🚬  Humidor"),
            ("pick",     "🎲  Pick-a-Stick"),
            ("pipe",     "🌿  Pipe Tobacco"),
            ("mypipes",  "🪵  My Pipes"),
            ("journal",  "📖  Journal"),
            ("import",   "📥  Import"),
        ]
        self._btns: dict[str, _NavBtn] = {}
        for i, (key, label) in enumerate(nav):
            btn = _NavBtn(sb, label, lambda k=key: self._show(k))
            btn.grid(row=i + 2, column=0, sticky="ew", padx=10, pady=2)
            self._btns[key] = btn

        # ── Content ──
        content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)

        self._pages: dict[str, ctk.CTkFrame] = {
            "humidor":  HumidorPage(content),
            "pick":     PickAStickPage(content),
            "pipe":     PipeTobaccoPage(content),
            "mypipes":  SmokingPipesPage(content),
            "journal":  JournalPage(content),
            "import":   ImportPage(content, on_imported=self._on_import),
        }
        for page in self._pages.values():
            page.grid(row=0, column=0, sticky="nsew")

        self._show("humidor")
        self.after(100, self._force_front)

    def _force_front(self) -> None:
        self.attributes("-topmost", True)
        self.focus_force()
        self.update_idletasks()
        self.update()
        self.after(500, lambda: self.attributes("-topmost", False))

    def _show(self, key: str) -> None:
        self._pages[key].tkraise()
        for k, btn in self._btns.items():
            btn.set_active(k == key)

    def _on_import(self) -> None:
        self._pages["humidor"]._load()  # type: ignore[attr-defined]


def _set_macos_dock_icon() -> None:
    icon_path = PROJECT_DIR / "assets" / "icon.png"
    if not icon_path.exists():
        return
    try:
        from AppKit import NSApplication, NSImage
        ns_img = NSImage.alloc().initWithContentsOfFile_(str(icon_path))
        NSApplication.sharedApplication().setApplicationIconImage_(ns_img)
    except Exception:
        pass


def main() -> None:
    if _OS == "Darwin":
        _set_macos_dock_icon()
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
