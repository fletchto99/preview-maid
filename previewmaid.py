#!/usr/bin/env python3

import os
import time
import schedule

from plexapi.server import PlexServer

def process_library(library, plex):
    print(f'Processing {library.title}...')
    for item in library.all():
        if item.type == 'show':
            for episode in item.episodes():
                if not episode.hasPreviewThumbnails:
                    print(f"{item.title} - {episode.title} (Season {episode.parentIndex}, Episode {episode.index}) "
                        f"has missing preview thumbnails.")
        elif not item.hasPreviewThumbnails:
            print(f"{item.title} has missing preview thumbnails.")


plex = PlexServer(os.getenv("PLEX_URL"), os.getenv("PLEX_TOKEN"), timeout=600)
libraries = plex.library.sections()

def find_missing_previews():
    print
    for library in libraries:
        if library.type == 'show' or library.type == 'movie':
            process_library(library, plex)

print("Preview Maid is running the bootup run...")
find_missing_previews()
print("Bootup run complete. Preview Maid is now going to run nightly at 00:00.")

if os.getenv("RUN_ONCE"):
    exit()

schedule.every().day.at("00:00").do(find_missing_previews)

while True:
    schedule.run_pending()
    time.sleep(1)