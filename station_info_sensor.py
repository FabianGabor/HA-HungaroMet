import logging

from homeassistant.components.sensor import SensorEntity

_LOGGER = logging.getLogger(__name__)


class HungarometStationInfoSensor(SensorEntity):
    def __init__(self, hass, name, station_info, sensor_type="daily"):
        self.hass = hass
        self._name = name
        self._station_info = station_info
        self._device_id = "hungaromet_weather"
        self._sensor_type = sensor_type
        self._unique_id = f"{self._device_id}_station_info_{sensor_type}"
        self._added = False

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return len(self._station_info) if self._station_info is not None else 0

    @property
    def extra_state_attributes(self):
        return {"stations": self._station_info}

    @property
    def device_info(self):
        return {
            "identifiers": {(self._device_id,)},
            "name": "HungaroMet napi",
            "manufacturer": "HungaroMet",
            "model": "Napi időjárás szenzorok",
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
        from .sensor import process_daily_data

        data, stations = await self.hass.async_add_executor_job(
            process_daily_data, self.hass
        )
        self._station_info = stations
        self.async_write_ha_state()

    async def async_update(self):
        await self.async_update_data()

    def update(self):
        pass
