"""Tests for Eau du Grand Lyon binary sensors."""

from unittest.mock import MagicMock

from custom_components.eau_du_grand_lyon.binary_sensor import (
    EGLWaterLeakBinarySensor,
)


def test_leak_binary_sensor_no_leak():
    """Test leak sensor is off when volumeEstimeFuite is 0 or absent."""
    coordinator = MagicMock()
    coordinator.entry.entry_id = "test_entry"
    coordinator.data = {
        "raw_journalier": {
            "postes": [
                {
                    "data": [
                        {
                            "annee": 2026,
                            "mois": 10,
                            "jour": 5,
                            "volumeEstimeFuite": 0,
                            "debitMin": 0.0,
                        }
                    ]
                }
            ]
        }
    }
    sensor = EGLWaterLeakBinarySensor(coordinator)
    assert sensor.is_on is False
    assert sensor.extra_state_attributes["volume_estime_fuite"] == 0


def test_leak_binary_sensor_leak_detected():
    """Test leak sensor turns on when volumeEstimeFuite > 0."""
    coordinator = MagicMock()
    coordinator.entry.entry_id = "test_entry"
    coordinator.data = {
        "raw_journalier": {
            "postes": [
                {
                    "data": [
                        {
                            "annee": 2026,
                            "mois": 10,
                            "jour": 6,
                            "volumeEstimeFuite": 42.5,
                            "debitMin": 15.0,
                        }
                    ]
                }
            ]
        }
    }
    sensor = EGLWaterLeakBinarySensor(coordinator)
    assert sensor.is_on is True
    assert sensor.extra_state_attributes["volume_estime_fuite"] == 42.5
    assert sensor.extra_state_attributes["debit_min"] == 15.0


def test_leak_binary_sensor_empty_data():
    """Test leak sensor when data is empty."""
    coordinator = MagicMock()
    coordinator.entry.entry_id = "test_entry"
    coordinator.data = {}
    sensor = EGLWaterLeakBinarySensor(coordinator)
    assert sensor.is_on is None

