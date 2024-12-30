# Preview Maid

![GHCR Build Status](https://github.com/fletchto99/preview-maid/actions/workflows/ghcr.yml/badge.svg)
![Docker Build Status](https://github.com/fletchto99/preview-maid/actions/workflows/docker.yml/badge.svg)
![Docker Pulls](https://img.shields.io/docker/pulls/fletchto99/preview-maid)

Preview maid is a tool to help you find missing thumbnail previews in your plex library. By default it will run upon startup and then be scheduled to run daily at 00:00. The schedule can be optionally turned off.

## Environment variables

| Variable | Description |
| :----: | --- |
| PLEX_URL | The URL to your plex instance. |
| PLEX_TOKEN | Your plex API token |
| RUN_ONCE | Set to true to disable scheduled runs, false is default. |