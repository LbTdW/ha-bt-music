"""Media Player platform for BT Music Speaker integration."""
import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, CONF_HOST, CONF_API_KEY

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=10)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BT Music Speaker media player platform."""
    data = hass.data[DOMAIN][entry.entry_id]
    host = data["host"]
    api_key = data["api_key"]
    session = data["session"]

    coordinator = BtMusicCoordinator(hass, session, host, api_key)
    await coordinator.async_config_entry_first_refresh()

    async_add_entities([BtMusicSpeakerEntity(coordinator, host, api_key)], True)


class BtMusicCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch BT Music status."""

    def __init__(self, hass, session, host, api_key):
        super().__init__(
            hass,
            _LOGGER,
            name="BT Music Speaker",
            update_interval=SCAN_INTERVAL,
        )
        self.session = session
        self.host = host
        self.api_key = api_key

    async def _async_update_data(self):
        """Fetch data from REST bridge."""
        import aiohttp
        try:
            async with self.session.get(
                f"http://{self.host}/rest/status",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"Status {resp.status}")
                return await resp.json()
        except (aiohttp.ClientError, TimeoutError, OSError) as err:
            raise UpdateFailed(f"Error fetching status: {err}")


class BtMusicSpeakerEntity(MediaPlayerEntity):
    """Representation of a BT Music Speaker."""

    _attr_has_entity_name = True
    _attr_name = "Sony Speaker"
    _attr_device_class = "speaker"

    def __init__(self, coordinator, host, api_key):
        self._coordinator = coordinator
        self._host = host
        self._api_key = api_key
        self._attr_unique_id = "bt_music_sony_speaker"

    @property
    def available(self):
        return self._coordinator.last_update_success

    @property
    def state(self):
        data = self._coordinator.data
        if not data:
            return MediaPlayerState.OFF
        if data.get("playing", False):
            return MediaPlayerState.PLAYING
        if data.get("connected", False):
            return MediaPlayerState.IDLE
        if data.get("state") == "playing":
            return MediaPlayerState.PLAYING
        if data.get("state") == "idle":
            return MediaPlayerState.IDLE
        return MediaPlayerState.OFF

    @property
    def volume_level(self):
        data = self._coordinator.data
        if data and "volume_level" in data:
            return data["volume_level"]
        return None

    @property
    def media_title(self):
        data = self._coordinator.data
        if data:
            return data.get("media_title") or data.get("current_track")
        return None

    @property
    def media_artist(self):
        data = self._coordinator.data
        if data:
            return data.get("media_artist") or data.get("current_artist")
        return None

    @property
    def supported_features(self):
        return (
            MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.NEXT_TRACK
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.PLAY_MEDIA
        )

    async def _send_control(self, action, **kwargs):
        import aiohttp
        payload = {"action": action, **kwargs}
        try:
            async with self._coordinator.session.post(
                f"http://{self._host}/rest/control",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                _LOGGER.debug("Control %s: status %s", action, resp.status)
        except (aiohttp.ClientError, TimeoutError, OSError) as err:
            _LOGGER.error("Control %s failed: %s", action, err)

        await self._coordinator.async_request_refresh()

    async def async_turn_on(self):
        await self._send_control("power_on")

    async def async_turn_off(self):
        await self._send_control("power_off")

    async def async_media_play(self):
        await self._send_control("play")

    async def async_media_pause(self):
        await self._send_control("pause")

    async def async_media_stop(self):
        await self._send_control("stop")

    async def async_media_next_track(self):
        await self._send_control("skip")

    async def async_set_volume_level(self, volume):
        level = int(volume * 100)
        await self._send_control("volume", level=level)

    async def async_volume_up(self):
        data = self._coordinator.data
        current = data.get("volume", 50) if data else 50
        await self._send_control("volume", level=min(current + 10, 100))

    async def async_volume_down(self):
        data = self._coordinator.data
        current = data.get("volume", 50) if data else 50
        await self._send_control("volume", level=max(current - 10, 0))

    async def async_play_media(self, media_type, media_id, **kwargs):
        if media_type in (MediaType.MUSIC, "music", "playlist"):
            await self._send_control("play", query=media_id)