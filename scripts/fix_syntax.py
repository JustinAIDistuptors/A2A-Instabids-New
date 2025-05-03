#!/usr/bin/env python3
"""
Script to automatically fix common Python syntax issues:
- E701: Multiple statements on one line (colon)
- F821: Undefined name (missing imports)
"""

import os
import re
import sys
from pathlib import Path

def fix_e701(content):
    """Fix E701: Multiple statements on one line (colon)"""
    # Pattern for if/for/while statements with code on same line
    pattern = r'(^\s*(?:if|for|while|elif|else)\s+.*?):(\s*\S.*?)$'
    
    # Replace with proper indentation
    def replace(match):
        stmt, code = match.groups()
        indent = len(match.group(0)) - len(match.group(0).lstrip())
        return f"{stmt}:\n{' ' * (indent + 4)}{code.lstrip()}"
    
    return re.sub(pattern, replace, content, flags=re.MULTILINE)

def add_missing_imports(content, filename):
    """Add commonly missing imports"""
    missing_imports = []
    
    # Check for common undefined names
    if 'json' in content and 'import json' not in content:
        missing_imports.append('import json')
    
    if 'datetime' in content and 'import datetime' not in content and 'from datetime import' not in content:
        missing_imports.append('import datetime')
    
    if 'typing' not in content and any(x in content for x in ['List', 'Dict', 'Optional', 'Union', 'Any', 'Tuple']):
        missing_imports.append('from typing import List, Dict, Optional, Union, Any, Tuple')
    
    # Add imports if needed
    if missing_imports:
        # Find the right position to add imports (after existing imports)
        import_section_end = 0
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_section_end = i + 1
        
        # Insert imports after the last import or at the top
        for imp in missing_imports:
            lines.insert(import_section_end, imp)
            import_section_end += 1
        
        return '\n'.join(lines)
    
    return content

def process_file(filepath):
    """Process a single Python file to fix common issues"""
    print(f"Processing {filepath}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Apply fixes
    fixed_content = fix_e701(content)
    fixed_content = add_missing_imports(fixed_content, filepath)
    
    # Only write if changes were made
    if fixed_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        print(f"Fixed issues in {filepath}")
    else:
        print(f"No issues found in {filepath}")

def main():
    """Main function to process Python files"""
    # Get the repository root directory
    repo_root = Path(__file__).parent.parent
    
    # Files with known issues
    problem_files = [
        'legacy_src/agents/homeowner/agent.py',
        'src/instabids/agents/homeowner_agent.py',
        'src/instabids/data/project_repo.py',
        'legacy_src/agents/matching/agent.py',
        'src/instabids/agents/messaging_agent.py',
        'src/instabids/webhooks.py',
    ]
    
    # Process each file
    for file_path in problem_files:
        full_path = repo_root / file_path
        if full_path.exists():
            process_file(full_path)
        else:
            print(f"Warning: {file_path} not found")
    
    print("Syntax fixing complete!")

if __name__ == "__main__":
    main()