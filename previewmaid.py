import logging
import os
import re
import schedule
import signal
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from plexapi.server import PlexServer

# Plex variables
PLEX_URL = os.getenv('PLEX_URL')
PLEX_TOKEN = os.getenv('PLEX_TOKEN')

# Preview Maid variables
FIND_MISSING_THUMBNAIL_PREVIEWS = os.getenv('FIND_MISSING_THUMBNAIL_PREVIEWS', 'True').lower() in ('true', '1', 't')
FIND_MISSING_VOICE_ACTIVITY = os.getenv('FIND_MISSING_VOICE_ACTIVITY', 'False').lower() in ('true', '1', 't')
FIND_MISSING_INTRO_MARKERS = os.getenv('FIND_MISSING_INTRO_MARKERS', 'False').lower() in ('true', '1', 't')
FIND_MISSING_CREDITS_MARKERS = os.getenv('FIND_MISSING_CREDITS_MARKERS', 'False').lower() in ('true', '1', 't')

# Run variables
RUN_ONCE = os.getenv('RUN_ONCE', 'False').lower() in ('true', '1', 't')
RUN_TIME = os.getenv('RUN_TIME', '00:00')

# Library skip variables
SKIP_LIBRARY_TYPES = os.getenv('SKIP_LIBRARY_TYPES', '').split(',')
SKIP_LIBRARY_NAMES = os.getenv('SKIP_LIBRARY_NAMES', '').split(',')

# Logging variables
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
LOG_DIRECTORY = '/app/logs'

log_level = logging.DEBUG if DEBUG else logging.INFO

# Set up logging
logger = logging.getLogger('preview_maid')
logger.setLevel(log_level)

