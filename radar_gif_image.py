import logging
import os
from datetime import datetime

from homeassistant.components.image import ImageEntity

from .radar_gif_creator import update_radar_gif

_LOGGER = logging.getLogger(__name__)

class HungarometRadarImage(ImageEntity):
    """ImageEntity for the HungaroMet radar GIF."""
    def __init__(self, hass, name="HungaroMet Radar"):
        super().__init__(hass)
        self.hass = hass
        self._name = name
        self._device_id = "hungaromet_radar_gif"
        self._unique_id = f"{self._device_id}_{self._name.lower().replace(' ', '_')}"
        self._added = False
        self._gif_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'www', 'radar_animation.gif')
        self._update_counter = 0
        # Set last_updated to file mtime if exists, else None
        if os.path.exists(self._gif_path):
            mtime = os.path.getmtime(self._gif_path)
            self._last_updated = datetime.fromtimestamp(mtime).isoformat()
        else:
            self._last_updated = None
            _LOGGER.warning(f"Radar GIF file not found at {self._gif_path}. The image entity will be unavailable until the file is created.")

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def device_info(self):
        return {
            "identifiers": {(self._device_id,)},
            "name": "HungaroMet Radar",
            "manufacturer": "HungaroMet",
            "model": "Radar Image",
            "entry_type": "service",
        }

    @property
    def available(self) -> bool:
        """Return True if the radar GIF file exists."""
        return os.path.exists(self._gif_path)

    @property
    def state(self) -> str:
        """Return the last updated time in ISO format, or 'unknown'."""
        return self._last_updated or "unknown"

    async def async_added_to_hass(self):
        self._added = True
        _LOGGER.debug(f"Image entity {self._name} added to hass with unique_id {self._unique_id}")
        # No timer logic here; scheduling is handled in image.py

    async def async_update_data(self):
        if not self._added:
            return
        _LOGGER.info("HungaroMetRadarImage: async_update_data called")
        await self.hass.async_add_executor_job(update_radar_gif)
        self._last_updated = datetime.now().isoformat()
        self._update_counter += 1
        self.async_write_ha_state()

    async def async_update(self):
        await self.async_update_data()

    async def async_image(self):
        if not os.path.exists(self._gif_path):
            _LOGGER.warning(f"Radar GIF file not found at {self._gif_path}. Returning None.")
            return None
        try:
            with open(self._gif_path, "rb") as f:
                return f.read()
        except Exception as e:
            _LOGGER.error(f"Failed to read radar GIF: {e}")
            return None

    @property
    def extra_state_attributes(self):
        return {"last_updated": self._last_updated, "update_counter": self._update_counter}
