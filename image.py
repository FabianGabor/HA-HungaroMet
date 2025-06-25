"""
Home Assistant image platform for HungaroMet radar GIF.
"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change

from .radar_gif_image import HungarometRadarImage

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
):
    # Deprecated platform setup, use config entry setup
    _setup_image_entities(hass, async_add_entities)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """
    Set up the HungaroMet radar GIF image entity from a config entry.
    """
    _setup_image_entities(hass, async_add_entities)


def _schedule_image_update(hass, entity):
    async def update_image_entity(now):
        _LOGGER.debug("HungaroMetRadarImage: scheduled update triggered from image.py")
        await entity.async_update_data()

    # Schedule update at every 1, 6, 11, ... 56 minute, second 30
    async_track_time_change(
        hass,
        update_image_entity,
        minute=[1, 6, 11, 16, 21, 26, 31, 36, 41, 46, 51, 56],
        second=30,
    )


def _setup_image_entities(hass, async_add_entities):
    entity = HungarometRadarImage(hass)
    async_add_entities([entity], True)
    _schedule_image_update(hass, entity)
