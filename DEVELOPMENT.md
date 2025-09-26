# Development Guide

## Development Environment Setup

### Prerequisites

- Python 3.13+
- `uv` for dependency management
- `just` for task automation
- Docker for containerized development
- SQLite for database operations

### Initial Setup

```bash
# Clone and setup
git clone <repository-url>
cd ivado
uv sync

# Download required data
just download-population

# Run initial setup
just etl
just train
```

## Development Workflow

### Code Organization

```
src/
├── __init__.py
├── api.py          # FastAPI application
├── cli.py          # Command-line interface
├── database.py     # Database operations
├── etl.py          # Extract, Transform, Load pipeline
└── model.py        # Machine learning operations

tests/
├── __init__.py
├── conftest.py     # Test fixtures
├── test_api.py     # API endpoint tests
└── README.md       # Testing documentation

docker/
├── notebook.Dockerfile    # Jupyter notebook container
└── web.Dockerfile         # API service container
```

### Common Development Tasks

**Data Pipeline Development:**
```bash
# Test ETL pipeline changes
just etl

# Verify data quality
uv run python -c "
import sqlite3
conn = sqlite3.connect('data/museums.sqlite')
print('Museums:', conn.execute('SELECT COUNT(*) FROM museums').fetchone()[0])
print('With population:', conn.execute('SELECT COUNT(*) FROM museums WHERE city_population IS NOT NULL').fetchone()[0])
"
```

**Model Development:**
```bash
# Retrain model after data changes
just train

# Test predictions
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"city_population": 2500000}'
```

**API Development:**
```bash
# Start development server with auto-reload
just serve

# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/metrics

# View interactive docs
open http://localhost:8000/docs
```

## Testing Strategy

### Running Tests

```bash
# All tests
just test

# With coverage
just test-coverage

# Specific test file
uv run python -m pytest tests/test_api.py -v

# Single test
uv run python -m pytest tests/test_api.py::test_health_endpoint -v
```

### Test Categories

1. **Unit Tests**: Test individual functions and classes
2. **Integration Tests**: Test API endpoints and data pipeline
3. **Data Quality Tests**: Verify ETL output and model inputs

### Writing Tests

Example test structure:
```python
import pytest
from src.api import app
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    return TestClient(app)

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

## Docker Development

### Building Images

```bash
# Build API image
just docker-build-api

# Build notebook image
just docker-build-notebook

# Build both via compose
docker compose build
```

### Development with Docker

```bash
# Start all services
just docker-up

# Start only API
just docker-api

# Start only notebook
just docker-notebook

# View logs
docker compose logs -f api
docker compose logs -f notebook
```

### Container Development Tips

- Use volume mounting for live code reloading
- Environment variables defined in `docker-compose.yml`
- Container logs available via `docker compose logs`
- Access containers: `docker compose exec api bash`

## Database Development

### Schema Management

```bash
# Inspect current schema
uv run python -c "
import sqlite3
conn = sqlite3.connect('data/museums.sqlite')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(museums)')
for row in cursor.fetchall():
    print(row)
"
```

### Data Exploration

```bash
# Launch interactive Python session
uv run python

# Example exploration
>>> import sqlite3
>>> conn = sqlite3.connect('data/museums.sqlite')
>>> df = pd.read_sql('SELECT * FROM museums LIMIT 10', conn)
>>> print(df.head())
```

## Model Development

### Training Pipeline

```python
from src.model import build_features_frame, train_and_persist

# Load and explore data
df = build_features_frame()
print(df.describe())

# Train model
model_info = train_and_persist(df)
print(f"R² Score: {model_info['r2_score']:.3f}")
```

### Model Evaluation

```python
from src.model import load_model, predict_visitors

# Load persisted model
model_info = load_model()

# Test predictions
test_populations = [500000, 1000000, 5000000, 10000000]
for pop in test_populations:
    prediction = predict_visitors(pop, model_info)
    print(f"Population: {pop:,} → Visitors: {prediction:,.0f}")
```

## Code Quality

### Formatting and Linting

```bash
# Format code with ruff
uv run ruff format src/ tests/

# Check linting
uv run ruff check src/ tests/

