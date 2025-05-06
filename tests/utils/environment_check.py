#!/usr/bin/env python
"""
Environment check script for multi-agent integration tests.

This script verifies that all the required dependencies and environment variables
are properly configured for running the multi-agent integration tests.

Usage:
    python -m tests.utils.environment_check
"""

import os
import sys
import importlib.util
from typing import Dict, List, Tuple, Any


def check_environment_variables() -> Tuple[bool, List[str]]:
    """Check if all required environment variables are set."""
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE",
        "GOOGLE_API_KEY",
        "ANTHROPIC_API_KEY",
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    return len(missing_vars) == 0, missing_vars


def check_python_dependencies() -> Tuple[bool, List[str]]:
    """Check if all required Python packages are installed."""
    required_packages = [
        "supabase",
        "pytest",
        "pytest-asyncio",
        "asyncio",
        "uuid",
        "datetime",
        "json",
        "random",
    ]
    
    # For Google ADK, we'll check separately since it's optional
    
    missing_packages = []
    for package in required_packages:
        try:
            importlib.import_module(package)
        except ImportError:
            missing_packages.append(package)
    
    return len(missing_packages) == 0, missing_packages


def check_google_adk() -> Tuple[bool, str]:
    """Check if Google ADK is installed and return the version."""
    try:
        spec = importlib.util.find_spec("google.adk")
        if spec is None:
            return False, "Google ADK not found"
        
        import google.adk
        version = getattr(google.adk, "__version__", "Unknown")
        return True, f"Google ADK version {version}"
    except ImportError:
        return False, "Google ADK not found"


def check_anthropic() -> Tuple[bool, str]:
    """Check if Anthropic Python SDK is installed."""
    try:
        spec = importlib.util.find_spec("anthropic")
        if spec is None:
            return False, "Anthropic SDK not found"
        
        import anthropic
        version = getattr(anthropic, "__version__", "Unknown")
        return True, f"Anthropic SDK version {version}"
    except ImportError:
        return False, "Anthropic SDK not found"


def check_supabase_connection() -> Tuple[bool, str]:
    """Check if the Supabase connection works."""
    env_ok, missing_vars = check_environment_variables()
    if not env_ok or "SUPABASE_URL" in missing_vars or "SUPABASE_SERVICE_ROLE" in missing_vars:
        return False, "Cannot check Supabase connection: missing environment variables"
    
    try:
        from supabase import create_client
        
        # Initialize the Supabase client
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE")
        client = create_client(url, key)
        
        # Try a simple query to check connection
        result = client.table("users").select("count").limit(1).execute()
        return True, "Supabase connection successful"
    except Exception as e:
        return False, f"Supabase connection failed: {str(e)}"


def print_result(name: str, success: bool, message: str = "") -> None:
    """Print a formatted check result."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {name:<40} | {message}")


def main() -> Dict[str, Any]:
    """Run all checks and return results."""
    print("\n🔍 INSTABIDS MULTI-AGENT TEST ENVIRONMENT CHECK 🔍\n")
    print("-" * 80)
    print(f"{'':<8} | {'CHECK':<40} | {'DETAILS'}")
    print("-" * 80)
    
    # Check environment variables
    env_ok, missing_vars = check_environment_variables()
    print_result(
        "Environment Variables", 
        env_ok, 
        ", ".join(missing_vars) if missing_vars else "All required variables set"
    )
    
    # Check Python dependencies
    deps_ok, missing_deps = check_python_dependencies()
    print_result(
        "Python Dependencies", 
        deps_ok, 
        ", ".join(missing_deps) if missing_deps else "All dependencies installed"
    )
    
    # Check Google ADK
    adk_ok, adk_msg = check_google_adk()
    print_result("Google ADK", adk_ok, adk_msg)
    
    # Check Anthropic SDK
    anthropic_ok, anthropic_msg = check_anthropic()
    print_result("Anthropic SDK", anthropic_ok, anthropic_msg)
    
    # Check Supabase connection
    supabase_ok, supabase_msg = check_supabase_connection()
    print_result("Supabase Connection", supabase_ok, supabase_msg)
    
    # Overall status
    all_passed = env_ok and deps_ok and (adk_ok or not adk_ok)  # ADK is optional
    print("-" * 80)
    if all_passed:
        print("\n✅ ENVIRONMENT CHECK PASSED: Ready for multi-agent tests!\n")
    else:
        print("\n❌ ENVIRONMENT CHECK FAILED: Please fix the issues above before running tests.\n")
    
    return {
        "environment_variables": {
            "status": env_ok,
            "missing": missing_vars
        },
        "python_dependencies": {
            "status": deps_ok,
            "missing": missing_deps
        },
        "google_adk": {
            "status": adk_ok,
            "message": adk_msg
        },
        "anthropic_sdk": {
            "status": anthropic_ok,
            "message": anthropic_msg
        },
        "supabase_connection": {
            "status": supabase_ok,
            "message": supabase_msg
        },
        "overall_status": all_passed
    }


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result["overall_status"] else 1)
