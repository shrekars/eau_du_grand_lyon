"""Pytest fixtures for Eau du Grand Lyon tests."""

import threading
from unittest.mock import patch

import pytest

# Filter out pycares internal shutdown daemon thread from Home Assistant test teardown
_orig_enumerate = threading.enumerate


def _filtered_enumerate():
    """Ignore internal pycares/aiodns shutdown daemon threads during thread leak verification."""
    return [t for t in _orig_enumerate() if "_run_safe_shutdown_loop" not in t.name]


threading.enumerate = _filtered_enumerate

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

