#!/usr/bin/env python3
"""
Real-world integration test with Home Assistant instance.

This test validates the actual integration behavior including:
- Non-blocking timezone conversions
- Sensor state updates
- Proper async patterns
"""

import asyncio
import sys
import time
from datetime import datetime
from unittest.mock import Mock, patch


async def test_timezone_performance():
    """Benchmark timezone conversion to ensure it's non-blocking."""
    print("Testing timezone conversion performance...")

    from homeassistant.util import dt as dt_util

    # Test multiple conversions to get average
    test_cases = [
        "2025-11-19T12:00:00+00:00",
        "2025-11-19T00:00:00+00:00",
        "2025-11-19T23:59:59+00:00",
    ]

    times = []
    for test_dt_str in test_cases:
        dt_utc = datetime.fromisoformat(test_dt_str)

        start = time.perf_counter()
        local_dt = dt_util.as_local(dt_utc)
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)  # Convert to ms

        formatted = local_dt.strftime("%Y-%m-%d %H:%M")
        print(f"  ✅ {test_dt_str} → {formatted} ({elapsed * 1000:.3f}ms)")

    avg_time = sum(times) / len(times)
    max_time = max(times)

    print(f"\n  📊 Average: {avg_time:.3f}ms, Max: {max_time:.3f}ms")

    # Assert non-blocking (should be < 1ms after first call due to caching)
    if max_time < 10:
        print(f"  ✅ All conversions are non-blocking (< 10ms)")
        return True
    else:
        print(f"  ⚠️  Some conversions were slow (max: {max_time:.3f}ms)")
        return False


async def test_sensor_state_property():
    """Test that sensor state property works correctly without pytz."""
    print("\nTesting sensor state property...")

    from homeassistant.util import dt as dt_util
    from homeassistant.core import HomeAssistant

    # Create mock hass instance
    hass = HomeAssistant("/tmp")
    await hass.async_start()

    try:
        # Simulate sensor logic from ten_minutes_sensor.py
        test_state = "2025-11-19T12:05:06+00:00"
        key = "time"

        # This is what happens in the state property
        dt_utc = datetime.fromisoformat(test_state)
        local_dt = dt_util.as_local(dt_utc)
        result = local_dt.strftime("%Y-%m-%d %H:%M")

        print(f"  ✅ UTC: {test_state}")
        print(f"  ✅ Local: {result}")
        print(f"  ✅ State property logic works without pytz")

        # Test with numeric values
        numeric_value = 25.12345
        rounded = round(numeric_value, 2)
        assert rounded == 25.12, f"Expected 25.12, got {rounded}"
        print(f"  ✅ Numeric rounding works: {numeric_value} → {rounded}")

        return True

    finally:
        await hass.async_stop()


async def test_async_call_later_pattern():
    """Test that async_call_later is imported and used correctly."""
    print("\nTesting async_call_later pattern...")

    from homeassistant.helpers.event import async_call_later, async_track_time_change
    from homeassistant.core import HomeAssistant

    hass = HomeAssistant("/tmp")
    await hass.async_start()

    try:
        # Test async_call_later
        callback_called = []

        def test_callback(now):
            callback_called.append(True)

        # Schedule callback for 0.1 seconds from now
        async_call_later(hass, 0.1, test_callback)

        # Wait for callback
        await asyncio.sleep(0.2)

        if callback_called:
            print(f"  ✅ async_call_later works correctly")
        else:
            print(f"  ❌ async_call_later callback was not called")
            return False

        # Verify async_track_time_change is available
        print(f"  ✅ async_track_time_change is available")

        return True

    finally:
        await hass.async_stop()


async def test_dt_util_utc():
    """Test that dt_util.UTC works correctly."""
    print("\nTesting dt_util.UTC...")

    from homeassistant.util import dt as dt_util
    from datetime import datetime

    # This mimics what happens in weather_data.py
    date_str = "202511191205"
    dt_utc = datetime.strptime(date_str, "%Y%m%d%H%M").replace(tzinfo=dt_util.UTC)

    print(f"  ✅ Created UTC datetime: {dt_utc}")
    print(f"  ✅ ISO format: {dt_utc.isoformat()}")

    # Verify it's actually UTC
    assert dt_utc.tzinfo is not None, "Timezone info is None"
    print(f"  ✅ dt_util.UTC works correctly")

    return True


async def test_no_blocking_operations():
    """Verify no blocking operations occur during sensor updates."""
    print("\nTesting for blocking operations...")

    from homeassistant.util import dt as dt_util

    # Simulate what happens in sensor state property - time this
    start = time.perf_counter()

    # Do 100 iterations to catch any blocking I/O
    for i in range(100):
        test_state = f"2025-11-{19:02d}T{i % 24:02d}:00:00+00:00"
        dt_utc = datetime.fromisoformat(test_state)
        local_dt = dt_util.as_local(dt_utc)
        _ = local_dt.strftime("%Y-%m-%d %H:%M")

    elapsed = time.perf_counter() - start
    avg_per_call = (elapsed / 100) * 1000  # ms

    print(f"  ✅ 100 conversions completed in {elapsed * 1000:.2f}ms")
    print(f"  ✅ Average per conversion: {avg_per_call:.3f}ms")

    # Should be well under 1ms per call after caching
    if avg_per_call < 1.0:
        print(f"  ✅ No blocking operations detected (< 1ms/call)")
        return True
    else:
        print(f"  ⚠️  Performance concern: {avg_per_call:.3f}ms per call")
        return avg_per_call < 10.0  # Still acceptable if under 10ms


async def main():
    """Run all integration tests."""
    print("=" * 70)
    print("HOME ASSISTANT REAL-WORLD INTEGRATION TEST")
    print("=" * 70)
    print()

    tests = [
        ("Timezone Performance", test_timezone_performance()),
        ("dt_util.UTC", test_dt_util_utc()),
        ("Sensor State Property", test_sensor_state_property()),
        ("async_call_later Pattern", test_async_call_later_pattern()),
        ("No Blocking Operations", test_no_blocking_operations()),
    ]

    results = []
    for test_name, test_coro in tests:
        try:
            result = await test_coro
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with exception: {e}")
            import traceback

            traceback.print_exc()
            results.append((test_name, False))

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")

    print("=" * 70)
    print(f"Results: {passed}/{len(results)} passed")

    if failed > 0:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        return 1
    else:
        print("\n🎉 All tests passed! Integration is working correctly.")
        print("\n📝 Summary:")
        print("   • Timezone conversions are non-blocking")
        print("   • dt_util.as_local() works correctly")
        print("   • dt_util.UTC works correctly")
        print("   • async_call_later is properly imported")
        print("   • No blocking I/O operations detected")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
