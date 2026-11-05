"""Coordinator for Eau du Grand Lyon."""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMetaData,
    StatisticMeanType,
)
from homeassistant.components.recorder.statistics import async_add_external_statistics

from .const import (
    AUTH_AUTHENTIFICATION,
    AUTH_AUTHORIZE,
    AUTH_TOKEN,
    BASE_URL,
    CONF_CLIENT_ID,
    CONF_CONTRAT_ID,
    CONF_PASSWORD,
    CONF_USERNAME,
    DEFAULT_CLIENT_ID,
    DEFAULT_CONTRAT_ID,
    DEFAULT_DAYS_BACK,
    DOMAIN,
    REDIRECT_URI,
    REST_JOURNALIER,
    REST_MENSUEL,
)

_LOGGER = logging.getLogger(__name__)
TZ_PARIS = ZoneInfo("Europe/Paris")


def _to_iso_z(dt: datetime) -> str:
    """Return ISO 8601 with Z suffix (like JS toISOString())."""
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _extract_daily_points(raw_j: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_j, dict):
        return []
    postes = raw_j.get("postes")
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


class EGLDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self._session = async_get_clientsession(hass)
        self._logged_in = False
        self._auth_headers: dict[str, str] | None = None
        self._store = Store(hass, 1, f"{DOMAIN}_{entry.entry_id}")

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=6),  # 1x/jour suffit, 6h = safe
        )

    async def _async_ensure_auth(self) -> None:
        """Réutilise le token en cache s'il existe pour éviter de saturer les connexions."""
        if self._auth_headers is not None:
            return

        cached = await self._store.async_load()
        if isinstance(cached, dict) and cached.get("access_token"):
            token_type = cached.get("token_type", "Bearer")
            access_token = cached["access_token"]
            self._auth_headers = {
                "Authorization": f"{token_type} {access_token}",
                "entreprise": "EPGL",
                "Accept": "application/json, text/plain, */*",
            }
            self._logged_in = True
            _LOGGER.debug("Eau du Grand Lyon: réutilisation du token persistant depuis le cache.")
            return

        await self._async_login()

    async def _async_login(self) -> None:
        """Login via PKCE, puis stocke Authorization Bearer dans la session et le cache persistant."""
        client_id = self.entry.data.get(CONF_CLIENT_ID) or DEFAULT_CLIENT_ID

        code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip("=")

        r = await self._session.post(
            f"{BASE_URL}{AUTH_AUTHENTIFICATION}",
            data={
                "username": self.entry.data[CONF_USERNAME],
                "password": self.entry.data[CONF_PASSWORD],
                "client_id": client_id,
            },
        )
        if r.status != 200:
            body = await r.text()
            if r.status == 403 or "nombre maximum de connexion" in body:
                _LOGGER.error(
                    "Eau du Grand Lyon: nombre maximum de connexions simultanées atteint. "
                    "Le serveur bloque temporairement la création de nouvelles sessions. "
                    "Conseil: déconnectez-vous de votre compte sur le site agence.eaudugrandlyon.com "
                    "(clic sur 'Déconnexion') et attendez environ 10 à 15 minutes sans recharger l'intégration."
                )
            raise UpdateFailed(
                f"authentification failed: HTTP {r.status} body={body[:200]}"
            )

        r = await self._session.get(
            f"{BASE_URL}{AUTH_AUTHORIZE}",
            params={
                "redirect_uri": REDIRECT_URI,
                "response_type": "code",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "client_id": client_id,
            },
            allow_redirects=False,
        )
        if r.status not in (301, 302, 303, 307, 308) or "Location" not in r.headers:
            body = await r.text()
            raise UpdateFailed(f"authorize failed: HTTP {r.status} body={body[:200]}")

        loc = r.headers["Location"]
        code = (parse_qs(urlparse(loc).query).get("code") or [None])[0]
        if not code:
            raise UpdateFailed("authorize did not return code")

        r = await self._session.post(
            f"{BASE_URL}{AUTH_TOKEN}",
            data={
                "client_id": client_id,
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            },
        )
        if r.status != 200:
            body = await r.text()
            raise UpdateFailed(f"token failed: HTTP {r.status} body={body[:200]}")

        token_json = await r.json()
        access_token = token_json.get("access_token")
        token_type = token_json.get("token_type", "Bearer")
        if not access_token:
            raise UpdateFailed(f"token missing, keys={list(token_json.keys())}")

        self._auth_headers = {
            "Authorization": f"{token_type} {access_token}",
            "entreprise": "EPGL",
            "Accept": "application/json, text/plain, */*",
        }
        self._logged_in = True

        # Sauvegarder dans le cache persistant
        try:
            await self._store.async_save(
                {"token_type": token_type, "access_token": access_token}
            )
        except Exception as save_err:
            _LOGGER.debug("Impossible d'enregistrer le token dans le store : %s", save_err)

    async def _async_get_active_contract_id(self) -> str:
        """Découvre dynamiquement l'identifiant de contrat actif (chiffré dynamiquement par session)."""
        url_contrats = f"{BASE_URL}/application/rest/produits/contrats"
        resp = await self._session.get(url_contrats, headers=self._auth_headers)

        if resp.status == 401:
            _LOGGER.debug("Contrats: 401 -> token expire, renouvellement login")
            await self._store.async_remove()
            await self._async_login()
            resp = await self._session.get(url_contrats, headers=self._auth_headers)

        if resp.status != 200:
            body = await resp.text()
            raise UpdateFailed(
                f"Erreur recuperation contrats : HTTP {resp.status} body={body[:200]}"
            )

        contrats = await resp.json()
        if not isinstance(contrats, list) or not contrats:
            raise UpdateFailed("Aucun contrat d'eau trouve sur ce compte Eau du Grand Lyon")

        c_id = contrats[0].get("id")
        if not c_id:
            raise UpdateFailed(f"Format de contrat inattendu : {contrats[0]}")

        _LOGGER.debug("Eau du Grand Lyon: contrat actif detecte : %s", c_id)
        return c_id

    def _daily_range_params(self) -> dict[str, str]:
        """
        Fenêtre sur jours complets en Europe/Paris, convertie en UTC.
        Ça évite d’avoir des points “partiels” selon l’heure d’exécution.
        """
        now_local = datetime.now(TZ_PARIS)
        end_local = now_local.replace(hour=23, minute=59, second=59, microsecond=999000)
        start_local = (end_local - timedelta(days=DEFAULT_DAYS_BACK)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        return {"dateDebut": _to_iso_z(start_local), "dateFin": _to_iso_z(end_local)}

    async def _async_update_data(self) -> dict:
        try:
            if not self._logged_in:
                await self._async_ensure_auth()

            # Récupération automatique du contrat actif (chiffré dynamiquement)
            contrat_id = await self._async_get_active_contract_id()

            # 1) Mensuel
            url_m = f"{BASE_URL}{REST_MENSUEL.format(contrat_id=contrat_id)}"
            resp_m = await self._session.get(url_m, headers=self._auth_headers)

            if resp_m.status in (404, 400):
                # Fallback sur l'autre namespace si besoin
                fallback_m = f"{BASE_URL}/application/rest/interfaces/ael/contrats/{contrat_id}/consommationsMensuelles"
                resp_m = await self._session.get(fallback_m, headers=self._auth_headers)

            if resp_m.status == 401:
                _LOGGER.debug("Mensuel: 401 -> token expire, renouvellement login")
                await self._store.async_remove()
                await self._async_login()
                contrat_id = await self._async_get_active_contract_id()
                resp_m = await self._session.get(url_m, headers=self._auth_headers)

            if resp_m.status != 200:
                body = await resp_m.text()
                raise UpdateFailed(f"Mensuel HTTP {resp_m.status} body={body[:200]}")

            data_m = await resp_m.json()

            # 2) Journalier (fenêtre glissante)
            url_j = f"{BASE_URL}{REST_JOURNALIER.format(contrat_id=contrat_id)}"
            params = self._daily_range_params()

            resp_j = await self._session.get(
                url_j,
                headers=self._auth_headers,
                params=params,
            )

            if resp_j.status == 401:
                _LOGGER.debug("Journalier: 401 -> token expire, renouvellement login")
                await self._store.async_remove()
                await self._async_login()
                contrat_id = await self._async_get_active_contract_id()
                url_j = f"{BASE_URL}{REST_JOURNALIER.format(contrat_id=contrat_id)}"
                resp_j = await self._session.get(
                    url_j,
                    headers=self._auth_headers,
                    params=params,
                )

            data_j = None
            if resp_j.status == 200:
                data_j = await resp_j.json()
                self._insert_statistics(data_j)
            else:
                body_j = await resp_j.text()
                _LOGGER.warning(
                    "Journalier HTTP %s (url=%s) : %s",
                    resp_j.status,
                    url_j,
                    body_j[:300],
                )

            return {
                "raw": data_m,
                "raw_journalier": data_j,
            }

        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(str(err)) from err

    def _insert_statistics(self, raw_journalier: Any) -> None:
        """Insert historical long-term external statistics for Home Assistant Energy Dashboard."""
        points = _extract_daily_points(raw_journalier)
        if not points:
            return

        # Déduplication et tri par date réelle (consommation du jour D)
        daily_records: dict[date, tuple[float | None, float | None]] = {}
        for p in points:
            d = _point_to_date(p)
            if d is None:
                continue
            idx = p.get("index")
            idx_f = float(idx) if isinstance(idx, (int, float)) else None
            conso = p.get("consommation")
            conso_f = float(conso) if isinstance(conso, (int, float)) else None
            daily_records[d] = (idx_f, conso_f)

        sorted_days = sorted(daily_records.keys())
        if not sorted_days:
            return

        # Construction de la série statistique continue.
        # Pour que la consommation du jour D apparaisse sur le jour D dans HA Energy :
        # - Début du jour D : D 00:00:00 (Europe/Paris en UTC), sum = cumul avant D.
        # - Fin du jour D : (D + 1 jour) 00:00:00 (Europe/Paris en UTC), sum = cumul après D.
        # HA calcule alors : Conso(D) = sum((D+1) 00:00) - sum(D 00:00).
        stats: list[StatisticData] = []

        first_day = sorted_days[0]
        first_idx, first_conso = daily_records[first_day]

        if first_idx is not None and first_conso is not None:
            running_sum = max(0.0, first_idx - first_conso)
        elif first_idx is not None:
            running_sum = max(0.0, first_idx)
        else:
            running_sum = 0.0

        # Point de départ au début du premier jour
        first_start_dt = datetime.combine(first_day, time(0, 0), tzinfo=TZ_PARIS).astimezone(timezone.utc)
        stats.append(
            StatisticData(
                start=first_start_dt,
                state=running_sum,
                sum=running_sum,
            )
        )

        prev_day = first_day
        for day in sorted_days:
            idx_val, conso_val = daily_records[day]

            # Si trou dans les jours relevés, fixer le début du jour courant
            if day > prev_day + timedelta(days=1):
                gap_start_dt = datetime.combine(day, time(0, 0), tzinfo=TZ_PARIS).astimezone(timezone.utc)
                stats.append(
                    StatisticData(
                        start=gap_start_dt,
                        state=running_sum,
                        sum=running_sum,
                    )
                )

            # Consommation du jour
            if conso_val is not None:
                day_conso = max(0.0, conso_val)
            elif idx_val is not None:
                day_conso = max(0.0, idx_val - running_sum)
            else:
                day_conso = 0.0

            running_sum += day_conso
            state_val = idx_val if idx_val is not None else running_sum

            # Fin du jour = début du jour suivant à 00:00:00
            end_of_day_dt = datetime.combine(day + timedelta(days=1), time(0, 0), tzinfo=TZ_PARIS).astimezone(timezone.utc)
            stats.append(
                StatisticData(
                    start=end_of_day_dt,
                    state=state_val,
                    sum=running_sum,
                )
            )
            prev_day = day

        if not stats:
            return

        stat_id = f"{DOMAIN}:water_consumption"
        metadata = StatisticMetaData(
            has_mean=False,
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name="Eau du Grand Lyon (Consommation)",
            source=DOMAIN,
            statistic_id=stat_id,
            unit_of_measurement=UnitOfVolume.LITERS,
            unit_class="volume",
        )

        try:
            async_add_external_statistics(self.hass, metadata, stats)
            _LOGGER.info(
                "Eau du Grand Lyon: %d points de statistiques externes injectés (du %s au %s, id=%s)",
                len(stats),
                sorted_days[0].isoformat(),
                sorted_days[-1].isoformat(),
                stat_id,
            )
        except Exception as err:
            _LOGGER.error("Erreur lors de l'injection des statistiques externes : %s", err)
