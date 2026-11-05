"""Sensors for Eau du Grand Lyon (incl. Energy backfill)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfVolume
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
TZ_PARIS = ZoneInfo("Europe/Paris")

MONTHS_TO_EXPOSE = 12
MAX_STORED_MONTHS = 60

MONTH_NAMES_FR = [
    "Janvier",
    "Février",
    "Mars",
    "Avril",
    "Mai",
    "Juin",
    "Juillet",
    "Août",
    "Septembre",
    "Octobre",
    "Novembre",
    "Décembre",
]


# -----------------------
# Parsing helpers
# -----------------------
def _extract_monthly_points(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, dict):
        return []
    postes = raw.get("postes")
    if not isinstance(postes, list) or not postes:
        return []
    poste0 = postes[0]
    if not isinstance(poste0, dict):
        return []
    data = poste0.get("data")
    if not isinstance(data, list):
        return []
    points = [x for x in data if isinstance(x, dict)]
    return sorted(points, key=lambda p: (p.get("annee", -1), p.get("mois", -1)))


def _month_key(point: dict[str, Any]) -> str | None:
    y = point.get("annee")
    m = point.get("mois")  # 0..11
    if isinstance(y, int) and isinstance(m, int):
        return f"{y}-{m + 1:02d}"
    return None


def _extract_daily_points(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, dict):
        return []
    postes = raw.get("postes")
    if not isinstance(postes, list) or not postes:
        return []
    poste0 = postes[0]
    if not isinstance(poste0, dict):
        return []
    data = poste0.get("data")
    if not isinstance(data, list):
        return []
    points = [x for x in data if isinstance(x, dict)]
    return sorted(
        points, key=lambda p: (p.get("annee", -1), p.get("mois", -1), p.get("jour", -1))
    )


def _get_daily_units(raw_j: Any) -> tuple[str | None, str | None]:
    if not isinstance(raw_j, dict):
        return (None, None)
    unites = raw_j.get("unites") or {}
    if not isinstance(unites, dict):
        return (None, None)
    return (unites.get("consommation"), unites.get("index"))


def _point_to_date(p: dict[str, Any]) -> date | None:
    y = p.get("annee")
    m0 = p.get("mois")  # 0..11
    d = p.get("jour")
    if not (isinstance(y, int) and isinstance(m0, int) and isinstance(d, int)):
        return None
    if not (0 <= m0 <= 11):
        return None
    try:
        return date(y, m0 + 1, d)
    except ValueError:
        return None


def _point_to_consumption_day(p: dict[str, Any]) -> date | None:
    """Le point retourné par l'API représente directement le jour de consommation."""
    return _point_to_date(p)


@dataclass(frozen=True)
class DailyIndex:
    # Jour de consommation
    day: date
    index_l: float
    conso_l: float | None


def _daily_index_series(raw_j: Any) -> list[DailyIndex]:
    series: list[DailyIndex] = []
    for p in _extract_daily_points(raw_j):
        day = _point_to_consumption_day(p)
        if day is None:
            continue

        idx = p.get("index")
        if not isinstance(idx, (int, float)):
            continue

        conso = p.get("consommation")
        conso_f = float(conso) if isinstance(conso, (int, float)) else None

        series.append(DailyIndex(day=day, index_l=float(idx), conso_l=conso_f))

    series.sort(key=lambda x: x.day)
    return series


# -----------------------
# Base & Sensors
# -----------------------
class EGLBaseEntity(CoordinatorEntity):
    """Classe de base fournissant les informations d'appareil (device_info)."""

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name="Eau du Grand Lyon",
            manufacturer="Eau du Grand Lyon / Veolia",
            model="Compteur Téléo",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://agence.eaudugrandlyon.com",
        )


