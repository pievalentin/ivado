set shell := ["/bin/sh", "-cu"]

# Default target prints available recipes.
default:
	@just --list

# Install Python dependencies using uv.
install:
	uv sync

# Run ETL pipeline (ingestion and population link).
etl:
	uv run python -m src.cli etl

# Train the regression model and persist the artifact.
train:
	uv run python -m src.cli train

# Run all unit tests.
test:
	uv run python -m pytest tests/ -v

# Run tests with coverage report.
test-coverage:
	uv run python -m pytest tests/ --cov=src --cov-report=term-missing

# Run the FastAPI server locally.
serve host="0.0.0.0" port="8000":
	uv run uvicorn src.api:app --host {{host}} --port {{port}}

# Launch the Jupyter notebook server outside Docker.
notebook:
	uv run python -m notebook --NotebookApp.allow_origin='*' --NotebookApp.token='' --NotebookApp.password='' --NotebookApp.ip=0.0.0.0 --NotebookApp.port=8888 --NotebookApp.notebook_dir=/Users/pierre/Developer/ivado/notebooks

# Download latest UNSD city population CSV from GitHub datasets.
download-population:
	curl -L https://github.com/datasets/population-city/raw/refs/heads/main/data/unsd-citypopulation-year-both.csv -o data/unsd-citypopulation-year-both.csv

# Build the API Docker image.
docker-build-api:
	docker build -f docker/web.Dockerfile -t museum-api:latest .

# Build the notebook Docker image.
docker-build-notebook:
	docker build -f docker/notebook.Dockerfile -t museum-notebook:latest .

# Bring up all docker-compose services.
docker-up:
	docker compose up --build

# Tear down docker-compose services.
docker-down:
	docker compose down --remove-orphans

# Start only the API service via docker-compose.
docker-api:
	docker compose up --build api

# Start only the notebook service via docker-compose.
docker-notebook:
	docker compose up --build notebook

