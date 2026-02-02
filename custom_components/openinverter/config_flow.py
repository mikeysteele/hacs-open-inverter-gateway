"""Config flow for My Open Inverter Gateway integration."""

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_ENDPOINT_PATH,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Schema for the user configuration step
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_IP_ADDRESS): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.positive_int,
    }
)


async def validate_input(hass, data: dict) -> dict[str, Any]:
    """
    Validate the user input allows us to connect and fetch data.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    session = async_get_clientsession(hass)
    ip_address = data[CONF_IP_ADDRESS]
    # Construct the full URL to the JSON endpoint
    url = f"http://{ip_address}{API_ENDPOINT_PATH}"

    try:
        # Attempt to connect and fetch data from the endpoint
        async with asyncio.timeout(10):  # 10-second timeout for the request
            async with session.get(url) as response:
                if response.status == 200:
                    # Optionally, try to parse JSON to ensure it's valid
                    try:
                        await response.json()
                        # Connection successful and JSON is valid
                        # Return info used to create the config entry title
                        return {"title": f"Open Inverter ({ip_address})"}
                    except Exception as json_err:
                        _LOGGER.error(f"Failed to parse JSON from {url}: {json_err}")
                        raise ValueError("invalid_json") from json_err
                else:
                    _LOGGER.error(f"Connection failed to {url}: Status {response.status}")
                    raise ValueError("cannot_connect")

    except (TimeoutError, aiohttp.ClientConnectorError) as conn_err:
        _LOGGER.error(f"Connection failed to {url}: {conn_err}")
        raise ValueError("cannot_connect") from conn_err
    except Exception as err:
        _LOGGER.error(f"Unexpected error validating connection to {url}: {err}")
        raise ValueError("unknown") from err


class OpenInverterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Open Inverter Gateway."""

    VERSION = 1
    # Defines that this integration polls locally
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def _async_validate_or_errors(
        self, user_input: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, dict[str, str]]:
        """Validate input and return info or errors."""
        errors: dict[str, str] = {}
        try:
            info = await validate_input(self.hass, user_input)
            return info, errors
        except ValueError as err_val:
            reason = str(err_val)
            _LOGGER.warning(f"Validation failed for IP {user_input.get(CONF_IP_ADDRESS)}: {reason}")
            if reason == "cannot_connect":
                errors["base"] = "cannot_connect"
            elif reason == "invalid_json":
                errors["base"] = "invalid_json"
            else:
                errors["base"] = "unknown_validation_error"
        except Exception as exc:
            _LOGGER.exception(f"Unexpected exception during validation for IP {user_input.get(CONF_IP_ADDRESS)}: {exc}")
            errors["base"] = "unknown"

        return None, errors

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            info, errors = await self._async_validate_or_errors(user_input)

            if not errors and info:
                # Validation successful, proceed to create entry
                try:
                    await self.async_set_unique_id(user_input[CONF_IP_ADDRESS])
                    self._abort_if_unique_id_configured()

                    _LOGGER.info(f"Configuration successful for {user_input[CONF_IP_ADDRESS]}")
                    return self.async_create_entry(title=info["title"], data=user_input)

                except config_entries.AlreadyConfigured:  # type: ignore[attr-defined]
                    _LOGGER.info(f"Configuration aborted for {user_input.get(CONF_IP_ADDRESS)}: already configured.")
                    return self.async_abort(reason="already_configured")
                except Exception as exc:
                    _LOGGER.exception(
                        f"Unexpected exception during creation for IP {user_input.get(CONF_IP_ADDRESS)}: {exc}"
                    )
                    errors["base"] = "unknown"

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_IP_ADDRESS,
                    default=user_input.get(CONF_IP_ADDRESS) if user_input else "",
                ): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                    if user_input
                    else DEFAULT_SCAN_INTERVAL,
                ): cv.positive_int,
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle reconfiguration."""
        errors: dict[str, str] = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        if entry is None:
            return self.async_abort(reason="unknown_entry")

        if user_input is not None:
            _, errors = await self._async_validate_or_errors(user_input)

            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    data={**entry.data, **user_input},
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_IP_ADDRESS, default=entry.data.get(CONF_IP_ADDRESS)): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): cv.positive_int,
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for the component."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Here you could add validation for the options if needed
            # Update the config entry's options with the user input
            return self.async_create_entry(title="", data=user_input)

        # Define the schema for the options form, pre-filling with current values
        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self._config_entry.options.get(
                        CONF_SCAN_INTERVAL,  # Get current option value
                        self._config_entry.data.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),  # Fallback to initial config value
                    ),
                ): cv.positive_int,
                # Add other configurable options here in the future if needed
            }
        )

        # Show the options form to the user
        return self.async_show_form(step_id="init", data_schema=options_schema, errors=errors)
