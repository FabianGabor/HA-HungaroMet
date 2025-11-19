"""Data coordinator for HungaroMet integration to prevent redundant API calls."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_DISTANCE_KM
from .weather_data import (
    process_daily_data,
    process_hourly_data,
    process_ten_minutes_data,
)

_LOGGER = logging.getLogger(__name__)


class HungarometDataCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching HungaroMet data."""

    def __init__(
        self,
        hass: HomeAssistant,
        data_type: str,
        update_interval: timedelta,
        distance_km: float = DEFAULT_DISTANCE_KM,
    ):
        """Initialize the coordinator."""
        self.data_type = data_type
        self.distance_km = distance_km

        super().__init__(
            hass,
            _LOGGER,
            name=f"HungaroMet {data_type}",
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            if self.data_type == "daily":
                data, station_info = await self.hass.async_add_executor_job(
                    process_daily_data, self.hass, self.distance_km
                )
            elif self.data_type == "hourly":
                data, station_info = await self.hass.async_add_executor_job(
                    process_hourly_data, self.hass, self.distance_km
                )
            elif self.data_type == "ten_minutes":
                data, station_info = await self.hass.async_add_executor_job(
                    process_ten_minutes_data, self.hass, self.distance_km
                )
            else:
                raise ValueError(f"Unknown data type: {self.data_type}")

            return {"data": data, "station_info": station_info}

        except Exception as err:
            _LOGGER.error(f"Error fetching {self.data_type} data: {err}")
            raise UpdateFailed(f"Error fetching {self.data_type} data: {err}")
