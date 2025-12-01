"""Tests for __init__.py"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import sys
from pathlib import Path

# Add parent directory to path to import __init__
sys.path.insert(0, str(Path(__file__).parent.parent))
import __init__ as hungaromet_init


@pytest.mark.asyncio
async def test_async_setup():
    """Test async_setup returns True."""
    hass = MagicMock()
    config = {}

    result = await hungaromet_init.async_setup(hass, config)

    assert result is True


@pytest.mark.asyncio
async def test_async_setup_entry():
    """Test async_setup_entry forwards to platforms."""
    hass = MagicMock()
    entry = MagicMock()

    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

    result = await hungaromet_init.async_setup_entry(hass, entry)

    assert result is True
    hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
        entry, ["sensor", "image"]
    )
