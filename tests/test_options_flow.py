"""Tests for options_flow.py"""

import pytest
from unittest.mock import MagicMock
import voluptuous as vol

from custom_components.hungaromet.options_flow import HungaroMetOptionsFlowHandler
from custom_components.hungaromet.sensor import CONF_DISTANCE_KM


@pytest.mark.asyncio
async def test_options_flow_init():
    """Test options flow initialization."""
    config_entry = MagicMock()
    config_entry.options = {}

    flow = HungaroMetOptionsFlowHandler(config_entry)

    assert flow.config_entry == config_entry


@pytest.mark.asyncio
async def test_options_flow_with_user_input():
    """Test options flow with user input creates entry."""
    config_entry = MagicMock()
    config_entry.options = {}

    flow = HungaroMetOptionsFlowHandler(config_entry)

    user_input = {CONF_DISTANCE_KM: 30.0}
    result = await flow.async_step_init(user_input=user_input)

    assert result["type"] == "create_entry"
    assert result["data"] == user_input


@pytest.mark.asyncio
async def test_options_flow_without_user_input():
    """Test options flow without user input shows form."""
    config_entry = MagicMock()
    config_entry.options = {CONF_DISTANCE_KM: 20.0}

    flow = HungaroMetOptionsFlowHandler(config_entry)

    result = await flow.async_step_init(user_input=None)

    assert result["type"] == "form"
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_flow_uses_default_when_no_options():
    """Test options flow uses default when no options are set."""
    config_entry = MagicMock()
    config_entry.options = {}

    flow = HungaroMetOptionsFlowHandler(config_entry)

    result = await flow.async_step_init(user_input=None)

    assert result["type"] == "form"
    # The schema will contain the default
    schema = result["data_schema"]
    assert isinstance(schema, vol.Schema)
