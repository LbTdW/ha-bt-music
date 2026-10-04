"""Media Player platform for BT Music Speaker integration."""
import logging
from datetime import timedelta
from typing import Any

import aiohttp

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
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, CONF_HOST, CONF_API_KEY

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)


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

    async_add_entities([BtMusicSpeakerEntity(coordinator)], True)


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
        url = f"http://{self.host}/rest/status"
        _LOGGER.info("BT Music polling %s, key=%s", url, repr(self.api_key[:8]) if self.api_key else "EMPTY")
        try:
            async with self.session.get(
                url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    _LOGGER.error("BT Music poll returned HTTP %s", resp.status)
                    raise UpdateFailed(f"Status {resp.status}")
                data = await resp.json()
                _LOGGER.debug("BT Music status: %s", data)
                return data
        except (aiohttp.ClientError, TimeoutError, OSError) as err:
            _LOGGER.error("BT Music fetch error: %s", err)
            raise UpdateFailed(f"Error fetching status: {err}")


class BtMusicSpeakerEntity(CoordinatorEntity, MediaPlayerEntity):
    """Representation of a BT Music Speaker."""

    _attr_has_entity_name = True
    _attr_name = "Sony Speaker"
    _attr_device_class = "speaker"
    _attr_icon = "mdi:speaker"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = "bt_music_sony_speaker"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._coordinator.last_update_success

    @property
    def state(self) -> MediaPlayerState:
        """Return the state of the media player."""
        data = self._coordinator.data
        if not data:
            return MediaPlayerState.OFF
        if data.get("playing"):
            return MediaPlayerState.PLAYING
        if data.get("connected"):
            return MediaPlayerState.IDLE
        if data.get("state") == "playing":
            return MediaPlayerState.PLAYING
        if data.get("state") == "idle":
            return MediaPlayerState.IDLE
        return MediaPlayerState.OFF

    @property
    def volume_level(self) -> float | None:
        """Volume level of the media player (0..1)."""
        data = self._coordinator.data
        if data and data.get("volume_level") is not None:
            return data["volume_level"]
        if data and data.get("volume") is not None:
            return data["volume"] / 100.0
        return None

    @property
    def media_title(self) -> str | None:
        """Title of current playing media."""
        data = self._coordinator.data
        if data:
            return data.get("media_title") or data.get("current_track")
        return None

    @property
    def media_artist(self) -> str | None:
        """Artist of current playing media."""
        data = self._coordinator.data
        if data:
            return data.get("media_artist") or data.get("current_artist")
        return None

    @property
    def media_content_type(self) -> str | None:
        """Content type of current playing media."""
        return MediaType.MUSIC

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Flag media player features that are supported."""
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

    async def _send_control(self, action: str, **kwargs) -> None:
        """Send a control command to the REST bridge."""
        payload = {"action": action, **kwargs}
        try:
            async with self._coordinator.session.post(
                f"http://{self._coordinator.host}/rest/control",
                headers={
                    "Authorization": f"Bearer {self._coordinator.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                _LOGGER.debug("Control %s: status %s", action, resp.status)
        except (aiohttp.ClientError, TimeoutError, OSError) as err:
            _LOGGER.error("Control %s failed: %s", action, err)

        await self._coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        """Turn the media player on."""
        await self._send_control("power_on")

    async def async_turn_off(self) -> None:
        """Turn the media player off."""
        await self._send_control("power_off")

    async def async_media_play(self) -> None:
        """Send play command."""
        await self._send_control("play")

    async def async_media_pause(self) -> None:
        """Send pause command."""
        await self._send_control("pause")

    async def async_media_stop(self) -> None:
        """Send stop command."""
        await self._send_control("stop")

    async def async_media_next_track(self) -> None:
        """Send next track command."""
        await self._send_control("skip")

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        await self._send_control("volume", level=int(volume * 100))

    async def async_volume_up(self) -> None:
        """Volume up the media player."""
        data = self._coordinator.data
        current = data.get("volume", 50) if data else 50
        await self._send_control("volume", level=min(current + 10, 100))

    async def async_volume_down(self) -> None:
        """Volume down the media player."""
        data = self._coordinator.data
        current = data.get("volume", 50) if data else 50
        await self._send_control("volume", level=max(current - 10, 0))

    async def async_play_media(
        self, media_type: str, media_id: str, **kwargs: Any
    ) -> None:
        """Play media from search query."""
        if media_type in (MediaType.MUSIC, "music", "playlist", "track"):
            await self._send_control("play", query=media_id)