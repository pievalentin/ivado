"""Minimal ETL pipeline for the museums project.

`run_pipeline()` orchestrates the process end-to-end so notebooks and CLI
wrappers can rely on a single entry point.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Mapping, Tuple

import csv
import time
import re
import requests

from .database import insert_museum_rows, upsert_cities

USER_AGENT = "ivado-museum-ingestion-bot/0.2 (contact: your-real-email@example.com)"
CANONICAL_TITLE = "List_of_most_visited_art_museums"
REST_BASE = "https://en.wikipedia.org/api/rest_v1"
ACTION_BASE = "https://en.wikipedia.org/w/api.php"

RAW_WIKI_PATH = Path("data/raw_wikitext.txt")
CITY_CSV_PATH = Path("data/unsd-citypopulation-year-both.csv")


@dataclass
class MuseumRecord:
    rank_2024: int | None
    museum_name: str
    country: str | None
    city: str | None
    visitors_2024: int | None
    raw_visitors_str: str | None


def fetch_wikitext(title: str = CANONICAL_TITLE) -> Tuple[str, str]:
    """Fetch wikitext via the REST source API with Action API fallback."""

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/plain",
    }
    try:
        response = requests.get(
            f"{REST_BASE}/page/source/{title}",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        resolved_title = response.headers.get("content-location", title)
        return resolved_title, response.text
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            return fetch_action_wikitext(title)
        raise


def fetch_action_wikitext(title: str) -> Tuple[str, str]:
    """Fallback to Wikipedia Action API for wikitext when REST source is unavailable."""

    headers = {"User-Agent": USER_AGENT}
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "titles": title,
        "redirects": 1,
        "formatversion": "2",
        "format": "json",
    }
    response = requests.get(ACTION_BASE, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        raise ValueError("Action API returned no pages for title")
    page = pages[0]
    if "missing" in page:
        raise ValueError(f"Action API missing page for title={title}")
    resolved = page["title"]
    wikitext = page["revisions"][0]["slots"]["main"]["content"]
    return resolved, wikitext


def _strip_refs(text: str) -> str:
    text = re.sub(r"<ref.*?</ref>", "", text, flags=re.IGNORECASE | re.DOTALL)
    return re.sub(r"<ref[^>/]*/>", "", text, flags=re.IGNORECASE)


def _strip_links(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        display = match.group(2)
        return display if display else match.group(1)

    return re.sub(r"\[\[([^|\]]+)(?:\|([^\]]+))?]]", repl, text)


def _clean_cell(text: str) -> str:
    text = _strip_refs(text)
    text = _strip_links(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("{{flagicon|", "").replace("}}", "")
    text = text.replace("{{lang|", "")
    text = re.sub(r"{{.*?}}", "", text)
    text = text.replace("&nbsp;", " ")
    text = text.strip()
    return re.sub(r"\s+", " ", text)


TABLE_START_RE = re.compile(r"{\|\s*class=\"wikitable sortable\"")
ROW_SPLIT_RE = re.compile(r"\n\|-\n")
PARENS_YEAR_RE = re.compile(r"\((?:19|20)\d{2}\)")
NUM_EXTRACT_RE = re.compile(r"([\d][\d,\.\s]*)")


def _clean_museum_name(name: str) -> str:
    name = name.lstrip('|').strip()
    if name.startswith("{{Lang|"):
        parts = name.split('|')
        if len(parts) >= 3:
            name = parts[2]
        else:
            name = parts[-1]
    name = name.replace("italic=no", "").replace("italic=yes", "")
    name = re.sub(r"{{.*", "", name)
    return re.sub(r"\s+", " ", name).strip(', ').strip()


def _extract_table(wikitext: str) -> str:
    match = TABLE_START_RE.search(wikitext)
    if not match:
        raise ValueError("No 'wikitable sortable' table found in wikitext.")
    start = match.start()
    lines = wikitext[start:].splitlines(keepends=True)
    brace_depth = 0
    collected: list[str] = []
    for line in lines:
        collected.append(line)
        stripped = line.strip()
        if stripped.startswith("{|"):
            brace_depth += 1
        elif stripped == "|}":
            brace_depth -= 1
            if brace_depth == 0:
                break
    return "".join(collected)


def _split_cells(row_block: str) -> list[str]:
    text = row_block.replace("\r", "").lstrip()
    if text.startswith("|"):
        text = text[1:]
    text = re.sub(r"\n(?!(\||!|\|-))", " ", text)
    return [segment.strip() for segment in text.split("||")]


def _parse_rank(cell: str) -> int | None:
    cleaned = re.sub(r"[^\d]", "", cell.strip().replace("(new)", ""))
    return int(cleaned) if cleaned else None


def _parse_visitors(cell: str) -> tuple[int | None, str]:
    raw = cell
    cell = _strip_refs(cell)
    cell = PARENS_YEAR_RE.sub("", cell)
    match = NUM_EXTRACT_RE.search(cell.replace(" ", ""))
    if not match:
        return None, raw
    number_text = match.group(1).replace(",", "").replace(".", "").replace(" ", "")
    try:
        return int(number_text), raw
    except ValueError:
        return None, raw


def _normalize_location(country: str | None, city: str | None) -> tuple[str | None, str | None]:
    if not country and not city:
        return None, None
    if country and city:
        key = (country, city)
        replacements = {
            ("United States New York", "City"): ("United States", "New York City"),
            ("United States Washington", "D.C."): ("United States", "Washington, D.C."),
            ("United States Los", "Angeles"): ("United States", "Los Angeles"),
            ("United States Grand Rapids Charter Township", "Michigan"): ("United States", "Grand Rapids Charter Township"),
            ("United States San Marino", "California"): ("United States", "San Marino"),
            ("United States New", "Orleans"): ("United States", "New Orleans"),
            ("UAE Abu", "Dhabi"): ("United Arab Emirates", "Abu Dhabi"),
            ("Mexico Mexico", "City"): ("Mexico", "Mexico City"),
            ("Russia Saint", "Petersburg"): ("Russia", "Saint Petersburg"),
            ("HK Hong", "Kong"): ("Hong Kong", "Hong Kong"),
            ("Brazil Rio", "Janeiro"): ("Brazil", "Rio de Janeiro"),
            ("Brazil Sao", "Paulo"): ("Brazil", "Sao Paulo"),
        }
        if key in replacements:
            return replacements[key]
    return country, city


def parse_museum_table(wikitext: str) -> Tuple[List[MuseumRecord], List[Mapping[str, object]]]:
    table_text = _extract_table(wikitext)
    parts = ROW_SPLIT_RE.split(table_text)
    accepted: list[MuseumRecord] = []
    discarded: list[Mapping[str, object]] = []
    for part in parts[1:]:
        if part.strip().startswith("|}"):
            break
        row = part.lstrip()
        if not row.startswith("|"):
            continue
        cells_raw = _split_cells(row)
        cells = [_clean_cell(cell) for cell in cells_raw]
        if len(cells) < 4:
            discarded.append({"reason": "too_few_cells", "cells": cells})
            continue
        rank = _parse_rank(cells[0])
        museum_name = cells[1] if len(cells) >= 2 else None
        location = cells[2] if len(cells) >= 3 else ""
        visitors_cell = cells[3] if len(cells) >= 4 else ""
        country: str | None = None
        city: str | None = None
        if location:
            if "," in location:
                parts_loc = [segment.strip() for segment in location.split(",") if segment.strip()]
                if len(parts_loc) >= 2:
                    country = parts_loc[0]
                    city = ", ".join(parts_loc[1:])
            elif " " in location:
                tokens = location.split()
                if len(tokens) >= 2:
                    country = " ".join(tokens[:-1])
                    city = tokens[-1]
            else:
                country = location
        visitors, raw_visitors = _parse_visitors(visitors_cell)
        if museum_name:
            museum_name = _clean_museum_name(museum_name)
        country, city = _normalize_location(country, city)
        if museum_name and visitors and visitors >= 100_000:
            accepted.append(
                MuseumRecord(
                    rank_2024=rank,
                    museum_name=museum_name,
                    country=country,
                    city=city,
                    visitors_2024=visitors,
                    raw_visitors_str=raw_visitors,
                )
            )
        else:
            discarded.append({
                "reason": "failed_validation",
                "cells": cells,
            })
    dedup: dict[tuple[str, str | None], MuseumRecord] = {}
    for record in accepted:
        key = (record.museum_name, record.city)
        existing = dedup.get(key)
        if not existing:
            dedup[key] = record
            continue
        if existing.rank_2024 is None or (
            record.rank_2024 is not None
            and existing.rank_2024 is not None
            and record.rank_2024 < existing.rank_2024
        ):
            dedup[key] = record
    return list(dedup.values()), discarded


def parse_city_population_csv(path: Path = CITY_CSV_PATH) -> Iterable[Mapping[str, object]]:
    if not path.exists():
        raise FileNotFoundError(f"City population CSV missing at {path}. Please run `just download` to fetch it.")
    # End of Selection
    latest: dict[tuple[str, str], dict[str, object]] = {}
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            country = row.get("Country or Area") or row.get("Country")
            city = row.get("City")
            year = row.get("Year")
            population = row.get("Value") or row.get("Population")
            if not (country and city and year and population):
                continue
            try:
                year_int = int(year)
                population_int = int(population)
            except ValueError:
                continue
            key = (country.strip(), city.strip())
            current = latest.get(key)
            if current is None or year_int > int(current["year"]):
                latest[key] = {
                    "country": key[0],
                    "city": key[1],
                    "population": population_int,
                    "year": year_int,
                    "source": "UNSD-local",
                }
    return latest.values()


def run_pipeline(*, save_raw: bool = False) -> None:
    """Run the ETL sequence and load into SQLite."""

    resolved_title, wikitext = fetch_wikitext()
    if save_raw:
        RAW_WIKI_PATH.parent.mkdir(parents=True, exist_ok=True)
        RAW_WIKI_PATH.write_text(wikitext, encoding="utf-8")

    records, discarded = parse_museum_table(wikitext)
    if not records:
        raise RuntimeError("No museum records parsed from wikitext.")

    inserted = insert_museum_rows(
        (
            {
                "rank_2024": record.rank_2024,
                "museum_name": record.museum_name,
                "country": record.country,
                "city": record.city,
                "visitors_2024": record.visitors_2024,
                "raw_visitors_str": record.raw_visitors_str,
            }
            for record in records
        ),
        page_title=resolved_title,
        page_revision=-1,
        extracted_at_utc=int(time.time()),
    )

    city_records = list(parse_city_population_csv())
    upserted = upsert_cities(city_records)

    print(f"Inserted {inserted} museum rows (deduplicated).")
    print(f"Upserted {upserted} city population rows.")
    if discarded:
        print(f"Discarded {len(discarded)} rows during parsing.")


__all__ = ["run_pipeline", "parse_museum_table", "fetch_wikitext"]

