# Museum Attendance vs City Population

## Overview

This repository ingests Wikipedia museum attendance data, enriches it with city populations, persists everything in SQLite, and trains a simple log–log linear regression to explore the relationship between city size and museum foot traffic. The project is structured to satisfy the deliverables in `rules.md`: reusable Python package, CLI, FastAPI service, notebook, and Docker setup.

## Quick Start

Get up and running in under 5 minutes:

```bash
# 1. Install dependencies
uv sync

# 2. Download population data
just download-population

# 3. Run ETL pipeline (fetch museum data + link populations)
just etl

# 4. Train the regression model
just train

# 5. Start the API server
just serve
```

Then visit:
- **API Documentation**: http://localhost:8000/docs
- **Make a Prediction**: `curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"city_population": 2500000}'`

## Getting Started

### Prerequisites

- Python 3.13+
- `uv` package manager ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))
- `just` command runner ([installation guide](https://github.com/casey/just#installation))

### Installation

Install dependencies with `uv`:

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
# Local development
uv run uvicorn src.api:app --host 0.0.0.0 --port 8000

# Or using just
just serve

# Or use Docker
just docker-build-api
just docker-api
```

**API Usage Examples:**

```bash
# Check service health
curl http://localhost:8000/health

# Get model metrics
curl http://localhost:8000/metrics

# Make a prediction
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"city_population": 2500000}'

# Interactive documentation
open http://localhost:8000/docs
```

### Notebook

Open `notebooks/museum_regression.ipynb` locally or via Docker (`just docker-build-notebook`, `just docker-notebook`). The notebook now calls directly into `src.etl.run_pipeline` and `src.model.build_features_frame` / `train_and_persist`.

## Project Structure

- `src/database.py` – SQLite helpers for schema management and queries.
- `src/etl.py` – Fetch, parse, and load museum & city data.
- `src/model.py` – Feature assembly, training, persistence, prediction.
- `src/api.py` – FastAPI application exposing health, metrics, prediction.
- `src/cli.py` – CLI entry points (`etl`, `train`).

## Docker Setup & Deployment

### Building Images

Build both services locally:

```bash
# Build API service
just docker-build-api

# Build notebook service  
just docker-build-notebook

# Or build both via docker-compose
just docker-up
```

### Running Services

**Option 1: Docker Compose (Recommended)**
```bash
# Start both API and notebook services
docker compose up --build

# Start only API service
just docker-api

# Start only notebook service
just docker-notebook

# Tear down services
just docker-down
```

**Option 2: Individual Containers**
```bash
# Run API container
docker run -p 8000:8000 -v $(pwd):/app museum-api:latest

# Run notebook container
docker run -p 8888:8888 -v $(pwd):/app museum-notebook:latest
```

### Service Endpoints

- **API Server**: http://localhost:8000
  - `/health` - Health check endpoint
  - `/metrics` - Model and system metrics
  - `/predict` - Visitor prediction endpoint
  - `/docs` - Interactive API documentation (Swagger UI)

- **Jupyter Notebook**: http://localhost:8888
  - Access `notebooks/museum_regression.ipynb` for data exploration
  - Full project source mounted at `/app`

### Docker Architecture

`docker-compose.yml` orchestrates two services:

1. **API Service** (`docker/web.Dockerfile`):
   - FastAPI application serving prediction endpoints
   - Auto-reloads code changes in development mode
   - Production-ready with uvicorn ASGI server

2. **Notebook Service** (`docker/notebook.Dockerfile`):
   - Jupyter notebook server with project dependencies
   - Mounts project directory for live code editing
   - Configured for external access and token-free development

Both images use Python 3.13-slim base with `uv` for fast dependency installation.

## Design Rationale & Trade-offs

### Architecture Decisions

This project prioritizes **rapid prototyping** and **interpretability** over complex infrastructure, aligning with MVP requirements while maintaining a clear path to production scaling.

**Key Design Choices:**
- **SQLite Database**: Zero-configuration persistence ideal for MVP, easily upgradeable to PostgreSQL for production
- **Linear Regression**: Simple, interpretable model providing clear insights into population-attendance relationships
- **FastAPI + Docker**: Modern web framework with containerization for consistent deployment
- **Wikipedia API**: Reliable structured data source with minimal setup complexity

**Trade-offs Made:**
- **Simplicity vs. Scale**: Chose single-node SQLite over distributed database for faster development
- **Interpretability vs. Accuracy**: Selected linear regression over complex ML models for stakeholder understanding
- **Development Speed vs. Production Readiness**: Prioritized quick iteration with clear migration path

See `implementation_plan.md` for detailed architectural decisions, scaling considerations, and technical trade-offs.

### Data Quality & Reliability

**Data Sources:**
- **Museum Data**: Wikipedia's REST API provides structured, reliable data with good uptime
- **Population Data**: UN Statistics Division offers authoritative city population figures
- **Matching Strategy**: Fuzzy string matching handles city name variations between data sources

**Quality Assurance:**
- Comprehensive error handling for API failures and data inconsistencies
- Validation and cleaning pipelines with detailed logging
- Missing data exclusion with monitoring for completeness tracking

## Troubleshooting

### Common Issues

**ETL Pipeline Fails**
- Ensure internet connectivity for Wikipedia API and UNSD data download
- Check `just download-population` completed successfully
- Verify `data/unsd-citypopulation-year-both.csv` exists

**API Server Won't Start**
- Confirm model artifact exists: `models/visitors_population_linreg.json`
- Run training first: `just train`
- Check port 8000 is available: `lsof -i :8000`

**Docker Issues**
- Ensure Docker daemon is running
- For M1/M2 Macs, add `--platform linux/amd64` if needed
- Clear Docker cache: `docker system prune`

**Model Training Errors**
- Verify database exists: `data/museums.sqlite`
- Run ETL first: `just etl`
- Check log output for data quality issues

### Performance Tips

- **Faster ETL**: Run `just etl` periodically to refresh data
- **API Optimization**: Model loads once at startup for fast predictions
- **Development**: Use volume mounting for live code reloading

### Testing

```bash
# Run all tests
just test

# Run with coverage
just test-coverage

# Test specific module
uv run python -m pytest tests/test_api.py -v
```

## Development Notes

- Dependencies managed via `uv` and pinned in `uv.lock`.
- Target Python 3.13 (see `pyproject.toml`).
- Use `just` recipes for common workflows (`just etl`, `just train`, `just serve`).
- Update `implementation_plan.md` / docs in tandem with code changes to keep deliverables aligned.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Run tests: `just test`
4. Update documentation as needed
5. Submit a pull request

For major changes, please open an issue first to discuss the proposed changes.

