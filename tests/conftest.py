"""Pytest fixtures for Eau du Grand Lyon tests."""

import pytest

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for testing in Home Assistant."""
    yield


@pytest.fixture(autouse=True)
def auto_recorder(recorder_mock):
    """Enable recorder mock for all tests."""
    yield recorder_mock
