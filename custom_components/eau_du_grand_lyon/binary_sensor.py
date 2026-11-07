"""Binary sensors for Eau du Grand Lyon."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .sensor import _extract_daily_points


class EGLBaseBinaryEntity(CoordinatorEntity):
    """Base binary entity providing device_info for Eau du Grand Lyon."""

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


class EGLWaterLeakBinarySensor(EGLBaseBinaryEntity, BinarySensorEntity):
    """Détecteur d'alerte fuite d'eau d'après le télérelevé quotidien."""

    _attr_name = "Eau (alerte fuite)"
    _attr_unique_id = "egl_water_leak_alert"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool | None:
        raw_j = (self.coordinator.data or {}).get("raw_journalier")
        points = _extract_daily_points(raw_j)
        if not points:
            return None
        last = points[-1]
        leak_vol = last.get("volumeEstimeFuite")
        if isinstance(leak_vol, (int, float)) and leak_vol > 0:
            return True
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        raw_j = (self.coordinator.data or {}).get("raw_journalier")
        points = _extract_daily_points(raw_j)
        if not points:
            return {}
        last = points[-1]
        return {
            "volume_estime_fuite": last.get("volumeEstimeFuite"),
            "debit_min": last.get("debitMin"),
            "origine": last.get("origine"),
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eau du Grand Lyon binary sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EGLWaterLeakBinarySensor(coordinator)])
