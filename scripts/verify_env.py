#!/usr/bin/env python
"""
Verify that all required environment variables are set.

This script:
1. Checks for required environment variables
2. Sets default values for optional environment variables
3. Creates a .env.test file if needed
"""

import os
import sys
from pathlib import Path

# Define required environment variables
REQUIRED_VARS = [
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE",
]

# Define optional environment variables with default values
OPTIONAL_VARS = {
    "GOOGLE_API_KEY": "mock-google-api-key",
    "OPENAI_API_KEY": "mock-openai-api-key",
    "ANTHROPIC_API_KEY": "mock-anthropic-api-key",
    "MOCK_SERVICES": "true",
}


def verify_environment():
    """
    Verify that all required environment variables are set.
    
    Returns:
        bool: True if all required variables are set, False otherwise
    """
    missing_vars = []
    
    # Check CI environment
    in_ci = os.environ.get("CI", "false").lower() in ["true", "1", "yes"]
    if in_ci:
        print("Running in CI environment, using mock values for required variables")
        # In CI, we don't need actual values, just set mock values
        for var in REQUIRED_VARS:
            if not os.environ.get(var):
                os.environ[var] = f"mock-{var.lower()}"
        return True
        
    # Otherwise check for required variables
    for var in REQUIRED_VARS:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    # Set default values for optional variables
    for var, default in OPTIONAL_VARS.items():
        if not os.environ.get(var):
            os.environ[var] = default
            print(f"Setting default value for {var}: {default}")
    
    return True


def create_env_test_file():
    """
    Create a .env.test file with current environment variables.
    """
    env_file = Path(".env.test")
    
    with open(env_file, "w") as f:
        # Write required variables
        for var in REQUIRED_VARS:
            value = os.environ.get(var, "")
            # Don't write actual values, use mocks for test file
            if value and not value.startswith("mock-"):
                value = f"mock-{var.lower()}"
            f.write(f"{var}={value}\n")
        
        # Write optional variables
        for var, default in OPTIONAL_VARS.items():
            value = os.environ.get(var, default)
            # Always set MOCK_SERVICES to true in test file
            if var == "MOCK_SERVICES":
                value = "true"
            f.write(f"{var}={value}\n")
    
    print(f"Created .env.test file at {env_file.absolute()}")


def main():
    """Main function."""
    # Verify environment
    if not verify_environment():
        return 1
    
    # Create .env.test file if in CI environment or requested
    if os.environ.get("CI") or "--write-env" in sys.argv:
        create_env_test_file()
    
    print("Environment verification successful")
    return 0


if __name__ == "__main__":
    sys.exit(main())
