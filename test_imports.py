#!/usr/bin/env python
"""Test script to verify that imports work correctly with the vendor namespace approach."""

import sys
import os

# Add the current directory to the path so we can import the package
sys.path.insert(0, os.path.abspath("."))

def test_imports():
    """Test that imports work correctly."""
    print("Testing imports...")
    
    # Test importing LlmAgent
    try:
        from instabids_google.adk import LlmAgent
        print("✅ Successfully imported LlmAgent")
    except ImportError as e:
        print(f"❌ Failed to import LlmAgent: {e}")
        return False
    
    # Test importing enable_tracing
    try:
        from instabids_google.adk import enable_tracing
        print("✅ Successfully imported enable_tracing")
    except ImportError as e:
        print(f"❌ Failed to import enable_tracing: {e}")
        return False
    
    # Test creating an instance of LlmAgent
    try:
        agent = LlmAgent("TestAgent")
        print(f"✅ Successfully created an LlmAgent instance: {agent.name}")
    except Exception as e:
        print(f"❌ Failed to create LlmAgent instance: {e}")
        return False
    
    print("\nAll imports and basic functionality tests passed!")
    return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)