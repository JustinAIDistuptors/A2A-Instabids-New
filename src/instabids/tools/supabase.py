import os
from pathlib import Path
from typing import List

from google.adk.tools.openapi_tool import OpenAPIToolset, RestApiTool
from google.adk.tools.openapi_tool.auth.auth_helpers import token_to_scheme_credential

# TODO: Ensure openapi_supabase.yaml contains the correct SUPABASE_URL in its 'servers' section.
# Example:
# servers:
#   - url: {SUPABASE_URL} # Replace {SUPABASE_URL} with your actual Supabase URL or use a variable that gets resolved.

# TODO: Ensure openapi_supabase.yaml defines a securityScheme for the 'apikey' header.
# Example in components.securitySchemes:
#   ApiKeyAuth:
#     type: apiKey
#     in: header
#     name: apikey
# And apply it under security:
# security:
#   - ApiKeyAuth: []

# Load the spec that sits next to this file
_SPEC_PATH = Path(__file__).with_name("openapi_supabase.yaml")
spec_str_template = _SPEC_PATH.read_text()

# Hardcode Supabase URL by replacing a placeholder in the spec string
actual_supabase_url = "https://mkfbxvwmuxebggfbljgn.supabase.co"
spec_str = spec_str_template.replace("{SUPABASE_URL}", actual_supabase_url)

# Setup Bearer token authentication
# Hardcode the Supabase Service Role Key
supabase_key_value = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1rZmJ4dndtdXhlYmdnZmJsamduIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NjA3ODQyMSwiZXhwIjoyMDYxNjU0NDIxfQ.tYXiJWcCUW1qufYDL-9wk9TZu0EQOWrTpA1FBhr6DOw"

bearer_auth_scheme, bearer_auth_credential = token_to_scheme_credential(
    token_type="oauth2Token", 
    location="header", 
    name="Authorization",  # This name is standard for Bearer tokens.
    credential_value=supabase_key_value
)

# Create the toolset once at import-time
# The 'apikey' header and 'base_url' should be handled by the OpenAPI spec itself.
# Default params like 'user_id' must now be passed by the LLM if required by an operation.
supabase_toolset = OpenAPIToolset(
    spec_str=spec_str,
    spec_str_type="yaml",
    auth_scheme=bearer_auth_scheme,
    auth_credential=bearer_auth_credential,
)

def get_supabase_tools() -> List[RestApiTool]:
    return supabase_toolset.get_tools()