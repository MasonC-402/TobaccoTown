"""SQLite persistence layer for TobaccoTown."""

import sqlite3
from datetime import date
from pathlib import Path

_DB = Path(__file__).resolve().parent / "data" / "tobaccotown.db"


def _conn():
    _DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(str(_DB))
    c.row_factory = sqlite3.Row
    return c


def init():
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS humidor_cigar (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT NOT NULL,
                brand        TEXT    DEFAULT '',
                quantity     INTEGER DEFAULT 0,
                avg_rating   REAL,
                my_rating    INTEGER,
                length       TEXT    DEFAULT '',
                ring_gauge   INTEGER,
                smoking_time INTEGER,
                price_paid   REAL,
                notes        TEXT    DEFAULT '',
                date_added   TEXT    DEFAULT (date('now'))
            );
            CREATE TABLE IF NOT EXISTS pipe_tobacco (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                brand      TEXT    DEFAULT '',
                blend_type TEXT    DEFAULT '',
                cut        TEXT    DEFAULT '',
                strength   TEXT    DEFAULT '',
                tin_oz     REAL,
                qty_oz     REAL,
                price      REAL,
                rating     INTEGER,
                notes      TEXT    DEFAULT '',
                date_added TEXT    DEFAULT (date('now'))
            );
            CREATE TABLE IF NOT EXISTS smoking_pipe (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                maker      TEXT    DEFAULT '',
                shape      TEXT    DEFAULT '',
                material   TEXT    DEFAULT '',
                finish     TEXT    DEFAULT '',
                condition  TEXT    DEFAULT '',
                date_acq   TEXT    DEFAULT '',
                price      REAL,
                notes      TEXT    DEFAULT '',
                date_added TEXT    DEFAULT (date('now'))
            );
            CREATE TABLE IF NOT EXISTS journal (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                date       TEXT    DEFAULT (date('now')),
                type       TEXT    NOT NULL DEFAULT 'cigar',
                name       TEXT    NOT NULL DEFAULT '',
                rating     INTEGER,
                duration   INTEGER,
                pairing    TEXT    DEFAULT '',
                draw       TEXT    DEFAULT '',
                burn       TEXT    DEFAULT '',
                flavor     TEXT    DEFAULT '',
                notes      TEXT    DEFAULT '',
                created_at TEXT    DEFAULT (datetime('now'))
            );
        """)


def humidor_all():
    with _conn() as c:
        return [dict(r) for r in
                c.execute("SELECT * FROM humidor_cigar ORDER BY name").fetchall()]


def humidor_add(name, brand, quantity, my_rating, length, ring_gauge,
                smoking_time, price_paid, notes):
    with _conn() as c:
        c.execute(
            "INSERT INTO humidor_cigar"
            " (name,brand,quantity,my_rating,length,ring_gauge,smoking_time,price_paid,notes)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (name, brand, quantity, my_rating, length, ring_gauge,
             smoking_time, price_paid, notes),
        )


def humidor_update(row_id, name, brand, quantity, my_rating, length,
                   ring_gauge, smoking_time, price_paid, notes):
    with _conn() as c:
        c.execute(
            "UPDATE humidor_cigar"
            " SET name=?,brand=?,quantity=?,my_rating=?,length=?,ring_gauge=?,"
            "     smoking_time=?,price_paid=?,notes=?"
            " WHERE id=?",
            (name, brand, quantity, my_rating, length, ring_gauge,
             smoking_time, price_paid, notes, row_id),
        )


def humidor_delete(row_id):
    with _conn() as c:
        c.execute("DELETE FROM humidor_cigar WHERE id=?", (row_id,))


def humidor_upsert_from_csv(rows):
    """Import CigarScanner CSV rows into the native humidor table (upsert by name)."""
    with _conn() as c:
        for r in rows:
            name = str(r.get("Name") or "").strip()
            if not name:
                continue
            existing = c.execute(
                "SELECT id FROM humidor_cigar WHERE name=?", (name,)
            ).fetchone()
            qty = r.get("Quantity")
            my_r = r.get("MyRating")
            avg_r = r.get("AvgRating")
            ring = r.get("RingGauge")
            smoke = r.get("SmokingTime")
            price = r.get("PricePaid")
            length = str(r.get("Length") or "")
            notes = str(r.get("MyNote") or r.get("MyComment") or "")
            if existing:
                c.execute(
                    "UPDATE humidor_cigar"
                    " SET quantity=?,avg_rating=?,my_rating=?,length=?,"
                    "     ring_gauge=?,smoking_time=?,price_paid=?,notes=?"
                    " WHERE id=?",
                    (qty, avg_r, my_r, length, ring, smoke, price, notes, existing[0]),
                )
            else:
                c.execute(
                    "INSERT INTO humidor_cigar"
                    " (name,quantity,avg_rating,my_rating,length,ring_gauge,"
                    "  smoking_time,price_paid,notes)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    (name, qty, avg_r, my_r, length, ring, smoke, price, notes),
                )


def pipe_all():
    with _conn() as c:
        return [dict(r) for r in
                c.execute("SELECT * FROM pipe_tobacco ORDER BY name").fetchall()]


def pipe_add(name, brand, blend_type, cut, strength,
             tin_oz, qty_oz, price, rating, notes):
    with _conn() as c:
        c.execute(
            "INSERT INTO pipe_tobacco"
            " (name,brand,blend_type,cut,strength,tin_oz,qty_oz,price,rating,notes)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (name, brand, blend_type, cut, strength,
             tin_oz, qty_oz, price, rating, notes),
        )


def pipe_delete(row_id):
    with _conn() as c:
        c.execute("DELETE FROM pipe_tobacco WHERE id=?", (row_id,))


def spipe_all():
    with _conn() as c:
        return [dict(r) for r in
                c.execute("SELECT * FROM smoking_pipe ORDER BY name").fetchall()]


def spipe_add(name, maker, shape, material, finish, condition, date_acq, price, notes):
    with _conn() as c:
        c.execute(
            "INSERT INTO smoking_pipe"
            " (name,maker,shape,material,finish,condition,date_acq,price,notes)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (name, maker, shape, material, finish, condition, date_acq, price, notes),
        )


def spipe_delete(row_id):
    with _conn() as c:
        c.execute("DELETE FROM smoking_pipe WHERE id=?", (row_id,))


def journal_all():
    with _conn() as c:
        return [dict(r) for r in
                c.execute(
                    "SELECT * FROM journal ORDER BY date DESC, id DESC"
                ).fetchall()]


def journal_add(date_str, type_, name, rating, duration,
                pairing, draw, burn, flavor, notes):
    with _conn() as c:
        c.execute(
            "INSERT INTO journal"
            " (date,type,name,rating,duration,pairing,draw,burn,flavor,notes)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (date_str or str(date.today()), type_, name,
             rating, duration, pairing, draw, burn, flavor, notes),
        )


def journal_delete(row_id):
    with _conn() as c:
        c.execute("DELETE FROM journal WHERE id=?", (row_id,))
