# API Unit Tests

This directory contains comprehensive unit tests for the FastAPI museum attendance prediction API.

## Test Coverage

The test suite covers:

### Endpoints
- `/health` - Health check endpoint
- `/metrics` - Model training metrics endpoint  
- `/predict` - Prediction endpoint

### Test Categories

1. **Basic Functionality Tests**
   - Health endpoint returns correct status
   - Metrics endpoint returns training data
   - Predict endpoint returns predictions

2. **Error Handling Tests**
   - 404 errors when model artifact is missing
   - 400 errors for invalid input validation
   - 500 errors for unexpected exceptions

3. **Input Validation Tests**
   - Pydantic model validation for request schemas
   - Population parameter validation (positive integers)
   - Request schema validation

4. **Async Behavior Tests**
   - All endpoints work correctly as async functions
   - Proper async/await usage

5. **Integration Tests**
   - App configuration and factory function
   - Mocked dependencies work correctly

## Running Tests

```bash
# Run all API tests
uv run python -m pytest tests/test_api.py -v

# Run with simple output
uv run python -m pytest tests/test_api.py

# Run a specific test class
uv run python -m pytest tests/test_api.py::TestHealthEndpoint -v

# Run a specific test method
uv run python -m pytest tests/test_api.py::TestPredictEndpoint::test_predict_validates_positive_population -v
```

## Test Dependencies

The tests use:
- `pytest` - Test framework
- `httpx` - HTTP client for FastAPI testing
- `pytest-asyncio` - Async test support
- `unittest.mock` - Mocking dependencies

## Test Structure

- `conftest.py` - Pytest configuration and shared fixtures
- `test_api.py` - Main API test suite organized by test classes

Each test class focuses on a specific aspect:
- `TestHealthEndpoint` - Health check tests
- `TestMetricsEndpoint` - Metrics endpoint tests
- `TestPredictEndpoint` - Prediction endpoint tests
- `TestPredictionRequestModel` - Pydantic model validation tests
- `TestAppIntegration` - App-level integration tests
- `TestAsyncEndpoints` - Async behavior tests
- `TestErrorHandling` - Error scenarios and edge cases

## Mocking Strategy

The tests mock external dependencies:
- `load_model_artifact()` - Mocked to return controlled test data
- `predict_from_population()` - Mocked to return predictable results

This ensures tests are:
- Fast and reliable
- Independent of model training state
- Focused on API behavior rather than ML logic
