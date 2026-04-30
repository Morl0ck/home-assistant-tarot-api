"""Config flow for Tarot API."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries

from .const import (
    CONF_BASE_URL,
    CONF_PROVIDER,
    DEFAULT_BASE_URL,
    DOMAIN,
    PROVIDER_EKELEN,
    PROVIDER_KRATES,
)

# vol.In avoids SelectSelectorMode / UI issues on older Home Assistant builds.
_PROVIDER_SELECTOR = vol.In(
    {
        PROVIDER_EKELEN: "tarotapi.dev (Waite text; images from public scans)",
        PROVIDER_KRATES: "Tarot Card API / krates98 (your server, bundled images)",
    }
)


class TarotAPIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tarot API."""

    VERSION = 2

    async def async_step_user(self, user_input: dict | None = None):
        """Prompt for provider and base URL."""
        errors: dict[str, str] = {}
        if user_input is not None:
            provider = user_input[CONF_PROVIDER]
            base_url = (user_input.get(CONF_BASE_URL) or "").strip()

            if provider == PROVIDER_EKELEN:
                base_url = base_url or DEFAULT_BASE_URL

            if not base_url.startswith(("http://", "https://")):
                errors[CONF_BASE_URL] = "invalid_url"
            elif (
                provider == PROVIDER_KRATES
                and base_url.rstrip("/") == DEFAULT_BASE_URL.rstrip("/")
            ):
                errors[CONF_BASE_URL] = "krates_need_own_url"
            else:
                await self.async_set_unique_id(f"{provider}_{base_url}")
                self._abort_if_unique_id_configured()
                title = (
                    "Tarot Card API (with images)"
                    if provider == PROVIDER_KRATES
                    else "Tarot API (tarotapi.dev)"
                )
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_PROVIDER: provider,
                        CONF_BASE_URL: base_url.rstrip("/"),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PROVIDER, default=PROVIDER_EKELEN): _PROVIDER_SELECTOR,
                    vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
                }
            ),
            errors=errors,
        )
