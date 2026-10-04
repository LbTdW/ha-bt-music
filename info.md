# BT Music Speaker

Home Assistant custom integration for controlling a Bluetooth speaker via the BT Music MCP REST bridge.

## Features

- **Media Player Entity**: Full media_player entity for your Bluetooth speaker
- **Playback Control**: Play, pause, stop, skip, volume up/down
- **Status Polling**: Auto-refreshes every 10 seconds
- **Play Media**: Play tracks by search query
- **Power Management**: Turn on (BT connect) / Turn off (BT disconnect)
- **No YAML Required**: Full UI configuration via config flow

## Requirements

- BT Music MCP server running on Docker VM with REST bridge on port 8767
- HACS installed in Home Assistant

## Installation

1. Add this repository as a custom repository in HACS (Integrations category)
2. Click "Download"
3. Restart Home Assistant
4. Settings → Devices & Services → Add Integration → "BT Music Speaker"
5. Enter host (e.g. `192.168.178.57:8767`) and API key

## Configuration

| Field | Description | Default |
|-------|-------------|---------|
| Host | IP:Port of the REST bridge | `192.168.178.57:8767` |
| API Key | Authentication key for the REST bridge | `bt-music-key-2026` |

## Entity

After setup, you'll get:
- `media_player.bt_music_sony_speaker` — The Bluetooth speaker media player

## Usage

Use the media player card or mini-media-player card on your dashboard:

```yaml
type: custom:mini-media-player
entity: media_player.bt_music_sony_speaker
artwork: cover
volume_stateless: false
```

## Source

- REST Bridge: `scripts/bt-music-rest-bridge.py` (runs inside bt-music-mcp container)
- GitHub: https://github.com/LbTdW/ha-bt-music