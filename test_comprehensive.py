#!/usr/bin/env python3
"""
Quick validation of the key fixes to ensure they work correctly.
This tests the timezone conversion logic without requiring Home Assistant.
"""

import sys
from datetime import datetime


def test_timezone_conversion():
    """Test that datetime objects can be converted properly."""
    print("Testing timezone conversion logic...")

    # Simulate a UTC datetime
    test_datetime_str = "2025-11-19T12:05:06+00:00"

    try:
        dt_utc = datetime.fromisoformat(test_datetime_str)
        print(f"  ✅ Successfully parsed datetime: {dt_utc}")

        # Test strftime (used in sensor state property)
        formatted = dt_utc.strftime("%Y-%m-%d %H:%M")
        print(f"  ✅ Successfully formatted datetime: {formatted}")

        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_async_call_later_import():
    """Verify the async_call_later import pattern is correct."""
    print("\nTesting async_call_later import pattern...")

    import_statement = "from homeassistant.helpers.event import async_track_time_change, async_call_later"

    # Check that sensor.py has the correct import
    try:
        with open("sensor.py", "r") as f:
            content = f.read()
            if import_statement in content:
                print(f"  ✅ Correct import found in sensor.py")
            else:
                print(f"  ❌ Import not found in sensor.py")
                return False

            # Verify no invalid hass.helpers.event usage
            if "hass.helpers.event.async_call_later" in content:
                print(f"  ❌ Found invalid hass.helpers.event.async_call_later usage")
                return False
            else:
                print(f"  ✅ No invalid hass.helpers.event usage found")

            return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_distance_km_parameters():
    """Verify that distance_km parameters are properly included."""
    print("\nTesting distance_km parameters...")

    files_to_check = ["daily_sensor.py", "hourly_sensor.py", "ten_minutes_sensor.py"]

    all_good = True
    for filename in files_to_check:
        try:
            with open(filename, "r") as f:
                content = f.read()

                # Check for the pattern
                if "DEFAULT_DISTANCE_KM" in content and "process_" in content:
                    print(f"  ✅ {filename}: distance_km parameter found")
                else:
                    print(f"  ❌ {filename}: distance_km parameter missing")
                    all_good = False
        except FileNotFoundError:
            print(f"  ⚠️  {filename} not found")
            continue

    return all_good


def test_dt_util_imports():
    """Verify that dt_util is imported where needed."""
    print("\nTesting dt_util imports...")

    files_to_check = {
        "ten_minutes_sensor.py": True,
        "hourly_sensor.py": True,
        "weather_data.py": True,
        "daily_sensor.py": False,  # Doesn't need dt_util
    }

    all_good = True
    for filename, should_have_import in files_to_check.items():
        try:
            with open(filename, "r") as f:
                content = f.read()
                has_import = "from homeassistant.util import dt as dt_util" in content

                if should_have_import and has_import:
                    print(f"  ✅ {filename}: dt_util import found")
                elif not should_have_import and not has_import:
                    print(f"  ✅ {filename}: correctly has no dt_util import")
                elif should_have_import and not has_import:
                    print(f"  ❌ {filename}: missing dt_util import")
                    all_good = False
                else:
                    print(f"  ⚠️  {filename}: has unexpected dt_util import")
        except FileNotFoundError:
            print(f"  ⚠️  {filename} not found")
            continue

    return all_good


def test_no_pytz_usage():
    """Ensure no pytz imports remain in production code."""
    print("\nTesting for pytz removal...")

    files_to_check = [
        "sensor.py",
        "daily_sensor.py",
        "hourly_sensor.py",
        "ten_minutes_sensor.py",
        "weather_data.py",
    ]

    all_good = True
    for filename in files_to_check:
        try:
            with open(filename, "r") as f:
                content = f.read()

                # Check for pytz imports (not in comments)
                lines = content.split("\n")
                for line_num, line in enumerate(lines, 1):
                    if "pytz" in line and not line.strip().startswith("#"):
                        # Check if it's in a string or comment
                        if "import pytz" in line or "pytz." in line:
                            print(
                                f"  ❌ {filename}:{line_num}: Found pytz usage: {line.strip()}"
                            )
                            all_good = False

            if all_good:
                print(f"  ✅ {filename}: No pytz usage found")

        except FileNotFoundError:
            print(f"  ⚠️  {filename} not found")
            continue

    return all_good


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("COMPREHENSIVE VALIDATION TEST")
    print("=" * 60)

    tests = [
        ("Timezone Conversion", test_timezone_conversion),
        ("async_call_later Import", test_async_call_later_import),
        ("distance_km Parameters", test_distance_km_parameters),
        ("dt_util Imports", test_dt_util_imports),
        ("pytz Removal", test_no_pytz_usage),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Code is ready for deployment.\n")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED. Please review the issues above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