formatter = logging.Formatter(
    fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

console_handler = logging.StreamHandler()
console_handler.setLevel(log_level)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

if not os.path.exists(LOG_DIRECTORY):
    logger.warning(f'Log directory "{LOG_DIRECTORY}" does not exist, logs will only be output to console...')
else:
    log_file = os.path.join(LOG_DIRECTORY, 'preview_maid.log')
    file_handler = RotatingFileHandler(
        log_file,
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    if os.path.getsize(log_file) > 0:
        file_handler.doRollover()

    logger.info(f'Since log file is being used, logs to the console will only show stats...')
    logger.info(f'To see missing previews and voice data check "{log_file}"...')
    console_handler.addFilter(lambda record: record.levelno != logging.WARN)

# Validate environment variables
if not PLEX_URL or not PLEX_TOKEN:
    logger.error('Please set the PLEX_URL and PLEX_TOKEN environment variables.')
    exit(1)

if not FIND_MISSING_THUMBNAIL_PREVIEWS and not FIND_MISSING_VOICE_ACTIVITY and not FIND_MISSING_INTRO_MARKERS and not FIND_MISSING_CREDITS_MARKERS:
    logger.error('One of the following settings must be enabled for previewmaid to work:')
    logger.error('- FIND_MISSING_THUMBNAIL_PREVIEWS')
    logger.error('- FIND_MISSING_VOICE_ACTIVITY')
    logger.error('- FIND_MISSING_INTRO_MARKERS')
    logger.error('- FIND_MISSING_CREDITS_MARKERS')
    exit(1)

if SKIP_LIBRARY_TYPES != ['']:
    for library_type in SKIP_LIBRARY_TYPES:
        if library_type not in ('movie', 'show', 'photo'):
            logger.error(f'Library type {library_type} invalid; SKIP_LIBRARY_TYPES must be a comma-separated list of "movie", "show", or "photo".')
            exit(1)

TIME_PATTERN = r'^(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?$'
if RUN_TIME and not re.match(TIME_PATTERN, RUN_TIME):
    logger.error('RUN_TIME must be in the format HH:MM(:SS).')
    exit(1)

# Setup signal handlers
def log_interrupt(signal_received, frame):
    logger.info('Received signal to terminate. Exiting...')
    exit(0)

signal.signal(signal.SIGTERM, log_interrupt)
signal.signal(signal.SIGINT, log_interrupt)

# Plex Helper functions
def is_library_setting_enabled(library, setting_id):
    for setting in library.settings():
        if setting.id == setting_id:
            return setting.value
    return False

# Preview Thumbnail Functions
def check_missing_preview_thumbnails_metadata(medias):
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
        count += check_missing_preview_thumbnails_metadata(clip.media)
    return count

def find_missing_preview_thumbnails(library, skip_library_types, skip_library_names):
    if library.type in skip_library_types:
        logger.info(f'Skipping library {library.title} as {library.type} is in the SKIP_LIBRARY_TYPES list...')
        return
    if library.title in skip_library_names:
        logger.info(f'Skipping library {library.title} as {library.title} is in the SKIP_LIBRARY_NAMES list...')
        return
    if not is_library_setting_enabled(library, 'enableBIFGeneration'):
        logger.info(f'Skipping {library.title} as preview generation is disabled...')
        return
    logger.info(f'Processing library {library.title} of type {library.type}...')
    count = 0
    for item in library.all():
        if item.type == 'show':
            for episode in item.episodes():
                count += check_missing_preview_thumbnails_metadata(episode.media)
        elif item.type == 'movie':
            count += check_missing_preview_thumbnails_metadata(item.media)
        elif item.type == 'photo':
            count += process_photos(item)
    if count > 0:
        logger.info(f'Found {count} missing preview thumbnails in {library.title}...')
    else:
        logger.info(f'No missing preview thumbnails found in {library.title}...')

# Voice Activity Functions
def check_missing_voice_activity_metadata(medias, media_data):
    count = 0
    for media in medias:
        if not media.hasVoiceActivity:
            logger.warning(f'"{media_data}" for resolution {media.videoResolution} is missing voice activity data')
            count += 1
    return count

def find_missing_voice_activity_data(library, skip_library_types, skip_library_names):
    if library.type in skip_library_types:
        logger.info(f'Skipping {library.title} as {library.type} is in the SKIP_LIBRARY_TYPES list...')
        return
    if library.title in skip_library_names:
        logger.info(f'Skipping {library.title} as {library.title} is in the SKIP_LIBRARY_NAMES list...')
        return
    if not is_library_setting_enabled(library, 'enableVoiceActivityGeneration'):
        logger.info(f'Skipping {library.title} as voice activity analysis is disabled...')
        return
    logger.info(f'Processing {library.title} of type {library.type}...')
    count = 0
    for item in library.all():
        if item.type == 'show':
            for episode in item.episodes():
                media_data = f'{item.title} - {episode.title} (Season {episode.parentIndex}, Episode {episode.index})'
                count += check_missing_voice_activity_metadata(episode.media, media_data)
        elif item.type == 'movie':
            count += check_missing_voice_activity_metadata(item.media, item.title)
    if count > 0:
        logger.info(f'Found {count} files with missing voice activity in {library.title}...')
    else:
        logger.info(f'No files are missing voice activity data in {library.title}...')

# Marker functions
def check_missing_marker_metadata(media, media_data, marker_type):
    for marker in media.markers:
        if marker.type == marker_type:
            return 0
    logger.warning(f'"{media_data}" is missing {marker_type} markers')
    return 1

def find_missing_marker_metadata(library, skip_library_types, skip_library_names, marker_type):
    if library.type in skip_library_types:
        logger.info(f'Skipping {library.title} as {library.type} is in the SKIP_LIBRARY_TYPES list...')
        return
    if library.title in skip_library_names:
        logger.info(f'Skipping {library.title} as {library.title} is in the SKIP_LIBRARY_NAMES list...')
        return
    setting = 'enableIntroMarkerGeneration' if marker_type == 'intro' else 'enableCreditsMarkerGeneration'
    if not is_library_setting_enabled(library, setting):
        logger.info(f'Skipping {library.title} as {marker_type} markers are disabled...')
        return
    logger.info(f'Processing {library.title} of type {library.type}...')
    count = 0
    for item in library.all():
        if item.type == 'show':
            for episode in item.episodes():
                media_data = f'{item.title} - {episode.title} (Season {episode.parentIndex}, Episode {episode.index})'
                count += check_missing_marker_metadata(episode, media_data, marker_type)
        elif item.type == 'movie':
            count += check_missing_marker_metadata(item, item.title, marker_type)
    if count > 0:
        logger.info(f'Found {count} files with missing {marker_type} markers in {library.title}...')
    else:
        logger.info(f'No files are missing {marker_type} markers in {library.title}...')

# Main logic
def find_missing_metadata(plex_url, plex_token, skip_library_types, skip_library_names):
    try:
        logger.info('Testing connection to Plex server...')
        plex = PlexServer(plex_url, plex_token, timeout=600)
        server_name = plex.friendlyName
        logger.info(f'Successfully connected to Plex server: {server_name}')

        libraries = plex.library.sections()

        if FIND_MISSING_THUMBNAIL_PREVIEWS:
            logger.info('Searching for missing thumbnail previews...')
            for library in libraries:
                find_missing_preview_thumbnails(library, skip_library_types, skip_library_names)
            logger.info('Missing thumbnail preview run finished...')

        if FIND_MISSING_VOICE_ACTIVITY:
            logger.info('Searching for missing voice activity data previews...')
            for library in libraries:
                find_missing_voice_activity_data(library, skip_library_types, skip_library_names)
            logger.info('Missing voice activity data run finished...')

        if FIND_MISSING_INTRO_MARKERS:
            logger.info('Searching for missing intro markers...')
            for library in libraries:
                find_missing_marker_metadata(library, skip_library_types, skip_library_names, 'intro')
            logger.info('Missing intro marker run finished...')

        if FIND_MISSING_CREDITS_MARKERS:
            logger.info('Searching for missing credits markers...')
            for library in libraries:
                find_missing_marker_metadata(library, skip_library_types, skip_library_names, 'credits')
            logger.info('Missing credits marker run finished...')

        logger.info('Run completed, check the logs for results...')
    except Exception as e:
        logger.error(f'Failed to connect to Plex server for this run...')
        logger.debug('An exception occurred: %s', e, exc_info=True)

# Entrypoint into main logic
if RUN_ONCE:
    logger.info('Preview Maid is running in one-time mode...')
    find_missing_metadata(PLEX_URL, PLEX_TOKEN, SKIP_LIBRARY_TYPES, SKIP_LIBRARY_NAMES)
    logger.info('Exiting since RUN_ONCE is set to True...')
    exit(0)
else:
    logger.info(f'Preview Maid is scheduled to run daily at {RUN_TIME}...')
    schedule.every().day.at(RUN_TIME).do(find_missing_metadata, PLEX_URL, PLEX_TOKEN, SKIP_LIBRARY_TYPES, SKIP_LIBRARY_NAMES)
    while True:
        schedule.run_pending()
        time.sleep(1)