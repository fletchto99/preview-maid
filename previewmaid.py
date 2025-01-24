import logging
import os
import re
import schedule
import signal
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from plexapi.server import PlexServer

# Get environment variables with default values
PLEX_URL = os.getenv('PLEX_URL')
PLEX_TOKEN = os.getenv('PLEX_TOKEN')
RUN_ONCE = os.getenv('RUN_ONCE', 'False').lower() in ('true', '1', 't')
RUN_TIME = os.getenv('RUN_TIME', '00:00')
SKIP_LIBRARY_TYPES = os.getenv('SKIP_LIBRARY_TYPES', '').split(',')
SKIP_LIBRARY_NAMES = os.getenv('SKIP_LIBRARY_NAMES', '').split(',')
LOGS_DIRECTORY = os.getenv('LOGS_DIRECTORY')

# Set up logging
logger = logging.getLogger('preview_maid')
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

if LOGS_DIRECTORY:
    if not os.path.exists(LOGS_DIRECTORY):
        logger.error(f'Log file enabled and LOGS_DIRECTORY "{LOGS_DIRECTORY}" does not exist. Exiting...')
        exit()
    else:
        log_file = os.path.join(LOGS_DIRECTORY, 'preview_maid.log')
        file_handler = RotatingFileHandler(
            log_file,
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        if os.path.getsize(log_file) > 0:
            file_handler.doRollover()

logger.info('Starting Preview Maid...')

# Validate environment variables
if not PLEX_URL or not PLEX_TOKEN:
    logger.error('Please set the PLEX_URL and PLEX_TOKEN environment variables.')
    exit(1)

if SKIP_LIBRARY_TYPES != ['']:
    for library_type in SKIP_LIBRARY_TYPES:
        if library_type not in ('movie', 'show', 'photo'):
            logger.error(f'Library type {library_type} invalid; SKIP_LIBRARY_TYPES must be a comma-separated list of "movie", "show", or "photo".')
            exit(1)

TIME_PATTERN = r"^(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?$"
if RUN_TIME and not re.match(TIME_PATTERN, RUN_TIME):
    logger.error('RUN_TIME must be in the format HH:MM(:SS).')
    exit(1)

# Setup signal handlers
def log_interrupt(signal_received, frame):
    logger.warning('Received signal to terminate. Exiting...')
    exit(0)

signal.signal(signal.SIGTERM, log_interrupt)
signal.signal(signal.SIGINT, log_interrupt)

# Helper functions
def is_preview_thumbnails_enabled(library):
    for setting in library.settings():
        if setting.id == 'enableBIFGeneration':
            return setting.value
    return False

def check_missing_preview_thumbnails(medias):
    count = 0
    for media in medias:
        for part in media.parts:
            if not part.hasPreviewThumbnails:
                logger.warning(f'{part.file} is missing preview thumbnails')
                count += 1
    return count

def process_photos(album):
    count = 0
    for album in album.albums():
        count += process_photos(album)
    for clip in album.clips():
        count += check_missing_preview_thumbnails(clip.media)
    return count

def process_library(library, skip_library_types, skip_library_names):
    if not is_preview_thumbnails_enabled(library):
        logger.info(f'Skipping {library.title} as preview generation is disabled...')
        return
    if library.type in skip_library_types:
        logger.info(f'Skipping library {library.title} as {library.type} is in the SKIP_LIBRARY_TYPES list...')
        return
    if library.title in skip_library_names:
        logger.info(f'Skipping library {library.title} as {library.title} is in the SKIP_LIBRARY_NAMES list...')
        return
    logger.info(f'Processing library {library.title} of type {library.type}...')
    count = 0
    for item in library.all():
        if item.type == 'show':
            for episode in item.episodes():
                count += check_missing_preview_thumbnails(episode.media)
        elif item.type == 'movie':
            count += check_missing_preview_thumbnails(item.media)
        elif item.type == 'photo':
            count += process_photos(item)
    if count > 0:
        logger.warning(f'Found {count} missing preview thumbnails in {library.title}...')
    else:
        logger.info(f'No missing preview thumbnails found in {library.title}...')

def find_missing_metadata(plex_url, plex_token, skip_library_types, skip_library_names):
    try:
        logger.info('Testing connection to Plex server...')
        plex = PlexServer(PLEX_URL, PLEX_TOKEN, timeout=600)
        server_name = plex.friendlyName
        logger.info(f'Successfully connected to Plex server: {server_name}')
        logger.info('Searching for missing thumbnail previews...')
        for library in plex.library.sections():
            process_library(library, skip_library_types, skip_library_names)
        logger.info('Missing thumbnail preview run finished...')
    except Exception as e:
        logger.error(f'Failed to connect to Plex server for this run')

# Main logic
if RUN_ONCE:
    logger.info('Preview Maid is running in one-time mode...')
    find_missing_metadata(PLEX_URL, PLEX_TOKEN, SKIP_LIBRARY_TYPES, SKIP_LIBRARY_NAMES)
    logger.info('Run completed. Exiting since RUN_ONCE is set to True...')
    exit(0)
else:
    logger.info(f'Preview Maid is scheduled to run daily at {RUN_TIME}...')
    schedule.every().day.at(RUN_TIME).do(find_missing_metadata, PLEX_URL, PLEX_TOKEN, SKIP_LIBRARY_TYPES, SKIP_LIBRARY_NAMES)
    while True:
        schedule.run_pending()
        time.sleep(1)