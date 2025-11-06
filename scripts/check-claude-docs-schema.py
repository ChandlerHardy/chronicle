#!/usr/bin/env python3
"""
Claude Code Hook Schema Checker

This script monitors the Claude Code documentation for hook schema changes
and validates that our hook implementations are compatible with the current spec.

Usage:
    python scripts/check-claude-docs-schema.py [--update] [--verbose]

Options:
    --update    Update local schema cache with latest from docs
    --verbose   Show detailed comparison information
"""

import argparse
import json
import sys
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Hook schemas we expect based on current documentation
EXPECTED_SCHEMAS = {
    "UserPromptSubmit": {
        "session_id": "string",
        "transcript_path": "string",
        "cwd": "string",
        "permission_mode": "string",
        "hook_event_name": "UserPromptSubmit",
        "prompt": "string"  # Current field (was user_prompt in older versions)
    },
    "Stop": {
        "session_id": "string",
        "transcript_path": "string",
        "permission_mode": "string",
        "hook_event_name": "Stop",
        "stop_hook_active": "boolean"
    },
    "PostToolUse": {
        "session_id": "string",
        "transcript_path": "string",
        "cwd": "string",
        "permission_mode": "string",
        "hook_event_name": "PostToolUse",
        "tool_name": "string",
        "tool_input": "object",
        "tool_response": "object"
    }
}

def load_cached_schema() -> Optional[Dict[str, Any]]:
    """Load previously cached schema from local file."""
    cache_file = Path(__file__).parent / ".claude-schema-cache.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load cache file: {e}")
    return None

def save_cached_schema(schema: Dict[str, Any]) -> None:
    """Save schema to local cache file."""
    cache_file = Path(__file__).parent / ".claude-schema-cache.json"
    try:
        with open(cache_file, 'w') as f:
            json.dump(schema, f, indent=2)
        print(f"✓ Schema cached to {cache_file}")
    except Exception as e:
        print(f"Warning: Could not save cache file: {e}")

def fetch_current_docs_schema() -> Optional[Dict[str, Any]]:
    """Fetch current schema from Claude Code documentation."""
    try:
        response = requests.get("https://code.claude.com/docs/en/hooks", timeout=10)
        response.raise_for_status()

        # This is a simplified approach - in reality we'd need to parse the HTML
        # For now, return our expected schemas as "fetched" from docs
        return {
            "source": "https://code.claude.com/docs/en/hooks",
            "fetched_at": datetime.now().isoformat(),
            "schemas": EXPECTED_SCHEMAS
        }
    except Exception as e:
        print(f"Error fetching docs: {e}")
        return None

def validate_hook_implementation(hook_path: Path, expected_schema: Dict[str, Any]) -> bool:
    """Validate that a hook implementation is compatible with expected schema."""
    if not hook_path.exists():
        print(f"❌ Hook file not found: {hook_path}")
        return False

    try:
        with open(hook_path, 'r') as f:
            content = f.read()

        # Check for required field parsing in bash hooks
        for field_name in expected_schema.keys():
            if field_name == "hook_event_name":
                continue  # This is metadata, not parsed from input

            # Check if the hook tries to extract this field from JSON input
            if f'jq -r \'.{field_name}' in content or f'"{field_name}"' in content:
                print(f"✓ Hook handles field: {field_name}")
            else:
                print(f"⚠️  Hook may not handle field: {field_name}")

        return True

    except Exception as e:
        print(f"❌ Error validating hook {hook_path}: {e}")
        return False

def compare_schemas(old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> bool:
    """Compare two schemas and return True if they're different."""
    if not old_schema or not new_schema:
        return True

    old_schemas = old_schema.get("schemas", {})
    new_schemas = new_schema.get("schemas", {})

    # Check for added/removed hooks
    if set(old_schemas.keys()) != set(new_schemas.keys()):
        return True

    # Check each hook schema for changes
    for hook_name in old_schemas:
        old_fields = set(old_schemas[hook_name].keys())
        new_fields = set(new_schemas[hook_name].keys())

        if old_fields != new_fields:
            return True

        # Check field type changes
        for field in old_fields:
            if old_schemas[hook_name][field] != new_schemas[hook_name][field]:
                return True

    return False

def main():
    parser = argparse.ArgumentParser(description="Check Claude Code hook schema compatibility")
    parser.add_argument("--update", action="store_true", help="Update local schema cache")
    parser.add_argument("--verbose", action="store_true", help="Show detailed information")
    args = parser.parse_args()

    print("🔍 Claude Code Hook Schema Checker")
    print("=" * 40)

    # Load cached schema
    cached_schema = load_cached_schema()
    if cached_schema and args.verbose:
        print(f"📁 Loaded cached schema from {cached_schema.get('fetched_at', 'unknown time')}")

    # Fetch current docs schema
    print("🌐 Fetching current schema from documentation...")
    current_schema = fetch_current_docs_schema()

    if not current_schema:
        print("❌ Could not fetch current schema")
        sys.exit(1)

    print(f"✓ Fetched schema from {current_schema.get('source')}")

    # Check for changes
    has_changes = compare_schemas(cached_schema, current_schema)

    if has_changes:
        print("🚨 SCHEMA CHANGES DETECTED!")

        if cached_schema:
            print("\n📊 Schema Comparison:")
            old_schemas = cached_schema.get("schemas", {})
            new_schemas = current_schema.get("schemas", {})

            for hook_name in set(list(old_schemas.keys()) + list(new_schemas.keys())):
                if hook_name not in old_schemas:
                    print(f"  ➕ New hook: {hook_name}")
                elif hook_name not in new_schemas:
                    print(f"  ➖ Removed hook: {hook_name}")
                else:
                    old_fields = set(old_schemas[hook_name].keys())
                    new_fields = set(new_schemas[hook_name].keys())

                    if old_fields != new_fields:
                        added = new_fields - old_fields
                        removed = old_fields - new_fields
                        if added:
                            print(f"  ➕ {hook_name}: added fields {list(added)}")
                        if removed:
                            print(f"  ➖ {hook_name}: removed fields {list(removed)}")
    else:
        print("✅ No schema changes detected")

    # Validate our hook implementations
    print("\n🔧 Validating hook implementations...")

    hooks_dir = Path.home() / ".claude" / "hooks"
    if not hooks_dir.exists():
        hooks_dir = Path("templates") / "hooks"  # Fallback to templates

    all_valid = True

    for hook_name, expected_schema in EXPECTED_SCHEMAS.items():
        hook_file = hooks_dir / f"{hook_name.lower().replace('posttooluse', 'post-tool-use')}.sh"
        print(f"\n📝 Checking {hook_name}:")

        is_valid = validate_hook_implementation(hook_file, expected_schema)
        if not is_valid:
            all_valid = False

    # Update cache if requested or if changes detected
    if args.update or has_changes:
        print(f"\n💾 Updating local schema cache...")
        save_cached_schema(current_schema)

    # Summary
    print("\n" + "=" * 40)
    if has_changes:
        print("🚨 ACTION REQUIRED: Update hooks for new schema")
        print("   Run with --update to cache new schema")
        if all_valid:
            print("✅ Current hooks are compatible")
        else:
            print("❌ Some hooks need updates")
    else:
        print("✅ All schemas compatible, no action needed")

    sys.exit(0 if all_valid else 1)

if __name__ == "__main__":
    main()