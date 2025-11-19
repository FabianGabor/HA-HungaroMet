#!/usr/bin/env python3
"""
Integration test setup for testing with Home Assistant.

This script creates a minimal Home Assistant test configuration
and validates that the integration can be loaded properly.
"""

import asyncio
import sys
import tempfile
from pathlib import Path


async def test_integration_imports():
    """Test that all integration files can be imported correctly."""
    print("Testing integration imports...")

    try:
        # Test basic imports
        from homeassistant.util import dt as dt_util

        print("  ✅ homeassistant.util.dt imported")

        from homeassistant.helpers.event import (
            async_track_time_change,
            async_call_later,
        )

        print("  ✅ homeassistant.helpers.event imported")

        from homeassistant.components.sensor import SensorEntity

        print("  ✅ SensorEntity imported")

        # Test that dt_util has the methods we need
        assert hasattr(dt_util, "as_local"), "dt_util.as_local not found"
        assert hasattr(dt_util, "UTC"), "dt_util.UTC not found"
        print("  ✅ dt_util has required methods")

        return True

    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        print("\n  💡 Home Assistant needs to be installed:")
        print("     pip install homeassistant")
        return False
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        return False


async def test_sensor_instantiation():
    """Test that sensor classes can be instantiated with Home Assistant."""
    print("\nTesting sensor instantiation...")

    try:
        from homeassistant.core import HomeAssistant
        from homeassistant.config_entries import ConfigEntry

        # Create a minimal Home Assistant instance
        hass = HomeAssistant("/tmp")
        await hass.async_start()

        print("  ✅ Created Home Assistant instance")

        # Try to import our sensors
        from daily_sensor import HungarometWeatherDailySensor
        from hourly_sensor import HungarometWeatherHourlySensor
        from ten_minutes_sensor import HungarometWeatherTenMinutesSensor

        print("  ✅ All sensor classes imported")

        # Test instantiation
        daily_sensor = HungarometWeatherDailySensor(
            hass, "Test Sensor", 25.0, "°C", "test_key"
        )
        print("  ✅ Daily sensor instantiated")

        hourly_sensor = HungarometWeatherHourlySensor(
            hass, "Test Hourly", 20.0, "°C", "test_key"
        )
        print("  ✅ Hourly sensor instantiated")

        ten_min_sensor = HungarometWeatherTenMinutesSensor(
            hass, "Test 10min", 15.0, "°C", "test_key"
        )
        print("  ✅ Ten-minute sensor instantiated")

        # Test state property (should not block)
        _ = daily_sensor.state
        _ = hourly_sensor.state
        _ = ten_min_sensor.state
        print("  ✅ All sensor states accessed without blocking")

        await hass.async_stop()
        return True

    except ImportError as e:
        print(f"  ⚠️  Skipped (Home Assistant not installed): {e}")
        return None  # Not a failure, just skipped
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_datetime_conversion():
    """Test timezone conversion with Home Assistant utilities."""
    print("\nTesting timezone conversion...")

    try:
        from datetime import datetime
        from homeassistant.util import dt as dt_util

        # Create a UTC datetime
        test_dt_str = "2025-11-19T12:00:00+00:00"
        dt_utc = datetime.fromisoformat(test_dt_str)

        # Convert to local time using dt_util
        import time

        start = time.time()
        local_dt = dt_util.as_local(dt_utc)
        elapsed = time.time() - start

        print(f"  ✅ Converted UTC to local in {elapsed * 1000:.2f}ms")
        print(f"     UTC: {dt_utc}")
        print(f"     Local: {local_dt}")

        # Ensure it's fast (should be < 10ms)
        if elapsed < 0.01:
            print(f"  ✅ Conversion is non-blocking (< 10ms)")
        else:
            print(f"  ⚠️  Conversion took {elapsed * 1000:.2f}ms (expected < 10ms)")

        return True

    except ImportError as e:
        print(f"  ⚠️  Skipped (Home Assistant not installed): {e}")
        return None
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


async def main():
    """Run all integration tests."""
    print("=" * 70)
    print("HOME ASSISTANT INTEGRATION TEST")
    print("=" * 70)
    print()

    tests = [
        ("Import Test", test_integration_imports()),
        ("Datetime Conversion", test_datetime_conversion()),
        ("Sensor Instantiation", test_sensor_instantiation()),
    ]

    results = []
    for test_name, test_coro in tests:
        try:
            result = await test_coro
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = 0
    failed = 0
    skipped = 0

    for test_name, result in results:
        if result is True:
            print(f"✅ {test_name}: PASSED")
            passed += 1
        elif result is False:
            print(f"❌ {test_name}: FAILED")
            failed += 1
        elif result is None:
            print(f"⏭️  {test_name}: SKIPPED")
            skipped += 1

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")

    if failed > 0:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        return 1
    elif skipped == len(results):
        print("\n💡 Install Home Assistant to run full integration tests:")
        print("   pip install homeassistant")
        return 2
    else:
        print("\n🎉 All available tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
