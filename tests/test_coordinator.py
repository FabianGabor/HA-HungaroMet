"""Tests for coordinator.py"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import timedelta

from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.hungaromet.coordinator import HungarometDataCoordinator


@pytest.mark.asyncio
async def test_coordinator_init():
    """Test coordinator initialization."""
    hass = MagicMock()

    coordinator = HungarometDataCoordinator(
        hass=hass,
        data_type="daily",
        update_interval=timedelta(hours=1),
        distance_km=10.0,
    )

    assert coordinator.data_type == "daily"
    assert coordinator.distance_km == 10.0
    assert coordinator.name == "HungaroMet daily"


@pytest.mark.asyncio
async def test_coordinator_daily_data_fetch():
    """Test coordinator fetches daily data."""
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(
        return_value=({"time": "2024-01-01", "average_t": 5.5}, [])
    )

    coordinator = HungarometDataCoordinator(
        hass=hass,
        data_type="daily",
        update_interval=timedelta(hours=1),
    )

    result = await coordinator._async_update_data()

    assert result["data"]["time"] == "2024-01-01"
    assert result["data"]["average_t"] == 5.5
    assert "station_info" in result
    hass.async_add_executor_job.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_hourly_data_fetch():
    """Test coordinator fetches hourly data."""
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(
        return_value=({"time": "2024-01-01T12:00:00", "average_t": 8.2}, [])
    )

    coordinator = HungarometDataCoordinator(
        hass=hass,
        data_type="hourly",
        update_interval=timedelta(minutes=60),
        distance_km=15.0,
    )

    result = await coordinator._async_update_data()

    assert result["data"]["time"] == "2024-01-01T12:00:00"
    assert result["data"]["average_t"] == 8.2
    hass.async_add_executor_job.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_ten_minutes_data_fetch():
    """Test coordinator fetches ten minutes data."""
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(
        return_value=({"time": "2024-01-01T12:10:00", "average_t": 7.1}, [])
    )

    coordinator = HungarometDataCoordinator(
        hass=hass,
        data_type="ten_minutes",
        update_interval=timedelta(minutes=10),
    )

    result = await coordinator._async_update_data()

    assert result["data"]["time"] == "2024-01-01T12:10:00"
    hass.async_add_executor_job.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_unknown_data_type():
    """Test coordinator raises ValueError for unknown data type."""
    hass = MagicMock()

    coordinator = HungarometDataCoordinator(
        hass=hass,
        data_type="invalid_type",
        update_interval=timedelta(hours=1),
    )

    with pytest.raises(UpdateFailed, match="Unknown data type"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_fetch_error_raises_update_failed():
    """Test coordinator raises UpdateFailed on fetch error."""
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(side_effect=Exception("Network error"))

    coordinator = HungarometDataCoordinator(
        hass=hass,
        data_type="daily",
        update_interval=timedelta(hours=1),
    )

    with pytest.raises(UpdateFailed, match="Error fetching daily data"):
        await coordinator._async_update_data()
