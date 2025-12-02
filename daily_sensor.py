import logging

from homeassistant.components.sensor import SensorEntity

from .weather_data import process_daily_data
from .const import DEFAULT_DISTANCE_KM

_LOGGER = logging.getLogger(__name__)


class HungarometWeatherDailySensor(SensorEntity):
    def __init__(self, hass, name, value, unit, key, coordinator=None):
        self.hass = hass
        self._name = name
        self._state = value
        self._unit = unit
        self._key = key
        self._device_id = "hungaromet_weather"
        self._unique_id = f"{self._device_id}_{self._name.lower().replace(' ', '_')}"
        self._added = False
        self.coordinator = coordinator

    @property
    def name(self):
        return self._name

    @property
    def state(self):
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
            "name": "HungaroMet",
            "manufacturer": "HungaroMet",
            "model": "Weather Sensors",
            "entry_type": "service",
        }

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def entity_registry_enabled_default(self):
        if self._key in ["tsn24", "et5", "et10", "et20", "et50", "et100"]:
            return False
        return True

    async def async_added_to_hass(self):
        self._added = True
        _LOGGER.debug(
            "Entity %s added to hass with unique_id %s",
            self._name,
            self._unique_id,
        )

    async def async_will_remove_from_hass(self):
        self._added = False
        _LOGGER.debug(
            "Entity %s removed from hass; skipping scheduled updates",
            self._name,
        )

    async def async_update_data(self):
        if not self._added:
            return

        # Use coordinator data if available, otherwise fetch directly
        if self.coordinator and self.coordinator.data:
            data = self.coordinator.data.get("data", {})
        else:
            data, _ = await self.hass.async_add_executor_job(
                process_daily_data, self.hass, DEFAULT_DISTANCE_KM
            )

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
