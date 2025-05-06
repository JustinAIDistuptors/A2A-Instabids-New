# InstaBids Test Suite

This directory contains the test suite for the InstaBids application. The tests are organized by type and validate the integration of real services, including Supabase and LLM providers.

## Test Structure

The test suite is organized into the following directories:

- **integration/** - Contains end-to-end integration tests that verify multiple components working together
- **unit/** - Contains unit tests for individual components
- **mocks/** - Contains mock objects used in testing (though we prefer using real services when possible)

## Key Test Files

### Integration Tests

- `test_end_to_end_integration.py` - Tests the complete workflow from user creation to bid card creation
- `test_homeowner_with_real_llm.py` - Tests the homeowner agent with real LLM integration
- `test_contractor_with_real_llm.py` - Tests the contractor agent with real LLM integration
- `test_memory_system_integration.py` - Tests the memory system with real Supabase integration
- `test_user_creation.py` - Tests user creation with real Supabase integration

### Unit Tests

- `test_api_bidcard.py` - Tests the bid card API endpoints
- `test_bidcard_agent.py` - Tests the bid card agent in isolation
- `test_memory_logger.py` - Tests the memory logging system
- `test_pref_repo.py` - Tests the preferences repository
- `test_slot_fill.py` - Tests the slot filling functionality

## Running Tests

### Prerequisites

To run the tests, you need to have the following installed:

1. Python 3.12+
2. Poetry (for dependency management)
3. pytest and pytest-asyncio
4. A properly configured `.env` file with API keys

### Environment Variables

The following environment variables must be set to run the tests:

```
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE=your_service_role_key
GOOGLE_API_KEY=your_google_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### Running Tests

To run all tests:

```bash
python -m pytest
```

To run only integration tests:

```bash
python -m pytest tests/integration
```

To run a specific test:

```bash
python -m pytest tests/integration/test_homeowner_with_real_llm.py
```

To run tests with output capture disabled (to see print statements):

```bash
python -m pytest tests/integration/test_homeowner_with_real_llm.py -v -s
```

### Skipping LLM Tests

LLM tests can be expensive and time-consuming. You can skip them with:

```bash
python -m pytest --skip-llm
```

## Test Fixtures

We use pytest fixtures to set up and tear down test resources. The most important fixtures are:

- `supabase_admin_client` - Provides a Supabase client with service role access
- `test_user` - Creates a test user and cleans up afterward
- `test_project` - Creates a test project for a user
- `test_memory` - Creates a memory record for a user
- `setup_env_variables` - Sets up environment variables for tests

## Real Service Integration

Our tests use real services rather than mocks whenever possible:

1. **Supabase** - Tests connect to a real Supabase instance using the service role key
2. **Google ADK** - LLM tests use the real Google ADK to call Gemini models
3. **Storage** - File upload tests use the real Supabase Storage service

## Cleanup

All tests are designed to clean up after themselves, including:

1. Deleting test users
2. Deleting test projects
3. Deleting test bid cards
4. Deleting uploaded files
5. Deleting memory records

This ensures that the test environment remains clean between test runs.

## CI/CD Integration

Tests are automatically run in the CI pipeline using GitHub Actions. The workflow configuration can be found in `.github/workflows/test.yml`.

To run LLM tests in CI, add `[run-llm-tests]` to your commit message.
