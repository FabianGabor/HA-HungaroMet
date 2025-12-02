"""Config flow for Hungaromet Weather."""

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_NAME

from .const import CONF_DISTANCE_KM, DEFAULT_DISTANCE_KM, DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


class HungarometConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for Hungaromet Weather."""

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={
                    "name": user_input[CONF_NAME],
                    CONF_DISTANCE_KM: user_input.get(
                        CONF_DISTANCE_KM, DEFAULT_DISTANCE_KM
                    ),
                },
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_DISTANCE_KM, default=DEFAULT_DISTANCE_KM): vol.All(
                    vol.Coerce(float), vol.Range(min=1, max=100)
                ),
            }),
            errors=errors,
        )

    def is_matching(self, other_flow: "HungarometConfigFlow") -> bool:
        """Return True if another flow is considered a duplicate."""
        return self.source == other_flow.source
