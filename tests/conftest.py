"""Pytest configuration and fixtures for the test suite."""

import pytest
from fastapi.testclient import TestClient

from src.api import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_model_artifact() -> dict:
    """Sample model artifact for testing."""
    return {
        "created_utc": "2024-01-01T00:00:00+00:00",
        "model": {
            "coef_log": [0.8],
            "intercept_log": 10.5
        },
        "training_metrics": {
            "r2": 0.85,
            "mae": 100000.0,
            "rmse": 150000.0,
            "n_rows": 50.0
        },
        "training_sample_preview": [
            {
                "museum_name": "Test Museum",
                "country": "Test Country",
                "city": "Test City",
                "visitors": 500000.0,
                "population": 1000000.0
            }
        ],
        "feature": "log1p(population)",
        "target": "log1p(visitors)"
    }


@pytest.fixture
def sample_training_metrics() -> dict:
    """Sample training metrics for testing."""
    return {
        "r2": 0.85,
        "mae": 100000.0,
        "rmse": 150000.0,
        "n_rows": 50.0
    }
