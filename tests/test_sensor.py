"""Tests for Eau du Grand Lyon sensor parsing helpers and calculations."""

from datetime import date

from custom_components.eau_du_grand_lyon.sensor import (
    _extract_daily_points,
    _extract_monthly_points,
    _get_daily_units,
    _month_key,
    _point_to_date,
)


def test_extract_monthly_points():
    """Test extracting and sorting monthly points."""
    raw = {
        "postes": [
            {
                "data": [
                    {"annee": 2024, "mois": 2, "volume": 12.5},
                    {"annee": 2024, "mois": 0, "volume": 10.0},
                    {"annee": 2024, "mois": 1, "volume": 11.2},
                ]
            }
        ]
    }
    points = _extract_monthly_points(raw)
    assert len(points) == 3
    assert points[0]["mois"] == 0
    assert points[1]["mois"] == 1
    assert points[2]["mois"] == 2


def test_extract_daily_points():
    """Test extracting and sorting daily points."""
    raw = {
        "postes": [
            {
                "data": [
                    {"annee": 2024, "mois": 10, "jour": 5, "volume": 150},
                    {"annee": 2024, "mois": 10, "jour": 3, "volume": 120},
                    {"annee": 2024, "mois": 10, "jour": 4, "volume": 130},
                ]
            }
        ]
    }
    points = _extract_daily_points(raw)
    assert len(points) == 3
    assert points[0]["jour"] == 3
    assert points[1]["jour"] == 4
    assert points[2]["jour"] == 5


def test_point_to_date():
    """Test converting API point (mois 0-indexed) to python date."""
    point = {"annee": 2024, "mois": 0, "jour": 15}
    assert _point_to_date(point) == date(2024, 1, 15)

    point_dec = {"annee": 2024, "mois": 11, "jour": 31}
    assert _point_to_date(point_dec) == date(2024, 12, 31)

    # Invalid
    assert _point_to_date({"annee": 2024, "mois": 12, "jour": 1}) is None
    assert _point_to_date({}) is None


def test_get_daily_units():
    """Test extracting units from response."""
    raw = {
        "unites": {
            "consommation": "LITRE",
            "index": "M3",
        }
    }
    conso_u, index_u = _get_daily_units(raw)
    assert conso_u == "LITRE"
    assert index_u == "M3"

    assert _get_daily_units(None) == (None, None)


def test_month_key():
    """Test generating formatted month key."""
    point = {"annee": 2024, "mois": 4}  # Mai
    assert _month_key(point) == "2024-05"
    assert _month_key({}) is None

