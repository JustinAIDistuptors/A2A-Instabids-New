#!/usr/bin/env python
"""
Fix common syntax issues in test files.

This script:
1. Adds missing import statements
2. Fixes pytest.mark.asyncio annotations
3. Adds missing mock_environment fixtures to tests that need it
"""

import os
import re
import sys
from pathlib import Path

# Constants
TEST_DIR = Path(__file__).parent.parent / "tests"
ASYNCIO_IMPORT = "import pytest"
MISSING_ASYNCIO_MARKER = re.compile(r'^(\s*)async\s+def\s+test_', re.MULTILINE)
SUPABASE_CLIENT_IMPORT = "from supabase import create_client"


def fix_test_file(file_path):
    """
    Fix common issues in a test file.
    
    Args:
        file_path: Path to the test file
    
    Returns:
        bool: True if changes were made, False otherwise
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    original_content = content
    changes = []
    
    # Fix 1: Add missing pytest import if using pytest marks
    if "@pytest.mark" in content and ASYNCIO_IMPORT not in content:
        content = ASYNCIO_IMPORT + "\n" + content
        changes.append("Added pytest import")
    
    # Fix 2: Add missing asyncio marker to async test functions
    has_asyncio_import = "pytest-asyncio" in content or "pytest.mark.asyncio" in content
    
    # If we have async test functions but no asyncio import
    if "async def test_" in content and not has_asyncio_import:
        # Add import if needed
        if "import pytest" not in content:
            insert_pos = 0
            import_match = re.search(r'^import\s+', content, re.MULTILINE)
            if import_match:
                # Find the last import statement
                last_import = 0
                for match in re.finditer(r'^(?:import|from)\s+', content, re.MULTILINE):
                    last_import = max(last_import, match.end())
                if last_import > 0:
                    insert_pos = content.find('\n', last_import) + 1
            
            content = content[:insert_pos] + "import pytest\n" + content[insert_pos:]
            changes.append("Added pytest import")
        
        # Add missing asyncio markers
        def add_marker(match):
            indentation = match.group(1)
            return f"{indentation}@pytest.mark.asyncio\n{match.group(0)}"
        
        new_content = MISSING_ASYNCIO_MARKER.sub(add_marker, content)
        if new_content != content:
            content = new_content
            changes.append("Added missing asyncio markers")
    
    # Fix 3: Add missing Supabase client import
    if "supabase" in content and SUPABASE_CLIENT_IMPORT not in content and "client" in content:
        # Find a good place to insert the import
        insert_pos = 0
        import_match = re.search(r'^import\s+', content, re.MULTILINE)
        if import_match:
            # Find the last import statement
            last_import = 0
            for match in re.finditer(r'^(?:import|from)\s+', content, re.MULTILINE):
                last_import = max(last_import, match.end())
            if last_import > 0:
                insert_pos = content.find('\n', last_import) + 1
        
        content = content[:insert_pos] + SUPABASE_CLIENT_IMPORT + "\n" + content[insert_pos:]
        changes.append("Added Supabase client import")
    
    # Fix 4: Fix pytest.fixture usage for test classes
    if "class Test" in content and "self" in content and "@pytest.fixture" in content:
        # Fix fixture usage in test classes
        content = content.replace("@pytest.fixture", "@classmethod\n    @pytest.fixture")
        changes.append("Fixed fixture usage in test classes")
    
    # Write the file if changes were made
    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Fixed {file_path.name}: {', '.join(changes)}")
        return True
    
    return False


def main():
    """Main function."""
    # Find all test files
    test_files = []
    for root, _, files in os.walk(TEST_DIR):
        for file in files:
            if file.endswith(".py") and (file.startswith("test_") or root.endswith("tests")):
                test_files.append(Path(root) / file)
    
    # Fix all test files
    changes_made = 0
    for file_path in test_files:
        if fix_test_file(file_path):
            changes_made += 1
    
    print(f"Fixed {changes_made} of {len(test_files)} test files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
