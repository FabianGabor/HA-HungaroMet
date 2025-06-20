from homeassistant.components.sensor import SensorEntity
import logging
from datetime import datetime
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class HungarometWeatherDailySensor(SensorEntity):
    def __init__(self, hass, name, value, unit, key):
        self.hass = hass
        self._name = name
        self._state = value
        self._unit = unit
        self._key = key
        self._device_id = "hungaromet_weather"
        self._unique_id = f"{self._device_id}_{self._name.lower().replace(' ', '_')}"
        self._added = False
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
        _LOGGER.debug(f"Entity {self._name} added to hass with unique_id {self._unique_id}")
    async def async_update_data(self):
        if not self._added:
            return
        from .sensor import process_daily_data
        data, stations = await self.hass.async_add_executor_job(process_daily_data, self.hass)
        if self._key in data:
            self._state = data[self._key]
        self.async_write_ha_state()
    async def async_update(self):
        await self.async_update_data()
    def update(self):
        pass
