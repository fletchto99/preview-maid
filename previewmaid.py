import os
import schedule
import time
import signal
import sys
from plexapi.server import PlexServer

# Get environment variables with default values
PLEX_URL = os.getenv("PLEX_URL")
PLEX_TOKEN = os.getenv("PLEX_TOKEN")
RUN_ONCE = os.getenv("RUN_ONCE", "False").lower() in ("true", "1", "t")

if not PLEX_URL or not PLEX_TOKEN:
    print("Please set the PLEX_URL and PLEX_TOKEN environment variables.")
    exit()

def exit_gracefully():
    print('Received signal to terminate. Exiting gracefully...')
    sys.exit(0)

signal.signal(signal.SIGTERM, exit_gracefully)
signal.signal(signal.SIGINT, exit_gracefully)

def test_plex_connection(plex):
    try:
        server_name = plex.friendlyName
        print(f"Successfully connected to Plex server: {server_name}")
    except Exception as e:
        print(f"Failed to connect to Plex server: {e}")
        sys.exit(1)

def process_library(library):
    for item in library.all():
        if item.type == 'show':
            for episode in item.episodes():
                if not episode.hasPreviewThumbnails:
                    print(f"{item.title} - {episode.title} (Season {episode.parentIndex}, Episode {episode.index}) "
                          f"has missing preview thumbnails.")
        elif not item.hasPreviewThumbnails:
            print(f"{item.title} has missing preview thumbnails.")

def find_missing_previews(libraries):
    for library in libraries:
        if library.type == 'show' or library.type == 'movie':
            process_library(library)

plex = PlexServer(PLEX_URL, PLEX_TOKEN, timeout=600)

print("Testing connection to Plex server...")
test_plex_connection(plex)
print("Preview Maid is running the bootup run...")
find_missing_previews(plex.library.sections())
print("Bootup run complete. Preview Maid is now going to run nightly at 00:00.")

if RUN_ONCE:
    exit()

schedule.every().day.at("00:00").do(lambda: find_missing_previews(plex.library.sections()))

while True:
    schedule.run_pending()
    time.sleep(1)