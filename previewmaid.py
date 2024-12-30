import os
import schedule
import time
import signal
import sys
from datetime import datetime
from plexapi.server import PlexServer

def log(message):
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")

def test_plex_connection(plex):
    try:
        server_name = plex.friendlyName
        log(f"Successfully connected to Plex server: {server_name}")
    except Exception as e:
        log(f"Failed to connect to Plex server: {e}")
        sys.exit(1)

def is_preview_thumbnails_enabled(library):
    for setting in library.settings():
        if setting.id == 'enableBIFGeneration':
            return setting.value
    return False

def process_library(library):
    if not is_preview_thumbnails_enabled(library):
        log(f"Skipping {library.title}...")
        return
    log(f'Processing {library.title}...')
    for item in library.all():
        if item.type == 'show':
            for episode in item.episodes():
                if not episode.hasPreviewThumbnails:
                    log(f"{item.title} - {episode.title} (Season {episode.parentIndex}, Episode {episode.index}) "
                          f"has missing preview thumbnails.")
        elif not item.hasPreviewThumbnails:
            log(f"{item.title} has missing preview thumbnails.")

def find_missing_previews(libraries):
    log("Searching for missing previews...")
    for library in libraries:
        process_library(library)
    log("Missing preview run finished.")

# Get environment variables with default values
PLEX_URL = os.getenv("PLEX_URL")
PLEX_TOKEN = os.getenv("PLEX_TOKEN")
RUN_ONCE = os.getenv("RUN_ONCE", "False").lower() in ("true", "1", "t")

if not PLEX_URL or not PLEX_TOKEN:
    log("Please set the PLEX_URL and PLEX_TOKEN environment variables.")
    exit()

def exit_gracefully():
    log('Received signal to terminate. Exiting gracefully...')
    sys.exit(0)

signal.signal(signal.SIGTERM, exit_gracefully)
signal.signal(signal.SIGINT, exit_gracefully)

plex = PlexServer(PLEX_URL, PLEX_TOKEN, timeout=600)

log("Testing connection to Plex server...")
test_plex_connection(plex)
log("Preview Maid will now commence a bootup run..")
find_missing_previews(plex.library.sections())

if RUN_ONCE:
    exit()

log("Preview Maid is now going to run nightly at 00:00.")
schedule.every().day.at("00:00").do(lambda: find_missing_previews(plex.library.sections()))

while True:
    schedule.run_pending()
    time.sleep(60)