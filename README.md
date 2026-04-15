# Preview Maid

[![Build Status](https://github.com/fletchto99/preview-maid/actions/workflows/publish_release.yml/badge.svg)](https://github.com/fletchto99/preview-maid/actions/workflows/publish_release.yml)
[![Docker Pulls](https://img.shields.io/docker/pulls/fletchto99/preview-maid)](https://hub.docker.com/r/fletchto99/preview-maid)
[![GitHub License](https://img.shields.io/github/license/fletchto99/preview-maid)](https://github.com/fletchto99/preview-maid/blob/main/LICENSE)

Preview Maid is a tool that scans your Plex library for missing preview thumbnails, voice activity analysis data, and marker data. It can run as a daily scheduled job at a configurable time or as a one-off job.

## Supported Architectures

| Architecture | Available | Tag |
| :----: | :----: | ---- |
| x86-64 | ✅ | latest |
| arm64 | ✅ | latest |

## Images

| Registry       | Image                                |
| -------------- | ------------------------------------ |
| **GHCR**       | `ghcr.io/fletchto99/preview-maid`    |
| **Docker Hub** | `fletchto99/preview-maid`            |

## Quick Start

### Docker Compose (recommended)

```yaml
services:
  preview-maid:
    image: ghcr.io/fletchto99/preview-maid:latest
    container_name: preview-maid
    environment:
      - PLEX_URL=http://your-plex-server:32400
      - PLEX_TOKEN=your-plex-token
      - RUN_TIME=02:00
    volumes:
      - /path/to/logs:/app/logs  # optional
    restart: unless-stopped
```

### Docker CLI

```bash
docker run -d \
  --name preview-maid \
  -e PLEX_URL=http://your-plex-server:32400 \
  -e PLEX_TOKEN=your-plex-token \
  -e RUN_TIME=02:00 \
  -v /path/to/logs:/app/logs \
  --restart unless-stopped \
  ghcr.io/fletchto99/preview-maid:latest
```

## Configuration

### Environment Variables

| Variable | Description | Default |
| :----: | --- | :----: |
| `PLEX_URL` | The URL to your Plex instance | *required* |
| `PLEX_TOKEN` | Your Plex API token | *required* |
| `FIND_MISSING_THUMBNAIL_PREVIEWS` | Find missing thumbnail previews | `true` |
| `FIND_MISSING_VOICE_ACTIVITY` | Find missing voice activity analysis data | `false` |
| `FIND_MISSING_INTRO_MARKERS` | Find missing skip intro markers (slow on large libraries) | `false` |
| `FIND_MISSING_CREDITS_MARKERS` | Find missing skip credit markers (slow on large libraries) | `false` |
| `FIND_MISSING_AD_MARKERS` | Find missing ad markers (slow on large libraries) | `false` |
| `RUN_ONCE` | Run once and exit instead of scheduling | `false` |
| `RUN_TIME` | Time to run the daily job (`HH:MM` format) | `00:00` |
| `SKIP_LIBRARY_TYPES` | Comma-separated library types to skip (`movie`, `show`, `photo`) | `""` |
| `SKIP_LIBRARY_NAMES` | Comma-separated library names to skip | `""` |
| `DEBUG` | Enable debug logging | `false` |

### Optional Volume Mounts

| Mount | Description |
| :----: | --- |
| `/app/logs` | Log file output with rotation (last 5 runs). When mounted, console output shows statistics only. |

## Building Missing Previews, Audio Analysis & Markers

You can force the creation of missing data using the **Analyze** option on the library or individual media items in Plex.

If preview thumbnail generation fails, try setting `GenerateBIFKeyframesOnly` to `0` in the [Plex advanced settings](https://support.plex.tv/articles/201105343-advanced-hidden-server-settings/). **Note:** This increases generation time and CPU load significantly.

## Building Locally

```bash
git clone https://github.com/fletchto99/preview-maid.git
cd preview-maid
docker build -t preview-maid .
```