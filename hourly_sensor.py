import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .weather_data import process_hourly_data
from homeassistant.util import dt as dt_util
from .const import DOMAIN, DEFAULT_DISTANCE_KM

_LOGGER = logging.getLogger(__name__)


class HungarometWeatherHourlySensor(SensorEntity):
    def __init__(self, hass, name, value, unit, key, coordinator=None):
        self.hass = hass
        self._name = name
        self._state = value
        self._unit = unit
        self._key = key
        self._device_id = "hungaromet_weather_hourly"
        self._unique_id = f"{self._device_id}_{self._name.lower().replace(' ', '_')}"
        self._added = False
        self.coordinator = coordinator

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        if self._key == "time" and self._state:
            try:
                dt_utc = datetime.fromisoformat(self._state)
                # Use Home Assistant's timezone utilities to avoid blocking calls
                local_dt = dt_util.as_local(dt_utc)
                return local_dt.strftime("%Y-%m-%d %H:%M")
            except Exception as e:
                _LOGGER.warning(f"Failed to convert time for hourly sensor: {e}")
                return self._state
        if isinstance(self._state, (int, float)):
            return round(self._state, 2)
        return self._state if self._state is not None else None

    @property
    def unit_of_measurement(self):
        return self._unit

    @property
    def device_info(self):
        return {
            "identifiers": {(self._device_id,)},
            "name": "HungaroMet órás",
            "manufacturer": "HungaroMet",
            "model": "Órás időjárás szenzorok",
            "entry_type": "service",
        }

    @property
    def unique_id(self):
        return self._unique_id

    async def async_added_to_hass(self):
        self._added = True
        _LOGGER.debug(
            f"Entity {self._name} added to hass with unique_id {self._unique_id}"
        )

    async def async_will_remove_from_hass(self):
        self._added = False
        _LOGGER.debug(
            f"Entity {self._name} removed from hass; skipping scheduled updates"
        )

    async def async_update_data(self):
        if not self._added:
            return

        # Use coordinator data if available, otherwise fetch directly
        if self.coordinator and self.coordinator.data:
            data = self.coordinator.data.get("data", {})
        else:
            data, _ = await self.hass.async_add_executor_job(
                process_hourly_data, self.hass, DEFAULT_DISTANCE_KM
            )

        # Try both the raw key and the 'average_' + key
        value = data.get(self._key)
        if value is None:
            value = data.get(f"average_{self._key}")
        if value is not None:
            self._state = value
        self.async_write_ha_state()

    async def async_update(self):
        await self.async_update_data()

    def update(self):
        pass
