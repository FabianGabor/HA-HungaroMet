import voluptuous as vol
from homeassistant import config_entries

from .sensor import CONF_DISTANCE_KM, DEFAULT_DISTANCE_KM


class HungaroMetOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_DISTANCE_KM, default=options.get(CONF_DISTANCE_KM, DEFAULT_DISTANCE_KM)): vol.All(vol.Coerce(float), vol.Range(min=1, max=100)),
            })
        )
