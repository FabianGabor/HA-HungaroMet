import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity

from .weather_data import process_ten_minutes_data

_LOGGER = logging.getLogger(__name__)

class HungarometWeatherTenMinutesSensor(SensorEntity):
    def __init__(self, hass, name, value, unit, key):
        self.hass = hass
        self._name = name
        self._state = value
        self._unit = unit
        self._key = key
        self._device_id = "hungaromet_weather_ten_minutes"
        self._unique_id = f"{self._device_id}_{self._name.lower().replace(' ', '_')}"
        self._added = False
    @property
    def name(self):
        return self._name
    @property
    def state(self):
        if self._key == "time" and self._state:
            try:
                import pytz
                dt_utc = datetime.fromisoformat(self._state)
                cet = pytz.timezone('Europe/Budapest')
                local_dt = dt_utc.astimezone(cet)
                return local_dt.strftime('%Y-%m-%d %H:%M')
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
            "name": "HungaroMet 10 perces",
            "manufacturer": "HungaroMet",
            "model": "10 perces időjárás szenzorok",
            "entry_type": "service",
        }
    @property
    def unique_id(self):
        return self._unique_id
    async def async_added_to_hass(self):
        self._added = True
        _LOGGER.debug(f"Entity {self._name} added to hass with unique_id {self._unique_id}")
    async def async_update_data(self):
        if not self._added:
            return
        data, _ = await self.hass.async_add_executor_job(process_ten_minutes_data, self.hass)
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
