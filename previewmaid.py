import os
import schedule
import time
import signal
import sys
from datetime import datetime
from plexapi.server import PlexServer

def log(message):
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")

def is_preview_thumbnails_enabled(library):
    for setting in library.settings():
        if setting.id == 'enableBIFGeneration':
            return setting.value
    return False

def check_missing_preview_thumbnails(medias):
    for media in medias:
        for part in media.parts:
            if not part.hasPreviewThumbnails:
                log(f"{part.file} is missing preview thumbnails")

def process_photos(album, path=''):
    for album in album.albums():
        process_photos(album, f"{path}/{album.title}")
    check_missing_preview_thumbnails(album.clips())

def process_library(library, skip_library_types, skip_library_names):
    if not is_preview_thumbnails_enabled(library):
        log(f"Skipping {library.title} as preview generation is disabled...")
        return
    if library.type in skip_library_types:
        log(f"Skipping {library.title} as {library.type} is in the SKIP_LIBRARY_TYPES list...")
        return
    if library.title in skip_library_names:
        log(f"Skipping {library.title} as {library.title} is in the SKIP_LIBRARY_NAMES list...")
        return
    log(f'Processing {library.title} of type {library.type}...')
    for item in library.all():
        if item.type == 'show':
            for episode in item.episodes():
                check_missing_preview_thumbnails(episode.media)
        elif item.type == 'movie':
            check_missing_preview_thumbnails(item.media)
        elif item.type == 'photo':
            process_photos(item, item.title)

def find_missing_previews(plex_url, plex_token, skip_library_types, skip_library_names):
    try:
        log("Testing connection to Plex server...")
        plex = PlexServer(PLEX_URL, PLEX_TOKEN, timeout=600)
        server_name = plex.friendlyName
        log(f"Successfully connected to Plex server: {server_name}")
        log("Searching for missing previews...")
        for library in plex.library.sections():
            process_library(library, skip_library_types, skip_library_names)
        log("Missing preview run finished.")
    except Exception as e:
        log(f"Failed to connect to Plex server for this run")

# Get environment variables with default values
PLEX_URL = os.getenv("PLEX_URL")
PLEX_TOKEN = os.getenv("PLEX_TOKEN")
RUN_ONCE = os.getenv("RUN_ONCE", "False").lower() in ("true", "1", "t")
SKIP_LIBRARY_TYPES = os.getenv("SKIP_LIBRARY_TYPES", "").split(",")
SKIP_LIBRARY_NAMES = os.getenv("SKIP_LIBRARY_NAMES", "").split(",")

if not PLEX_URL or not PLEX_TOKEN:
    log("Please set the PLEX_URL and PLEX_TOKEN environment variables.")
    exit()

def exit_gracefully():
    log('Received signal to terminate. Exiting gracefully...')
    sys.exit(0)

signal.signal(signal.SIGTERM, exit_gracefully)
signal.signal(signal.SIGINT, exit_gracefully)

if RUN_ONCE:
    log("Preview Maid is running in one-time mode...")
    find_missing_previews(PLEX_URL, PLEX_TOKEN, SKIP_LIBRARY_TYPES, SKIP_LIBRARY_NAMES)
    log("Run completed. Exiting...")
    exit()
else:
    log("Preview Maid is scheduled to run nightly at 00:00.")
    schedule.every().day.at("00:00").do(lambda: find_missing_previews(PLEX_URL, PLEX_TOKEN, SKIP_LIBRARY_TYPES, SKIP_LIBRARY_NAMES))

    while True:
        schedule.run_pending()
        time.sleep(10)