class EGLWaterIndexTotalIncreasingSensor(EGLBaseEntity, RestoreSensor):
    """
    Capteur d'index d'eau (Liters) pour affichage / cartes Lovelace.
    Note : La statistique pour le tableau de bord Énergie est gérée sous
    l'identifiant externe `eau_du_grand_lyon:water_consumption`.
    """

    _attr_name = "Eau (index)"
    _attr_unique_id = "egl_water_index_l_v5"
    _attr_device_class = SensorDeviceClass.WATER
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._index: float | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        last_data = await self.async_get_last_sensor_data()
        if last_data and last_data.native_value is not None:
            try:
                self._index = float(last_data.native_value)
            except (TypeError, ValueError):
                self._index = None

        self._sync_state_to_latest()
        self.async_write_ha_state()

    def _sync_state_to_latest(self) -> None:
        raw_j = (self.coordinator.data or {}).get("raw_journalier")
        series = _daily_index_series(raw_j)
        if not series:
            return
        self._index = series[-1].index_l

    @callback
    def _handle_coordinator_update(self) -> None:
        self._sync_state_to_latest()
        super()._handle_coordinator_update()

    @property
    def native_value(self) -> float | None:
        return self._index

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        raw_j = (self.coordinator.data or {}).get("raw_journalier")
        series = _daily_index_series(raw_j)
        cons_u, idx_u = _get_daily_units(raw_j)
        last_day = series[-1].day.isoformat() if series else None

        return {
            "last_data_day": last_day,
            "statistic_id": f"{DOMAIN}:water_consumption",
            "raw_index_unit": idx_u,
            "raw_consumption_unit": cons_u,
        }


class EGLWaterLastDayConsumptionSensor(EGLBaseEntity, SensorEntity):
    """Last available daily consumption (measurement), for UI display."""

    _attr_name = "Eau (dernier jour)"
    _attr_unique_id = "egl_water_last_day_l_v3"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_suggested_display_precision = 0

    @property
    def native_value(self) -> float | None:
        raw_j = (self.coordinator.data or {}).get("raw_journalier")
        points = _extract_daily_points(raw_j)
        if not points:
            return None
        last = points[-1]
        v = last.get("consommation")
        if not isinstance(v, (int, float)):
            return None
        return float(v)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        raw_j = (self.coordinator.data or {}).get("raw_journalier")
        points = _extract_daily_points(raw_j)
        if not points:
            return {}

        last = points[-1]
        cons_u, idx_u = _get_daily_units(raw_j)

        dd = _point_to_consumption_day(last)
        day_str = dd.isoformat() if dd else None

        return {
            "day": day_str,
            "origine": last.get("origine"),
            "debit_min": last.get("debitMin"),
            "volume_estime_fuite": last.get("volumeEstimeFuite"),
            "raw_consumption_unit": cons_u,
            "raw_index_unit": idx_u,
        }


class EGLWaterTotalIncreasingSensor(EGLBaseEntity, RestoreSensor):
    """Cumulative water consumption derived from monthly consumptions (total_increasing)."""

    _attr_name = "Eau (total)"
    _attr_unique_id = "egl_water_total_m3"
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._total: float | None = None
        self._processed_months: list[str] = []
        self._update_from_raw()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        last_data = await self.async_get_last_sensor_data()
        if last_data and last_data.native_value is not None:
            try:
                self._total = float(last_data.native_value)
            except (TypeError, ValueError):
                self._total = None

        last_state = await self.async_get_last_state()
        if last_state:
            pm = last_state.attributes.get("processed_months")
            if isinstance(pm, list):
                self._processed_months = [x for x in pm if isinstance(x, str)][
                    -MAX_STORED_MONTHS:
                ]

        if self._total is None:
            self._total = 0.0

        self._update_from_raw()
        self.async_write_ha_state()

    def _update_from_raw(self) -> None:
        raw = (self.coordinator.data or {}).get("raw")
        points = _extract_monthly_points(raw)

        month_values: list[tuple[str, float]] = []
        for p in points:
            key = _month_key(p)
            v = p.get("consommation")
            if key and isinstance(v, (int, float)):
                month_values.append((key, float(v)))

        if not month_values:
            return

        if not self._processed_months:
            self._total = float(sum(v for _, v in month_values))
            self._processed_months = [k for k, _ in month_values][-MAX_STORED_MONTHS:]
            return

        processed = set(self._processed_months)
        for k, v in month_values:
            if k not in processed:
                self._total = float((self._total or 0.0) + v)
                self._processed_months.append(k)
                processed.add(k)

        self._processed_months = self._processed_months[-MAX_STORED_MONTHS:]

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_from_raw()
        super()._handle_coordinator_update()

    @property
    def native_value(self) -> float | None:
        return self._total

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        raw = (self.coordinator.data or {}).get("raw")
        points = _extract_monthly_points(raw)
        history_12: list[dict[str, Any]] = []
        for p in points[-MONTHS_TO_EXPOSE:]:
            k = _month_key(p)
            v = p.get("consommation")
            if k and isinstance(v, (int, float)):
                parts = k.split("-")
                history_12.append(
                    {
                        "month": k,
                        "label": f"{parts[1]}/{parts[0][-2:]}",
                        "conso_m3": round(float(v), 2),
                    }
                )

        return {
            "processed_months": list(self._processed_months) if self._processed_months else [],
            "last_processed_month": self._processed_months[-1]
            if self._processed_months
            else None,
            "history_12_months": history_12,
        }


