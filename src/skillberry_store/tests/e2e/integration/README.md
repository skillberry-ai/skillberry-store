# Integration Tests for Skillberry Store

This directory contains integration tests that test the skillberry-store API using the SDK client.

## Prerequisites

**IMPORTANT**: These tests require a running skillberry-store service. The tests do NOT start the service automatically.

### Starting the Service

Before running the integration tests, start the skillberry-store service:

```bash
# From the skillberry-store directory
python -m skillberry_store.main
```

Or using Docker:

```bash
# From the skillberry-store directory
make docker-run
```

The service should be running on `http://localhost:8000` (default).

## Running the Tests

Integration tests are marked with the `@pytest.mark.integration` decorator and will NOT run by default with `pytest`.

### Run Only Integration Tests

```bash
# From the skillberry-store directory
pytest -m integration
```

### Run Integration Tests with Verbose Output

```bash
pytest -m integration -v
```

### Run Specific Integration Test File

```bash
pytest -m integration src/skillberry_store/tests/e2e/integration/test_tools_integration.py
```

### Run Specific Test Function

```bash
pytest -m integration src/skillberry_store/tests/e2e/integration/test_tools_integration.py::test_add_tool
```

## Automatic Service Check

The integration tests automatically check if the skillberry-store service is running before executing any tests. If the service is not available on `http://localhost:8000`, all integration tests will be skipped with a clear message.

This prevents confusing connection errors and makes it clear that the service needs to be started first.

## Test Structure

The integration tests are organized by API endpoint:

- **test_tools_integration.py**: Tests for Tools API endpoints
  - Add tool from Python file
  - List tools
  - Get tool by name
  - Get tool by UUID
  - Update tool
  - Delete tool
  - Get tool module/code

- **test_skills_integration.py**: Tests for Skills API endpoints
  - Create skill
  - List skills
  - Get skill by name
  - Get skill by UUID
  - Update skill
  - Delete skill
  - Search skills

- **test_snippets_integration.py**: Tests for Snippets API endpoints
  - Create snippet
  - List snippets
  - Get snippet by name
  - Get snippet by UUID
  - Update snippet
  - Delete snippet
  - Search snippets

## Test Dependencies

Tests may have dependencies on each other within a test class. For example:
- You cannot delete a tool unless it has been created first
- Update operations require an existing resource

The tests are designed to run in order within each test class to handle these dependencies.

## Configuration

The tests use the SDK client configured to connect to `http://localhost:8000` by default.

To use a different host/port, you can modify the `api_config` fixture in `conftest.py` or set environment variables (if implemented).

## Troubleshooting

### Service Not Running

If you see a skip message like "Skillberry-store service is not running", make sure the service is running:

```bash
curl http://localhost:8000/docs
```

Should return the API documentation page.

### Port Already in Use

If port 8000 is already in use, you'll need to:
1. Stop the conflicting service
2. Or configure skillberry-store to use a different port
3. Update the test configuration accordingly

### Test Failures

If tests fail:
1. Check that the service is running and accessible
2. Check service logs for errors
3. Verify the service database/storage is in a clean state
4. Some tests may leave artifacts - consider cleaning the test data directory between runs