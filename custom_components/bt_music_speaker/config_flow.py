"""Config flow for BT Music Speaker integration."""
from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol

from .const import DOMAIN, CONF_HOST, CONF_API_KEY, DEFAULT_API_KEY, DEFAULT_NAME


class BtMusicSpeakerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BT Music Speaker."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            api_key = user_input.get(CONF_API_KEY, DEFAULT_API_KEY)

            # Test connection
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"http://{host}/rest/status",
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as resp:
                        if resp.status == 200:
                            return self.async_create_entry(
                                title=DEFAULT_NAME,
                                data={
                                    CONF_HOST: host,
                                    CONF_API_KEY: api_key,
                                },
                            )
                        elif resp.status == 401:
                            errors[CONF_API_KEY] = "invalid_auth"
                        else:
                            errors["base"] = "cannot_connect"
            except (aiohttp.ClientError, TimeoutError, OSError):
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default="192.168.178.57:8766"): str,
                    vol.Optional(CONF_API_KEY, default=DEFAULT_API_KEY): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow."""
        return BtMusicSpeakerOptionsFlow(config_entry)


class BtMusicSpeakerOptionsFlow(config_entries.OptionsFlow):
    """Options flow for BT Music Speaker."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        default=self.config_entry.data.get(CONF_HOST),
                    ): str,
                    vol.Optional(
                        CONF_API_KEY,
                        default=self.config_entry.data.get(CONF_API_KEY, DEFAULT_API_KEY),
                    ): str,
                }
            ),
        )