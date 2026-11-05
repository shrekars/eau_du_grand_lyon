"""Pytest fixtures for Eau du Grand Lyon tests."""

from unittest.mock import patch

import pytest

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for testing in Home Assistant."""
    yield


@pytest.fixture(autouse=True)
def mock_recorder_dependency():
    """Mock recorder component setup to avoid spinning up database in unit tests."""
    with patch("homeassistant.setup.async_setup_component", return_value=True):
        yield
