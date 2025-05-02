#!/usr/bin/env python3
"""Test script to verify the package structure and imports."""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath('.'))

try:
    print("Testing imports...")
    
    # Test importing LlmAgent
    from instabids_google.adk import LlmAgent
    print("✅ Successfully imported LlmAgent")
    
    # Test importing enable_tracing
    from instabids_google.adk import enable_tracing
    print("✅ Successfully imported enable_tracing")
    
    # Test creating an LlmAgent instance
    agent = LlmAgent(name="TestAgent", system_prompt="This is a test")
    print(f"✅ Successfully created an LlmAgent instance: {agent.name}")
    
    print("\nAll imports and basic functionality tests passed!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nThe package structure might not be set up correctly.")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)