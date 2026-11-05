"""Test setup and unload for Eau du Grand Lyon integration."""

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eau_du_grand_lyon.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
)


async def test_setup_and_unload_entry(hass):
    """Test successful setup and unload of config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Eau du Grand Lyon (test@example.com)",
        unique_id="test@example.com",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "secret_password",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.eau_du_grand_lyon.coordinator.EGLDataUpdateCoordinator.async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]

    # Test unload
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.entry_id not in hass.data.get(DOMAIN, {})

