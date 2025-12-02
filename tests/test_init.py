"""Tests for __init__.py"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hungaromet import (
    async_setup,
    async_setup_entry,
)


@pytest.mark.asyncio
async def test_async_setup():
    """Test async_setup returns True."""
    hass = MagicMock()
    config = {}

    result = await async_setup(hass, config)

    assert result is True


@pytest.mark.asyncio
async def test_async_setup_entry():
    """Test async_setup_entry forwards to platforms."""
    hass = MagicMock()
    entry = MagicMock()

    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

    result = await async_setup_entry(hass, entry)

    assert result is True
    hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
        entry, ["sensor", "image"]
    )
