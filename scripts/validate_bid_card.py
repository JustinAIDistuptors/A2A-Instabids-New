#!/usr/bin/env python
"""
Bid Card Validation Script

This script validates bid card JSON data against the BidCard Pydantic model.
It can be used to validate a single file or all JSON files in a directory.

Usage:
    python validate_bid_card.py path/to/file.json
    python validate_bid_card.py --dir path/to/directory

Options:
    --dir       Validate all JSON files in the specified directory
    --verbose   Show detailed validation errors
    --fix       Attempt to fix common issues in the JSON files
"""
import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the BidCard model
from instabids.models.bid_card import BidCard
from pydantic import ValidationError

def validate_file(file_path: str, verbose: bool = False, fix: bool = False) -> bool:
    """
    Validate a single JSON file against the BidCard model.
    
    Args:
        file_path: Path to the JSON file
        verbose: Whether to show detailed validation errors
        fix: Whether to attempt to fix common issues
        
    Returns:
        bool: True if validation passed, False otherwise
    """
    try:
        # Read the JSON file
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # If fix is enabled, attempt to fix common issues
        if fix:
            data = fix_common_issues(data)
            # Write the fixed data back to the file
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        
        # Validate against the BidCard model
        bid_card = BidCard(**data)
        print(f"✅ {file_path}: Valid")
        return True
        
    except FileNotFoundError:
        print(f"❌ {file_path}: File not found")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ {file_path}: Invalid JSON - {str(e)}")
        return False
    except ValidationError as e:
        if verbose:
            print(f"❌ {file_path}: Validation failed")
            for error in e.errors():
                print(f"  - {error['loc']}: {error['msg']}")
        else:
            print(f"❌ {file_path}: Validation failed - use --verbose for details")
        return False
    except Exception as e:
        print(f"❌ {file_path}: Unexpected error - {str(e)}")
        return False

def fix_common_issues(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fix common issues in bid card data.
    
    Args:
        data: Bid card data
        
    Returns:
        Dict with fixed data
    """
    # Ensure budget_range is a tuple/list with two integers
    if "budget_range" in data and not isinstance(data["budget_range"], (list, tuple)):
        if isinstance(data["budget_range"], str):
            # Try to parse from string like "$1,000-$5,000"
            try:
                parts = data["budget_range"].replace("$", "").replace(",", "").split("-")
                if len(parts) == 2:
                    data["budget_range"] = [int(parts[0]), int(parts[1])]
            except:
                # Default range if parsing fails
                data["budget_range"] = [0, 10000]
        else:
            # Default range
            data["budget_range"] = [0, 10000]
    
    # Ensure images is a list
    if "images" in data and not isinstance(data["images"], list):
        data["images"] = []
    
    # Ensure group_bidding is a boolean
    if "group_bidding" in data and not isinstance(data["group_bidding"], bool):
        if isinstance(data["group_bidding"], str):
            data["group_bidding"] = data["group_bidding"].lower() in ["true", "yes", "1"]
        else:
            data["group_bidding"] = bool(data["group_bidding"])
    
    return data

def validate_directory(dir_path: str, verbose: bool = False, fix: bool = False) -> Dict[str, int]:
    """
    Validate all JSON files in a directory against the BidCard model.
    
    Args:
        dir_path: Path to the directory
        verbose: Whether to show detailed validation errors
        fix: Whether to attempt to fix common issues
        
    Returns:
        Dict with counts of valid and invalid files
    """
    if not os.path.isdir(dir_path):
        print(f"❌ {dir_path} is not a directory")
        return {"valid": 0, "invalid": 0}
    
    valid_count = 0
    invalid_count = 0
    
    for file_path in Path(dir_path).glob("**/*.json"):
        if validate_file(str(file_path), verbose, fix):
            valid_count += 1
        else:
            invalid_count += 1
    
    return {"valid": valid_count, "invalid": invalid_count}

def main():
    parser = argparse.ArgumentParser(description="Validate bid card JSON data against the BidCard model")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("file", nargs="?", help="Path to the JSON file to validate")
    group.add_argument("--dir", help="Path to the directory containing JSON files to validate")
    parser.add_argument("--verbose", action="store_true", help="Show detailed validation errors")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix common issues")
    
    args = parser.parse_args()
    
    if args.dir:
        results = validate_directory(args.dir, args.verbose, args.fix)
        print(f"\nSummary: {results['valid']} valid, {results['invalid']} invalid")
    else:
        validate_file(args.file, args.verbose, args.fix)

if __name__ == "__main__":
    main()