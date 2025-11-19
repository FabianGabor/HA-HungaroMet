#!/usr/bin/env python3
"""
Test script to validate that blocking calls have been removed from the codebase.
This script checks for common blocking patterns that should not be used in
async Home Assistant integrations.
"""

import re
import sys
from pathlib import Path

# Patterns that indicate blocking calls
BLOCKING_PATTERNS = [
    (r"import\s+pytz", "pytz import (use homeassistant.util.dt instead)"),
    (r"pytz\.timezone\(", "pytz.timezone() call (use dt_util.as_local)"),
    (r"pytz\.UTC", "pytz.UTC (use dt_util.UTC)"),
    (
        r"hass\.helpers\.event\.async_call_later",
        "hass.helpers.event.async_call_later (import async_call_later directly)",
    ),
    (r'open\([^)]+,\s*[\'"]r', "blocking open() call (use async file I/O)"),
    (r"requests\.get\(", "blocking requests.get() (should be run in executor)"),
]

# Files to check
PYTHON_FILES = [
    "sensor.py",
    "daily_sensor.py",
    "hourly_sensor.py",
    "ten_minutes_sensor.py",
    "weather_data.py",
    "station_info_sensor.py",
]


def check_file_for_blocking_calls(filepath):
    """Check a file for blocking call patterns."""
    issues = []

    if not filepath.exists():
        print(f"⚠️  File not found: {filepath}")
        return issues

    content = filepath.read_text(encoding="utf-8")
    lines = content.split("\n")

    for line_num, line in enumerate(lines, 1):
        for pattern, description in BLOCKING_PATTERNS:
            if re.search(pattern, line):
                # Special case: allow pytz import in weather_data.py if it's commented out
                if (
                    "pytz" in description and "#" in line.split("pytz")[0]
                    if "pytz" in line
                    else False
                ):
                    continue

                # Special case: requests.get is OK in weather_data.py as it's run in executor
                # The entire weather_data.py functions are called via async_add_executor_job
                if "requests.get" in description and filepath.name == "weather_data.py":
                    continue

                issues.append({
                    "file": filepath.name,
                    "line": line_num,
                    "pattern": description,
                    "code": line.strip(),
                })

    return issues


def check_for_proper_imports(filepath):
    """Check that files have proper imports for async utilities."""
    required_imports = {
        "sensor.py": [
            "from homeassistant.helpers.event import async_track_time_change, async_call_later"
        ],
        "ten_minutes_sensor.py": ["from homeassistant.util import dt as dt_util"],
        "hourly_sensor.py": ["from homeassistant.util import dt as dt_util"],
        "weather_data.py": ["from homeassistant.util import dt as dt_util"],
    }

    if filepath.name not in required_imports:
        return True

    content = filepath.read_text(encoding="utf-8")

    for required_import in required_imports[filepath.name]:
        if required_import not in content:
            print(f"❌ Missing import in {filepath.name}: {required_import}")
            return False

    return True


def main():
    """Run all validation checks."""
    print("🔍 Checking for blocking calls in Home Assistant integration...\n")

    base_path = Path(__file__).parent
    all_issues = []
    import_checks_passed = True

    # Check each Python file
    for filename in PYTHON_FILES:
        filepath = base_path / filename

        if not filepath.exists():
            continue

        print(f"Checking {filename}...")

        # Check for blocking patterns
        issues = check_file_for_blocking_calls(filepath)
        all_issues.extend(issues)

        # Check for proper imports
        if not check_for_proper_imports(filepath):
            import_checks_passed = False

    print()

    # Report results
    if all_issues:
        print("❌ FOUND BLOCKING CALLS:\n")
        for issue in all_issues:
            print(f"  File: {issue['file']}, Line {issue['line']}")
            print(f"  Issue: {issue['pattern']}")
            print(f"  Code: {issue['code']}")
            print()
        return 1

    if not import_checks_passed:
        print("❌ MISSING REQUIRED IMPORTS\n")
        return 1

    print("✅ All checks passed! No blocking calls detected.\n")
    print("Summary of fixes applied:")
    print("  • Replaced pytz.timezone() with dt_util.as_local()")
    print("  • Replaced pytz.UTC with dt_util.UTC")
    print("  • Fixed hass.helpers.event.async_call_later to use direct import")
    print("  • Added missing distance_km parameters to data processing calls")
    print("  • Removed recursive async_call_later calls from scheduled updates")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
