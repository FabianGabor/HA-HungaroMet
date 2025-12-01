"""Tests for image.py platform setup"""

import pytest
from unittest.mock import MagicMock

from custom_components.hungaromet.image import (
    async_setup_platform,
    async_setup_entry,
    _setup_image_entities,
)


@pytest.mark.asyncio
async def test_async_setup_platform():
    """Test deprecated platform setup."""
    hass = MagicMock()
    config = {}
    async_add_entities = MagicMock()

    await async_setup_platform(hass, config, async_add_entities, discovery_info=None)

    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    assert len(args[0]) == 1  # One entity
    assert args[1] is True  # update_before_add


@pytest.mark.asyncio
async def test_async_setup_entry():
    """Test config entry setup."""
    hass = MagicMock()
    entry = MagicMock()
    async_add_entities = MagicMock()

    await async_setup_entry(hass, entry, async_add_entities)

    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    assert len(args[0]) == 1
    assert args[1] is True


def test_setup_image_entities():
    """Test _setup_image_entities helper."""
    hass = MagicMock()
    async_add_entities = MagicMock()

    _setup_image_entities(hass, async_add_entities)

    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    entities = args[0]
    assert len(entities) == 1
    assert entities[0].name == "HungaroMet Radar"
