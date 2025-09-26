"""SQLite helpers centralised in a single module.

This module is intentionally small so other parts of the project can
depend on a single place for database connections, schema management and
common queries.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Mapping, Optional

DB_PATH = Path(__file__).parent.parent / "data" / "museums.sqlite"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS museum_visitors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rank_2024 INTEGER,
    museum_name TEXT NOT NULL,
    country TEXT,
    city TEXT,
    visitors_2024 INTEGER,
    raw_visitors_str TEXT,
    page_title TEXT,
    page_revision INTEGER,
    extracted_at_utc INTEGER,
    city_id INTEGER REFERENCES city(id),
    UNIQUE(museum_name, city, page_revision) ON CONFLICT IGNORE
);
CREATE INDEX IF NOT EXISTS idx_museum_city ON museum_visitors (museum_name, city);
CREATE INDEX IF NOT EXISTS idx_rank ON museum_visitors (rank_2024);

CREATE TABLE IF NOT EXISTS city (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country TEXT NOT NULL,
    city TEXT NOT NULL,
    population INTEGER,
    year INTEGER,
    source TEXT NOT NULL,
    UNIQUE(country, city)
);
CREATE INDEX IF NOT EXISTS idx_city_name ON city (country, city);
"""


def get_conn() -> sqlite3.Connection:
    """Return a connection with foreign keys enabled."""

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_city_id_column(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(museum_visitors)")}
    if "city_id" not in columns:
        conn.execute("ALTER TABLE museum_visitors ADD COLUMN city_id INTEGER REFERENCES city(id)")


def init_schema() -> None:
    """Ensure both museum and city tables exist."""

    with get_conn() as conn:
        conn.executescript(SCHEMA_SQL)
        _ensure_city_id_column(conn)


def insert_museum_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    page_title: str,
    page_revision: int,
    extracted_at_utc: Optional[int] = None,
) -> int:
    """Bulk insert museum rows. Returns the number of input rows."""

    if extracted_at_utc is None:
        import time

        extracted_at_utc = int(time.time())

    payload = [
        {
            **row,
            "page_title": page_title,
            "page_revision": page_revision,
            "extracted_at_utc": extracted_at_utc,
        }
        for row in rows
    ]

    if not payload:
        return 0

    init_schema()
    with get_conn() as conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO museum_visitors (
                rank_2024,
                museum_name,
                country,
                city,
                visitors_2024,
                raw_visitors_str,
                page_title,
                page_revision,
                extracted_at_utc
            ) VALUES (
                :rank_2024,
                :museum_name,
                :country,
                :city,
                :visitors_2024,
                :raw_visitors_str,
                :page_title,
                :page_revision,
                :extracted_at_utc
            )
            """,
            payload,
        )
    return len(payload)


def upsert_cities(records: Iterable[Mapping[str, object]]) -> int:
    """Insert or update city rows and relink museums.

    Returns the number of processed records.
    """

    data = list(records)
    if not data:
        return 0

    init_schema()
    with get_conn() as conn:
        conn.executemany(
            """
            INSERT INTO city (country, city, population, year, source)
            VALUES (:country, :city, :population, :year, :source)
            ON CONFLICT(country, city) DO UPDATE SET
                population = excluded.population,
                year = excluded.year,
                source = excluded.source
            """,
            data,
        )
        conn.execute(
            """
            UPDATE museum_visitors
            SET city_id = (
                SELECT id
                FROM city
                WHERE city.country = museum_visitors.country
                  AND city.city = museum_visitors.city
            )
            WHERE country IS NOT NULL
              AND city IS NOT NULL
            """
        )
    return len(data)


def fetch_museums(limit: Optional[int] = None) -> list[tuple]:
    """Return museum rows ordered by rank."""

    query = "SELECT rank_2024, museum_name, country, city, visitors_2024 FROM museum_visitors ORDER BY rank_2024 ASC"
    if limit is not None:
        query += " LIMIT ?"

    init_schema()
    with get_conn() as conn:
        cur = conn.execute(query, (limit,) if limit is not None else ())
        return cur.fetchall()


def fetch_museum_city_rows(min_visitors: int) -> list[dict[str, object]]:
    """Return joined museum/city rows for modelling."""

    query = """
    SELECT
        m.museum_name,
        m.country,
        m.city,
        m.visitors_2024 AS visitors,
        c.population
    FROM museum_visitors AS m
    JOIN city AS c
      ON lower(trim(m.country)) = lower(trim(c.country))
     AND lower(trim(m.city)) = lower(trim(c.city))
    WHERE m.visitors_2024 IS NOT NULL
      AND m.visitors_2024 >= ?
      AND c.population IS NOT NULL
      AND c.population > 0
    ORDER BY m.rank_2024 ASC
    """

    init_schema()
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(query, (min_visitors,))
        return [dict(row) for row in cur.fetchall()]


__all__ = [
    "DB_PATH",
    "fetch_museum_city_rows",
    "fetch_museums",
    "get_conn",
    "init_schema",
    "insert_museum_rows",
    "upsert_cities",
]

