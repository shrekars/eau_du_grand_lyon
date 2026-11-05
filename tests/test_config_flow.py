"""Test the Eau du Grand Lyon config flow."""
from unittest.mock import patch
from homeassistant import config_entries, data_entry_flow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eau_du_grand_lyon.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
)

MOCK_USER_INPUT = {
    CONF_USERNAME: "test_user@example.com",
    CONF_PASSWORD: "secret_password",
}


async def test_form_user_success(hass):
    """Test full successful user flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.eau_du_grand_lyon.config_flow._async_validate_input",
        return_value=None,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_USER_INPUT,
        )
        await hass.async_block_till_done()

    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Eau du Grand Lyon (test_user@example.com)"
    assert result2["data"][CONF_USERNAME] == "test_user@example.com"
    assert result2["data"][CONF_PASSWORD] == "secret_password"
    assert result2["result"].unique_id == "test_user@example.com"


async def test_form_user_invalid_auth(hass):
    """Test user flow with invalid credentials."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.eau_du_grand_lyon.config_flow._async_validate_input",
        return_value="invalid_auth",
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_USER_INPUT,
        )
        await hass.async_block_till_done()

    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_user_cannot_connect(hass):
    """Test user flow when connection fails."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.eau_du_grand_lyon.config_flow._async_validate_input",
        return_value="cannot_connect",
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_USER_INPUT,
        )
        await hass.async_block_till_done()

    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_already_configured(hass):
    """Test duplicate account is prevented."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="test_user@example.com",
        data=MOCK_USER_INPUT,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        MOCK_USER_INPUT,
    )

    assert result2["type"] == data_entry_flow.FlowResultType.ABORT
    assert result2["reason"] == "already_configured"

