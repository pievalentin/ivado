"""Unit tests for the FastAPI museum attendance prediction API."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient

from src.api import app


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_ok_status(self) -> None:
        """Test that health endpoint returns status ok."""
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestMetricsEndpoint:
    """Tests for the /metrics endpoint."""

    def test_metrics_returns_training_metrics_when_model_exists(self) -> None:
        """Test that metrics endpoint returns training metrics from model artifact."""
        mock_artifact = {
            "training_metrics": {
                "r2": 0.85,
                "mae": 100000.0,
                "rmse": 150000.0,
                "n_rows": 50.0
            }
        }
        
        with patch("src.api.load_model_artifact", return_value=mock_artifact):
            client = TestClient(app)
            response = client.get("/metrics")
            
            assert response.status_code == 200
            assert response.json() == mock_artifact["training_metrics"]

    def test_metrics_returns_404_when_model_not_found(self) -> None:
        """Test that metrics endpoint returns 404 when model artifact is missing."""
        with patch("src.api.load_model_artifact", side_effect=FileNotFoundError("Model not found")):
            client = TestClient(app)
            response = client.get("/metrics")
            
            assert response.status_code == 404
            assert "Model not found" in response.json()["detail"]

    def test_metrics_returns_empty_dict_when_no_training_metrics(self) -> None:
        """Test that metrics endpoint returns empty dict when training_metrics key is missing."""
        mock_artifact: Dict[str, Any] = {}
        
        with patch("src.api.load_model_artifact", return_value=mock_artifact):
            client = TestClient(app)
            response = client.get("/metrics")
            
            assert response.status_code == 200
            assert response.json() == {}


class TestPredictEndpoint:
    """Tests for the /predict endpoint."""

    def test_predict_returns_prediction_for_valid_population(self) -> None:
        """Test that predict endpoint returns prediction for valid population."""
        expected_visitors = 250000.0
        
        with patch("src.api.predict_from_population", return_value=expected_visitors):
            client = TestClient(app)
            response = client.post("/predict", json={"population": 1000000})
            
            assert response.status_code == 200
            assert response.json() == {"predicted_visitors": expected_visitors}

    def test_predict_validates_positive_population(self) -> None:
        """Test that predict endpoint validates population is positive."""
        client = TestClient(app)
        
        # Test zero population
        response = client.post("/predict", json={"population": 0})
        assert response.status_code == 400
        assert "Population must be positive" in response.json()["detail"]
        
        # Test negative population
        response = client.post("/predict", json={"population": -1000})
        assert response.status_code == 400
        assert "Population must be positive" in response.json()["detail"]

    def test_predict_returns_404_when_model_not_found(self) -> None:
        """Test that predict endpoint returns 404 when model artifact is missing."""
        with patch("src.api.predict_from_population", side_effect=FileNotFoundError("Model not found")):
            client = TestClient(app)
            response = client.post("/predict", json={"population": 1000000})
            
            assert response.status_code == 404
            assert "Model not found" in response.json()["detail"]

    def test_predict_validates_request_schema(self) -> None:
        """Test that predict endpoint validates request schema."""
        client = TestClient(app)
        
        # Test missing population field
        response = client.post("/predict", json={})
        assert response.status_code == 422
        
        # Test invalid population type
        response = client.post("/predict", json={"population": "invalid"})
        assert response.status_code == 422

    def test_predict_calls_prediction_function_with_correct_population(self) -> None:
        """Test that predict endpoint calls prediction function with the correct population."""
        test_population = 1500000
        expected_visitors = 300000.0
        
        with patch("src.api.predict_from_population", return_value=expected_visitors) as mock_predict:
            client = TestClient(app)
            response = client.post("/predict", json={"population": test_population})
            
            assert response.status_code == 200
            mock_predict.assert_called_once_with(test_population)


class TestPredictionRequestModel:
    """Tests for the PredictionRequest Pydantic model."""

    def test_prediction_request_accepts_valid_population(self) -> None:
        """Test that PredictionRequest accepts valid population values."""
        from src.api import PredictionRequest
        
        # Test positive integer
        request = PredictionRequest(population=1000000)
        assert request.population == 1000000
        
        # Test small positive integer
        request = PredictionRequest(population=1)
        assert request.population == 1

    def test_prediction_request_validates_population_type(self) -> None:
        """Test that PredictionRequest validates population is an integer."""
        from src.api import PredictionRequest
        from pydantic import ValidationError
        
        # Test that string gets converted to int if possible
        request = PredictionRequest(population="1000000")
        assert request.population == 1000000
        
        # Test that invalid string raises validation error
        with pytest.raises(ValidationError):
            PredictionRequest(population="invalid")
        
        # Test that float with fractional part raises validation error
        with pytest.raises(ValidationError):
            PredictionRequest(population=1000000.5)
        
        # Test that float without fractional part works
        request = PredictionRequest(population=1000000.0)
        assert request.population == 1000000


class TestAppIntegration:
    """Integration tests for the FastAPI app."""

    def test_app_title_is_set_correctly(self) -> None:
        """Test that the FastAPI app has the correct title."""
        assert app.title == "Museum Attendance API"

    def test_create_app_factory_returns_app_instance(self) -> None:
        """Test that create_app factory function returns the app instance."""
        from src.api import create_app
        
        created_app = create_app()
        assert created_app is app


@pytest.mark.asyncio
class TestAsyncEndpoints:
    """Test async behavior of endpoints."""

    async def test_health_endpoint_is_async(self) -> None:
        """Test that health endpoint works as an async function."""
        from src.api import health
        
        result = await health()
        assert result == {"status": "ok"}

    async def test_metrics_endpoint_is_async(self) -> None:
        """Test that metrics endpoint works as an async function."""
        from src.api import metrics
        
        mock_artifact = {
            "training_metrics": {
                "r2": 0.85,
                "mae": 100000.0
            }
        }
        
        with patch("src.api.load_model_artifact", return_value=mock_artifact):
            result = await metrics()
            assert result == mock_artifact["training_metrics"]

    async def test_predict_endpoint_is_async(self) -> None:
        """Test that predict endpoint works as an async function."""
        from src.api import predict, PredictionRequest
        
        expected_visitors = 250000.0
        
        with patch("src.api.predict_from_population", return_value=expected_visitors):
            request = PredictionRequest(population=1000000)
            result = await predict(request)
            assert result == {"predicted_visitors": expected_visitors}


class TestErrorHandling:
    """Test error handling across different scenarios."""

    def test_predict_handles_model_function_errors_gracefully(self) -> None:
        """Test that predict endpoint handles various errors from model functions."""
        # For testing unhandled exceptions, we need to use pytest.raises since
        # TestClient by default re-raises exceptions instead of returning 500
        with patch("src.api.predict_from_population", side_effect=ValueError("Invalid model data")):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/predict", json={"population": 1000000})
            # FastAPI converts unhandled exceptions to 500 by default
            assert response.status_code == 500

    def test_metrics_handles_malformed_artifact_gracefully(self) -> None:
        """Test that metrics endpoint handles malformed artifacts."""
        # Test with None artifact - this will cause an AttributeError
        with patch("src.api.load_model_artifact", return_value=None):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/metrics")
            # This will be a 500 error due to AttributeError on None.get()
            assert response.status_code == 500
        
        # Test with artifact that has no training_metrics key
        with patch("src.api.load_model_artifact", return_value={}):
            client = TestClient(app)
            response = client.get("/metrics")
            # Should return empty dict when artifact has no training_metrics
            assert response.status_code == 200
            assert response.json() == {}


if __name__ == "__main__":
    pytest.main([__file__])
