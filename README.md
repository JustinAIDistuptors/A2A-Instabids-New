# InstaBids Google ADK

This repository contains InstaBids' implementation of the Google Agent Development Kit (ADK).

## Vendor Namespace Approach

This package uses a vendor namespace approach (`instabids_google.adk`) instead of `google.adk` to avoid namespace collisions with existing Google packages in the Python environment.

### Why a Vendor Namespace?

Using a vendor namespace has several advantages:
- Avoids conflicts with existing Google packages
- Clearly indicates that this is InstaBids' implementation of the ADK
- Works reliably in all environments, regardless of what other packages are installed

## Installation

```bash
# Install from the repository
pip install -e .
```

## Usage

```python
# Import the LlmAgent class
from instabids_google.adk import LlmAgent

# Create an agent
agent = LlmAgent("MyAgent", system_prompt="You are a helpful assistant.")

# Import tracing utilities
from instabids_google.adk import enable_tracing

# Enable tracing
enable_tracing(output="stdout")
```

## Testing

To verify that the package works correctly, run:

```bash
python test_imports.py
```

This will test importing the key components and creating an agent instance.

---

## Project Structure & Key Components

This project follows a standard Python structure:

-   `src/instabids/`: Contains the core application code.
    -   `agents/`: Houses the different autonomous agents (e.g., MatchingAgent).
    -   `api/`: Defines the FastAPI application and API routes.
    -   `data/`: Includes data access layers (repositories, Supabase client).
    -   `services/`: Contains wrappers for external services (e.g., Google Places).
    -   `tools/`: Holds utility functions or wrappers for tools (e.g., Twilio, SendGrid).
    -   `a2a_comm.py`: Handles Agent-to-Agent communication patterns (event handling).
    -   `app.py`: Main FastAPI application setup.
-   `supabase/migrations/`: Stores SQL migration files managed by Supabase CLI.
-   `tests/`: Contains unit and integration tests using pytest.
-   `pyproject.toml`: Project metadata and dependencies (managed by Poetry).
-   `README.md`: This file.

## Sprint 6: Matching V1 (Rule-Based)

This sprint introduced the first version of the contractor matching functionality.

**Key Additions:**

-   **Database Enhancements (`supabase/migrations/20240530_add_match_contractors.sql`):**
    -   Enabled `cube` and `earthdistance` PostgreSQL extensions for geospatial calculations.
    -   Added `match_contractors` SQL function for finding nearby contractors based on project location and category.
    -   Added `match_contractors_rule` SQL function implementing a scoring logic based on category similarity, distance, activity, and acceptance rate.
-   **Matching Agent (`src/instabids/agents/matching_agent.py`):**
    -   Listens for `bidcard.created` events via the A2A communication system (`on_envelope`).
    -   Fetches bid card details (category, location).
    -   Calls the `match_contractors_rule` RPC to get scored contractor matches.
    -   Saves the results to the `match_scores` table.
    -   Sends a `matching.invited` A2A event (`send_envelope`) with the matched contractor IDs.
    -   **Prospect Seeding:** If fewer than 6 database matches are found and the bid card has a valid location, it queries the Google Places API (via the service wrapper) for nearby contractors. These prospects are saved to `prospect_contractors` and queued for outreach in `prospect_outbox`.
-   **Service/Tool Wrappers:**
    -   `src/instabids/services/google_places.py`: Thin wrapper around the Google Places Nearby Search API to find potential contractors.
    -   `src/instabids/tools/twilio_sms.py`: Stub for sending SMS via Twilio (to be fully implemented later).
    -   `src/instabids/tools/sendgrid_mail.py`: Stub for sending emails via SendGrid (to be fully implemented later).
-   **Unit Tests (`tests/test_matching_agent.py`):**
    -   Added tests for `handle_new_bidcard`, covering the success path, prospect seeding logic, error handling, and helper functions.