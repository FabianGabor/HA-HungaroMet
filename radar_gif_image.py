import logging
import os
from datetime import datetime

from homeassistant.components.image import ImageEntity
from homeassistant.helpers.event import async_track_time_change

from .radar_gif_creator import update_radar_gif

_LOGGER = logging.getLogger(__name__)


class HungarometRadarImage(ImageEntity):
    """ImageEntity for the HungaroMet radar GIF."""

    def __init__(self, hass, name="HungaroMet Radar"):
        super().__init__(hass)
        self.hass = hass
        self._name = name
        self._device_id = "hungaromet_radar_gif"
        normalized_name = self._name.lower().replace(" ", "_")
        self._unique_id = f"{self._device_id}_{normalized_name}"
        self._added = False
        self._gif_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "www", "radar_animation.gif"
        )
        self._update_counter = 0
        self._unsub_update = None
        # Set last_updated to file mtime if exists, else None
        if os.path.exists(self._gif_path):
            mtime = os.path.getmtime(self._gif_path)
            self._last_updated = datetime.fromtimestamp(mtime).isoformat()
        else:
            self._last_updated = None
            _LOGGER.warning(
                "Radar GIF file not found at %s. The image entity will be unavailable "
                "until the file is created.",
                self._gif_path,
            )

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
        _LOGGER.debug(
            "Image entity %s added to hass with unique_id %s",
            self._name,
            self._unique_id,
        )
        if self._unsub_update is None:
            self._unsub_update = async_track_time_change(
                self.hass,
                self._handle_scheduled_update,
                minute=[1, 6, 11, 16, 21, 26, 31, 36, 41, 46, 51, 56],
                second=30,
            )

    async def async_will_remove_from_hass(self):
        self._added = False
        if self._unsub_update:
            self._unsub_update()
            self._unsub_update = None

    async def _handle_scheduled_update(self, now):
        if not self._added:
            return
        _LOGGER.debug("HungaroMetRadarImage: scheduled update triggered")
        await self.async_update_data()

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
            _LOGGER.warning(
                "Radar GIF file not found at %s. Returning None.",
                self._gif_path,
            )
            return None
        try:
            with open(self._gif_path, "rb") as f:
                return f.read()
        except OSError as err:
            _LOGGER.error("Failed to read radar GIF: %s", err)
            return None

    def image(self):
        """Return the most recent radar image bytes synchronously."""
        if not os.path.exists(self._gif_path):
            return None
        try:
            with open(self._gif_path, "rb") as gif_file:
                return gif_file.read()
        except OSError as err:
            _LOGGER.error("Failed to read radar GIF synchronously: %s", err)
            return None

    @property
    def extra_state_attributes(self):
        return {
            "last_updated": self._last_updated,
            "update_counter": self._update_counter,
        }