class EGLMonthlyConsumptionLastSensor(EGLBaseEntity, SensorEntity):
    _attr_name = "Conso mois dernier"
    _attr_unique_id = "egl_last_month_m3"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS

    @property
    def native_value(self) -> float | None:
        raw = (self.coordinator.data or {}).get("raw")
        points = _extract_monthly_points(raw)
        if not points:
            return None
        last = points[-1]
        v = last.get("consommation")
        return float(v) if isinstance(v, (int, float)) else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        raw = (self.coordinator.data or {}).get("raw")
        points = _extract_monthly_points(raw)
        if not points:
            return {}
        last = points[-1]
        return {"month": _month_key(last), "origine": last.get("origine")}


class EGLMonthlyConsumptionOffsetSensor(EGLBaseEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS

    def __init__(self, coordinator, idx_from_latest: int) -> None:
        super().__init__(coordinator)
        self._idx = idx_from_latest
        self._attr_unique_id = f"egl_month_m{idx_from_latest:02d}_m3"
        self._value: float | None = None
        self._month_label: str | None = None
        self._attr_name = f"Conso M-{self._idx}"
        self._recalc()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._recalc()
        self.async_write_ha_state()

    def _recalc(self) -> None:
        raw = (self.coordinator.data or {}).get("raw")
        points = _extract_monthly_points(raw)

        if len(points) <= self._idx:
            self._value = None
            self._month_label = None
            return

        point = points[-1 - self._idx]
        v = point.get("consommation")
        self._value = float(v) if isinstance(v, (int, float)) else None

        y = point.get("annee")
        m_idx = point.get("mois")  # 0..11
        if isinstance(y, int) and isinstance(m_idx, int) and 0 <= m_idx <= 11:
            self._month_label = f"{MONTH_NAMES_FR[m_idx]} {y}"
        else:
            self._month_label = _month_key(point)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._recalc()
        super()._handle_coordinator_update()

    @property
    def native_value(self) -> float | None:
        return self._value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        raw = (self.coordinator.data or {}).get("raw")
        points = _extract_monthly_points(raw)
        if len(points) <= self._idx:
            return {}

        point = points[-1 - self._idx]
        return {
            "month": _month_key(point),
            "month_label": self._month_label,
            "annee": point.get("annee"),
            "mois_index": point.get("mois"),
            "origine": point.get("origine"),
        }


async def async_setup_entry(
    hass,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        EGLWaterIndexTotalIncreasingSensor(coordinator),  # Energy -> Water
        EGLWaterLastDayConsumptionSensor(coordinator),
        EGLWaterTotalIncreasingSensor(coordinator),
        EGLMonthlyConsumptionLastSensor(coordinator),
    ]

    entities.extend(
        EGLMonthlyConsumptionOffsetSensor(coordinator, i)
        for i in range(MONTHS_TO_EXPOSE)
    )

    async_add_entities(entities)