# Type checking (if using mypy)
uv run mypy src/
```

### Pre-commit Hooks

Consider setting up pre-commit hooks for consistent code quality:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

## Performance Optimization

### Profiling

```python
import cProfile
import pstats
from src.etl import run_pipeline

# Profile ETL pipeline
pr = cProfile.Profile()
pr.enable()
run_pipeline()
pr.disable()

stats = pstats.Stats(pr)
stats.sort_stats('cumulative')
stats.print_stats(10)  # Top 10 functions
```

### Memory Usage

```python
import tracemalloc
from src.model import build_features_frame

tracemalloc.start()
df = build_features_frame()
current, peak = tracemalloc.get_traced_memory()
print(f"Current: {current / 1024 / 1024:.1f} MB")
print(f"Peak: {peak / 1024 / 1024:.1f} MB")
tracemalloc.stop()
```

## Debugging

### API Debugging

```bash
# Enable debug mode
FASTAPI_DEBUG=1 just serve

# Or with uvicorn directly
uv run uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

### Database Debugging

```python
import sqlite3
import logging

# Enable SQL logging
logging.basicConfig(level=logging.DEBUG)
conn = sqlite3.connect('data/museums.sqlite')
conn.set_trace_callback(print)  # Print all SQL statements
```

### Model Debugging

```python
import numpy as np
import matplotlib.pyplot as plt
from src.model import build_features_frame

df = build_features_frame()

# Visualize data distribution
plt.figure(figsize=(12, 4))

plt.subplot(1, 3, 1)
plt.hist(df['city_population'], bins=20, alpha=0.7)
plt.title('City Population Distribution')
plt.xlabel('Population')

plt.subplot(1, 3, 2)
plt.hist(df['visitors_millions'], bins=20, alpha=0.7)
plt.title('Visitors Distribution')
plt.xlabel('Visitors (millions)')

plt.subplot(1, 3, 3)
plt.scatter(np.log(df['city_population']), np.log(df['visitors_millions']), alpha=0.6)
plt.title('Log-Log Relationship')
plt.xlabel('log(Population)')
plt.ylabel('log(Visitors)')

plt.tight_layout()
plt.show()
```

## Deployment

### Production Considerations

1. **Environment Variables**: Use `.env` files for configuration
2. **Database**: Consider PostgreSQL for production workloads
3. **Monitoring**: Add logging, metrics, and health checks
4. **Security**: Implement authentication and rate limiting
5. **Scaling**: Use container orchestration (Kubernetes, Docker Swarm)

### Configuration Management

```python
# src/config.py
import os
from pathlib import Path

class Config:
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/museums.sqlite')
    MODEL_PATH = os.getenv('MODEL_PATH', 'models/visitors_population_linreg.json')
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', 8000))
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
```

## Contributing Guidelines

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Write docstrings for public functions
- Keep functions focused and testable

### Documentation

- Update `README.md` for user-facing changes
- Update `implementation_plan.md` for architectural changes
- Add inline comments for complex logic
- Update this `DEVELOPMENT.md` for workflow changes

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and test
just test

# Commit changes
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/new-feature
```

### Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md` (if exists)
3. Run full test suite: `just test-coverage`
4. Build and test Docker images
5. Tag release: `git tag v1.0.0`
6. Push tags: `git push --tags`

## Troubleshooting Development Issues

### Common Problems

**Import Errors:**
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=/path/to/project:$PYTHONPATH

# Or use module syntax
uv run python -m src.cli etl
```

**Database Locked:**
```bash
# Check for hanging connections
lsof data/museums.sqlite

# Kill processes if needed
pkill -f "python.*etl"
```

**Docker Build Failures:**
```bash
# Clear build cache
docker system prune -f

# Rebuild without cache
docker compose build --no-cache
```

**Test Failures:**
```bash
# Run single test with verbose output
uv run python -m pytest tests/test_api.py::test_predict_endpoint -v -s

# Debug with pdb
uv run python -m pytest tests/test_api.py::test_predict_endpoint --pdb
```

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [UV Package Manager](https://docs.astral.sh/uv/)
- [Just Command Runner](https://github.com/casey/just)
- [SQLite Documentation](https://sqlite.org/docs.html)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [pytest Documentation](https://docs.pytest.org/)
