"""Config flow for Eau du Grand Lyon."""
from __future__ import annotations

import base64
import hashlib
import logging
import os
from urllib.parse import parse_qs, urlparse

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    AUTH_AUTHENTIFICATION,
    AUTH_AUTHORIZE,
    AUTH_TOKEN,
    BASE_URL,
    CONF_PASSWORD,
    CONF_USERNAME,
    DEFAULT_CLIENT_ID,
    DOMAIN,
    REDIRECT_URI,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def _async_validate_input(hass, user_input: dict[str, str]) -> str | None:
    """Valide les identifiants en effectuant un test de connexion PKCE.
    Retourne None si succès, ou la clé d'erreur correspondante.
    """
    session = async_get_clientsession(hass)
    client_id = DEFAULT_CLIENT_ID

    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip("=")

    try:
        r = await session.post(
            f"{BASE_URL}{AUTH_AUTHENTIFICATION}",
            data={
                "username": user_input[CONF_USERNAME],
                "password": user_input[CONF_PASSWORD],
                "client_id": client_id,
            },
            timeout=aiohttp.ClientTimeout(total=15),
        )
        if r.status != 200:
            body = await r.text()
            if r.status == 403 or "nombre maximum de connexion" in body:
                return "rate_limit"
            return "invalid_auth"

        r = await session.get(
            f"{BASE_URL}{AUTH_AUTHORIZE}",
            params={
                "redirect_uri": REDIRECT_URI,
                "response_type": "code",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "client_id": client_id,
            },
            allow_redirects=False,
            timeout=aiohttp.ClientTimeout(total=15),
        )
        if r.status not in (301, 302, 303, 307, 308) or "Location" not in r.headers:
            return "cannot_connect"

        loc = r.headers["Location"]
        code = (parse_qs(urlparse(loc).query).get("code") or [None])[0]
        if not code:
            return "cannot_connect"

        r = await session.post(
            f"{BASE_URL}{AUTH_TOKEN}",
            data={
                "client_id": client_id,
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            },
            timeout=aiohttp.ClientTimeout(total=15),
        )
        if r.status != 200:
            return "cannot_connect"

        return None
    except aiohttp.ClientError:
        return "cannot_connect"
    except Exception as err:
        _LOGGER.exception("Erreur inattendue lors de la validation : %s", err)
        return "unknown"


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Eau du Grand Lyon."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME].strip().lower()
            await self.async_set_unique_id(username)
            self._abort_if_unique_id_configured()

            err = await _async_validate_input(self.hass, user_input)
            if err is None:
                return self.async_create_entry(
                    title=f"Eau du Grand Lyon ({username})",
                    data={
                        CONF_USERNAME: user_input[CONF_USERNAME].strip(),
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )
            errors["base"] = err

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
