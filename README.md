# Preview Maid

![GHCR Build Status](https://github.com/fletchto99/preview-maid/actions/workflows/ghcr.yml/badge.svg)
![Docker Build Status](https://github.com/fletchto99/preview-maid/actions/workflows/docker.yml/badge.svg)
![Docker Pulls](https://img.shields.io/docker/pulls/fletchto99/preview-maid)

Preview maid is a tool which scans you library items for missing preview thumbnails and, optionally, missing voice activity analysis data. It can be run as a daily scheduled job at a configurable time or as a one-off job. For more information on how to generate the missing preview thumbnails and voice activity analysis data, see the section below.

## Building missing previews & Audio analysis data

You can try to force the creation of missing preview thumbnails & Audio analysis data using the `Analyze` option on the library. Sometimes plex is picky using the analyze button on the library itself, so you can try using the `Analyze` option on the individual media item.

If the preview thumbnail generation fails you can try setting `GenerateBIFKeyframesOnly` to `0` in the [plex advanced settings](https://support.plex.tv/articles/201105343-advanced-hidden-server-settings/). **Note:** This will increase the time it takes to generate preview thumbnails and will greatly increase the load on your CPU.

## Setup

### Environment variables

| Variable | Description | Default |
| :----: | --- | --- |
| PLEX_URL | The URL to your plex instance. | |
| PLEX_TOKEN | Your plex API token | |
| FIND_MISSING_THUMBNAIL_PREVIEWS | Set to true to find missing thumbnail previews | true |
| FIND_MISSING_VOICE_ACTIVITY | Set to true to find missing voice activity analysis data | false |
| RUN_ONCE | Set to true to disable scheduled runs | false |
| RUN_TIME | The time to run the job in the format `HH:MM` | 00:00 |
| SKIP_LIBRARY_TYPES | A comma separated list of library types to skip. Options are movie,show,photo | "" |
| SKIP_LIBRARY_NAMES | A comma separated list of library names to skip | "" |
| DEBUG | Set to true to enable debug logging | false |

### Optional Volume Mounts

| Mount | Description |
| :----: | --- |
| `/app/logs` | Used to write logs to a file, rotating per container restart and saving the last 5 restarts. |

**Note:** If the log volumne is mounted, the console output will only show statistics of the run while the affected files will be found in the logs.