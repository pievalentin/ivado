# Museum Attendance vs City Population

## Overview

This repository ingests Wikipedia museum attendance data, enriches it with city populations, persists everything in SQLite, and trains a simple log–log linear regression to explore the relationship between city size and museum foot traffic. The project is structured to satisfy the deliverables in `rules.md`: reusable Python package, CLI, FastAPI service, notebook, and Docker setup.

## Getting Started

Install dependencies with `uv` (preferred):

```bash
uv sync
```

### ETL & Training

```bash
# Run ingestion + city population linkage (download population CSV first via `just download-population`)
uv run python -m src.cli etl

# Train the regression model and persist artifact
uv run python -m src.cli train
```

The ETL step fetches data from Wikipedia, parses the museum table, loads rows into `data/museums.sqlite`, and upserts city populations from the UNSD CSV. Training reads the harmonized data, fits the regression, and writes `models/visitors_population_linreg.json`.

### API Server

Launch the FastAPI app that serves `/health`, `/metrics`, and `/predict`:

```bash
uv run uvicorn src.api:app --host 0.0.0.0 --port 8000
```

Or use Docker:

```bash
just docker-build-api
just docker-api
```

### Notebook

Open `notebooks/museum_regression.ipynb` locally or via Docker (`just docker-build-notebook`, `just docker-notebook`). The notebook now calls directly into `src.etl.run_pipeline` and `src.model.build_features_frame` / `train_and_persist`.

## Project Structure

- `src/database.py` – SQLite helpers for schema management and queries.
- `src/etl.py` – Fetch, parse, and load museum & city data.
- `src/model.py` – Feature assembly, training, persistence, prediction.
- `src/api.py` – FastAPI application exposing health, metrics, prediction.
- `src/cli.py` – CLI entry points (`etl`, `train`).

## Docker Compose

`docker-compose.yml` orchestrates the API and notebook services. Images are built from `docker/web.Dockerfile` and `docker/notebook.Dockerfile`, both leveraging `uv` for dependency installation.

## Development Notes

- Dependencies managed via `uv` and pinned in `uv.lock`.
- Target Python 3.13 (see `pyproject.toml`).
- Use `just` recipes for common workflows (`just etl`, `just train`, `just serve`).
- Update `implementation_plan.md` / docs in tandem with code changes to keep deliverables aligned.

