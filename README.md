# Preview Maid

![GHCR Build Status](https://github.com/fletchto99/preview-maid/actions/workflows/ghcr.yml/badge.svg)
![Docker Build Status](https://github.com/fletchto99/preview-maid/actions/workflows/docker.yml/badge.svg)
![Docker Pulls](https://img.shields.io/docker/pulls/fletchto99/preview-maid)

Preview maid is a tool to help you find missing thumbnail previews in your plex library. By default it will run daily at 00:00. Optionally you can set `RUN_ONCE` to `true` to disable the scheduled runs and have it run immediately.

The results of the runs are output to the console.

## Building missing previews

You can try to force the creation of missing preview thumbnails using the `Analyze` option on the library. If this fails you can try setting `GenerateBIFKeyframesOnly` to `0` in the [plex advanced settings](https://support.plex.tv/articles/201105343-advanced-hidden-server-settings/). **Note:** This will increase the time it takes to generate preview thumbnails and will greatly increase the load on your CPU.

## Environment variables

| Variable | Description |
| :----: | --- |
| PLEX_URL | The URL to your plex instance. |
| PLEX_TOKEN | Your plex API token |
| RUN_ONCE | Set to true to disable scheduled runs; default false |
| SKIP_LIBRARY_TYPES | A comma separated list of library types to skip. Options are movie,show,photo; default "" |
| SKIP_LIBRARY_NAMES | A comma separated list of library names to skip; default "" |
