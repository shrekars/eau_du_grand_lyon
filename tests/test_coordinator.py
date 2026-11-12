"""Tests for Eau du Grand Lyon coordinator and statistics backfill."""

from datetime import date, datetime, time, timezone
from unittest.mock import MagicMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eau_du_grand_lyon.const import DOMAIN
from custom_components.eau_du_grand_lyon.coordinator import (
    TZ_PARIS,
    EGLDataUpdateCoordinator,
)

RAW_DAILY_FIXTURE = {
    "postes": [
        {
            "data": [
                {
                    "annee": 2026,
                    "mois": 10,  # Novembre (0-indexed)
                    "jour": 7,
                    "consommation": 100.0,
                    "index": 639000.0,
                },
                {
                    "annee": 2026,
                    "mois": 10,
                    "jour": 8,
                    "consommation": 200.0,
                    "index": 639200.0,
                },
                {
                    "annee": 2026,
                    "mois": 10,
                    "jour": 9,
                    "consommation": 271.0,
                    "index": 639471.0,
                },
            ]
        }
    ]
}


async def test_insert_statistics_dates_alignment(hass):
    """Verify that every daily consumption point is attached to day D at 23:00 (Europe/Paris), never D+1."""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")

    with patch(
        "custom_components.eau_du_grand_lyon.coordinator.async_get_clientsession",
        return_value=MagicMock(),
    ):
        coordinator = EGLDataUpdateCoordinator(hass, entry)

    captured_stats = []

    def mock_add_stats(_hass, _meta, stats):
        captured_stats.extend(stats)

    with patch(
        "custom_components.eau_du_grand_lyon.coordinator.async_add_external_statistics",
        side_effect=mock_add_stats,
    ):
        coordinator._insert_statistics(RAW_DAILY_FIXTURE)

    assert len(captured_stats) == 4  # 1 initial baseline + 3 daily consumption points

    # Baseline at start of first day (7 Nov 00:00 Paris)
    baseline = captured_stats[0]
    expected_baseline_dt = datetime.combine(
        date(2026, 11, 7), time(0, 0), tzinfo=TZ_PARIS
    ).astimezone(timezone.utc)
    assert baseline.start == expected_baseline_dt
    assert baseline.sum == 638900.0

    # Point 1: 7 Nov consumption (100 L) must be at 7 Nov 23:00 Paris
    p1 = captured_stats[1]
    expected_p1_dt = datetime.combine(
        date(2026, 11, 7), time(23, 0), tzinfo=TZ_PARIS
    ).astimezone(timezone.utc)
    assert p1.start == expected_p1_dt
    assert p1.sum == 639000.0
    # Crucial check: Local calendar date must be 7 Nov, NOT 8 Nov!
    assert p1.start.astimezone(TZ_PARIS).date() == date(2026, 11, 7)

    # Point 2: 8 Nov consumption (200 L) must be at 8 Nov 23:00 Paris
    p2 = captured_stats[2]
    expected_p2_dt = datetime.combine(
        date(2026, 11, 8), time(23, 0), tzinfo=TZ_PARIS
    ).astimezone(timezone.utc)
    assert p2.start == expected_p2_dt
    assert p2.sum == 639200.0
    assert p2.start.astimezone(TZ_PARIS).date() == date(2026, 11, 8)

    # Point 3: 9 Nov consumption (271 L) must be at 9 Nov 23:00 Paris
    p3 = captured_stats[3]
    expected_p3_dt = datetime.combine(
        date(2026, 11, 9), time(23, 0), tzinfo=TZ_PARIS
    ).astimezone(timezone.utc)
    assert p3.start == expected_p3_dt
    assert p3.sum == 639471.0
    # Crucial check: 271 L is attached to 9 Nov, NEVER to 10 Nov!
    assert p3.start.astimezone(TZ_PARIS).date() == date(2026, 11, 9)
    assert p3.start.astimezone(TZ_PARIS).date() != date(2026, 11, 10)


async def test_insert_statistics_with_gap(hass):
    """Verify gap handling in telemetry days."""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")

    raw_with_gap = {
        "postes": [
            {
                "data": [
                    {
                        "annee": 2026,
                        "mois": 10,
                        "jour": 5,
                        "consommation": 150.0,
                        "index": 1000.0,
                    },
                    # Days 6 and 7 missing
                    {
                        "annee": 2026,
                        "mois": 10,
                        "jour": 8,
                        "consommation": 300.0,
                        "index": 1300.0,
                    },
                ]
            }
        ]
    }

    with patch(
        "custom_components.eau_du_grand_lyon.coordinator.async_get_clientsession",
        return_value=MagicMock(),
    ):
        coordinator = EGLDataUpdateCoordinator(hass, entry)

    captured_stats = []

    with patch(
        "custom_components.eau_du_grand_lyon.coordinator.async_add_external_statistics",
        side_effect=lambda _h, _m, stats: captured_stats.extend(stats),
    ):
        coordinator._insert_statistics(raw_with_gap)

    # Expected points:
    # 0: 5 Nov 00:00 (baseline: 850)
    # 1: 5 Nov 23:00 (day 5: 1000)
    # 2: 8 Nov 00:00 (gap anchor: 1000)
    # 3: 8 Nov 23:00 (day 8: 1300)
    assert len(captured_stats) == 4
    assert captured_stats[0].start.astimezone(TZ_PARIS).date() == date(2026, 11, 5)
    assert captured_stats[1].start.astimezone(TZ_PARIS).date() == date(2026, 11, 5)
    assert captured_stats[2].start.astimezone(TZ_PARIS).date() == date(2026, 11, 8)
    assert captured_stats[3].start.astimezone(TZ_PARIS).date() == date(2026, 11, 8)
