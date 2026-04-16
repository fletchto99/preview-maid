from __future__ import annotations

import logging
import os
import re
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from typing import NamedTuple

import schedule
from plexapi.server import PlexServer


@dataclass
class Config:
    plex_url: str
    plex_token: str
    find_missing_thumbnail_previews: bool
    find_missing_voice_activity: bool
    find_missing_intro_markers: bool
    find_missing_credits_markers: bool
    find_missing_ad_markers: bool
    run_once: bool
    run_time: str
    skip_library_types: list[str] = field(default_factory=list)
    skip_library_names: list[str] = field(default_factory=list)
    debug: bool = False
    log_directory: str = "/app/logs"


class FeatureScan(NamedTuple):
    """Maps a config flag to the scan function and its arguments."""

    label: str
    setting: str
    scan_fn: str
    extra_args: tuple = ()


FEATURE_SCANS: list[FeatureScan] = [
    FeatureScan(
        "missing thumbnail previews",
        "find_missing_thumbnail_previews",
        "find_missing_preview_thumbnails",
    ),
    FeatureScan(
        "missing voice activity data",
        "find_missing_voice_activity",
        "find_missing_voice_activity_data",
    ),
    FeatureScan(
        "missing intro markers",
        "find_missing_intro_markers",
        "find_missing_marker_metadata",
        ("intro",),
    ),
    FeatureScan(
        "missing credits markers",
        "find_missing_credits_markers",
        "find_missing_marker_metadata",
        ("credits",),
    ),
    FeatureScan(
        "missing ad markers",
        "find_missing_ad_markers",
        "find_missing_marker_metadata",
        ("ad",),
    ),
]


def parse_bool_env(name: str, default: str = "False") -> bool:
    return os.getenv(name, default).lower() in ("true", "1", "t")


def load_config() -> Config:
    skip_types = [
        t.strip() for t in os.getenv("SKIP_LIBRARY_TYPES", "").split(",") if t.strip()
    ]
    skip_names = [
        n.strip() for n in os.getenv("SKIP_LIBRARY_NAMES", "").split(",") if n.strip()
    ]

    return Config(
        plex_url=os.getenv("PLEX_URL", ""),
        plex_token=os.getenv("PLEX_TOKEN", ""),
        find_missing_thumbnail_previews=parse_bool_env(
            "FIND_MISSING_THUMBNAIL_PREVIEWS", "True"
        ),
        find_missing_voice_activity=parse_bool_env("FIND_MISSING_VOICE_ACTIVITY"),
        find_missing_intro_markers=parse_bool_env("FIND_MISSING_INTRO_MARKERS"),
        find_missing_credits_markers=parse_bool_env("FIND_MISSING_CREDITS_MARKERS"),
        find_missing_ad_markers=parse_bool_env("FIND_MISSING_AD_MARKERS"),
        run_once=parse_bool_env("RUN_ONCE"),
        run_time=os.getenv("RUN_TIME", "00:00"),
        skip_library_types=skip_types,
        skip_library_names=skip_names,
        debug=parse_bool_env("DEBUG"),
    )


def validate_config(config: Config) -> list[str]:
    errors = []

    if not config.plex_url:
        errors.append("PLEX_URL environment variable is required.")
    if not config.plex_token:
        errors.append("PLEX_TOKEN environment variable is required.")

    feature_flags = [
        config.find_missing_thumbnail_previews,
        config.find_missing_voice_activity,
        config.find_missing_intro_markers,
        config.find_missing_credits_markers,
        config.find_missing_ad_markers,
    ]
    if not any(feature_flags):
        errors.append(
            "One of the following settings must be enabled: "
            "FIND_MISSING_THUMBNAIL_PREVIEWS, FIND_MISSING_VOICE_ACTIVITY, "
            "FIND_MISSING_INTRO_MARKERS, FIND_MISSING_CREDITS_MARKERS, "
            "FIND_MISSING_AD_MARKERS"
        )

    valid_library_types = ("movie", "show", "photo")
    for library_type in config.skip_library_types:
        if library_type not in valid_library_types:
            errors.append(
                f'Library type "{library_type}" invalid; '
                f'SKIP_LIBRARY_TYPES must be a comma-separated list of "movie", "show", or "photo".'
            )

    time_pattern = r"^(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?$"
    if config.run_time and not re.match(time_pattern, config.run_time):
        errors.append("RUN_TIME must be in the format HH:MM(:SS).")

    return errors


def setup_logging(
    debug: bool = False, log_directory: str = "/app/logs"
) -> logging.Logger:
    log_level = logging.DEBUG if debug else logging.INFO
    logger = logging.getLogger("preview_maid")
    logger.setLevel(log_level)
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if not os.path.exists(log_directory):
        logger.warning(
            f'Log directory "{log_directory}" does not exist, logs will only be output to console...'
        )
    else:
        log_file = os.path.join(log_directory, "preview_maid.log")
        file_handler = RotatingFileHandler(log_file, backupCount=5)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        if os.path.getsize(log_file) > 0:
            file_handler.doRollover()

        logger.info(
            "Since log file is being used, logs to the console will only show stats..."
        )
        logger.info(f'To see missing previews and voice data check "{log_file}"...')
        console_handler.addFilter(lambda record: record.levelno != logging.WARNING)

    return logger


# Plex Helper functions


def is_library_setting_enabled(library: object, setting_id: str) -> bool:
    for setting in library.settings():
        if setting.id == setting_id:
            return setting.value
    return False


def should_skip_library(
    library: object, config: Config, setting_id: str, logger: logging.Logger
) -> bool:
    if library.type in config.skip_library_types:
        logger.info(
            f"Skipping library {library.title} as {library.type} is in the SKIP_LIBRARY_TYPES list..."
        )
        return True
    if library.title in config.skip_library_names:
        logger.info(
            f"Skipping library {library.title} as {library.title} is in the SKIP_LIBRARY_NAMES list..."
        )
        return True
    if not is_library_setting_enabled(library, setting_id):
        logger.info(f"Skipping {library.title} as {setting_id} is disabled...")
        return True
    return False


# Preview Thumbnail Functions


def check_missing_preview_thumbnails_metadata(
    medias: list, logger: logging.Logger
) -> int:
    count = 0
    for media in medias:
        for part in media.parts:
            if not part.hasPreviewThumbnails:
                logger.warning(f"{part.file} is missing preview thumbnails")
                count += 1
    return count


def process_photos(album: object, logger: logging.Logger) -> int:
    count = 0
    for sub_album in album.albums():
        count += process_photos(sub_album, logger)
    for clip in album.clips():
        count += check_missing_preview_thumbnails_metadata(clip.media, logger)
    return count


def find_missing_preview_thumbnails(
    library: object, config: Config, logger: logging.Logger
) -> None:
    if should_skip_library(library, config, "enableBIFGeneration", logger):
        return
    logger.info(f"Processing library {library.title} of type {library.type}...")
    count = 0
    for item in library.all():
        if item.type == "show":
            for episode in item.episodes():
                count += check_missing_preview_thumbnails_metadata(
                    episode.media, logger
                )
        elif item.type == "movie":
            count += check_missing_preview_thumbnails_metadata(item.media, logger)
        elif item.type == "photo":
            count += process_photos(item, logger)
    if count > 0:
        logger.info(f"Found {count} missing preview thumbnails in {library.title}...")
    else:
        logger.info(f"No missing preview thumbnails found in {library.title}...")


# Voice Activity Functions


def check_missing_voice_activity_metadata(
    medias: list, media_data: str, logger: logging.Logger
) -> int:
    count = 0
    for media in medias:
        if not media.hasVoiceActivity:
            logger.warning(
                f'"{media_data}" for resolution {media.videoResolution} is missing voice activity data'
            )
            count += 1
    return count


def find_missing_voice_activity_data(
    library: object, config: Config, logger: logging.Logger
) -> None:
    if should_skip_library(library, config, "enableVoiceActivityGeneration", logger):
        return
    logger.info(f"Processing {library.title} of type {library.type}...")
    count = 0
    for item in library.all():
        if item.type == "show":
            for episode in item.episodes():
                media_data = f"{item.title} - {episode.title} (Season {episode.parentIndex}, Episode {episode.index})"
                count += check_missing_voice_activity_metadata(
                    episode.media, media_data, logger
                )
        elif item.type == "movie":
            count += check_missing_voice_activity_metadata(
                item.media, item.title, logger
            )
    if count > 0:
        logger.info(
            f"Found {count} files with missing voice activity in {library.title}..."
        )
    else:
        logger.info(f"No files are missing voice activity data in {library.title}...")


# Marker functions


def check_missing_marker_metadata(
    media: object, media_data: str, marker_type: str, logger: logging.Logger
) -> int:
    for marker in media.markers:
        if marker.type == marker_type:
            return 0
    logger.warning(f'"{media_data}" is missing {marker_type} markers')
    return 1


def find_missing_marker_metadata(
    library: object, config: Config, marker_type: str, logger: logging.Logger
) -> None:
    if should_skip_library(
        library, config, f"enable{marker_type.capitalize()}MarkerGeneration", logger
    ):
        return
    logger.info(f"Processing {library.title} of type {library.type}...")
    count = 0
    for item in library.all():
        if item.type == "show":
            for episode in item.episodes():
                media_data = f"{item.title} - {episode.title} (Season {episode.parentIndex}, Episode {episode.index})"
                count += check_missing_marker_metadata(
                    episode, media_data, marker_type, logger
                )
        elif item.type == "movie":
            count += check_missing_marker_metadata(
                item, item.title, marker_type, logger
            )
    if count > 0:
        logger.info(
            f"Found {count} files with missing {marker_type} markers in {library.title}..."
        )
    else:
        logger.info(f"No files are missing {marker_type} markers in {library.title}...")


# Main logic


def find_missing_metadata(config: Config, logger: logging.Logger) -> None:
    try:
        logger.info("Testing connection to Plex server...")
        plex = PlexServer(config.plex_url, config.plex_token, timeout=600)
        server_name = plex.friendlyName
        logger.info(f"Successfully connected to Plex server: {server_name}")
        start_time = datetime.now()

        libraries = plex.library.sections()
        scan_functions = {
            "find_missing_preview_thumbnails": find_missing_preview_thumbnails,
            "find_missing_voice_activity_data": find_missing_voice_activity_data,
            "find_missing_marker_metadata": find_missing_marker_metadata,
        }

        for feature in FEATURE_SCANS:
            if not getattr(config, feature.setting):
                continue
            logger.info(f"Searching for {feature.label}...")
            scan_fn = scan_functions[feature.scan_fn]
            for library in libraries:
                scan_fn(library, config, *feature.extra_args, logger)
            logger.info(f"{feature.label.capitalize()} run finished...")

        elapsed_time = datetime.now() - start_time
        logger.info(
            f"Run completed in {timedelta(seconds=elapsed_time.total_seconds())}, check the logs for results..."
        )
    except Exception as e:
        logger.error("Failed to connect to Plex server for this run...")
        logger.debug("An exception occurred: %s", e, exc_info=True)


def _handle_signal(signum: int, frame: object, logger: logging.Logger) -> None:
    logger.info("Received signal to terminate. Exiting...")
    sys.exit(0)


def main() -> None:
    config = load_config()
    logger = setup_logging(debug=config.debug, log_directory=config.log_directory)

    errors = validate_config(config)
    if errors:
        for error in errors:
            logger.error(error)
        sys.exit(1)

    signal.signal(signal.SIGTERM, lambda sig, frame: _handle_signal(sig, frame, logger))
    signal.signal(signal.SIGINT, lambda sig, frame: _handle_signal(sig, frame, logger))

    if config.run_once:
        logger.info("Preview Maid is running in one-time mode...")
        find_missing_metadata(config, logger)
        logger.info("Exiting since RUN_ONCE is set to True...")
        sys.exit(0)
    else:
        logger.info(f"Preview Maid is scheduled to run daily at {config.run_time}...")
        schedule.every().day.at(config.run_time).do(
            find_missing_metadata, config, logger
        )
        while True:
            schedule.run_pending()
            time.sleep(1)


if __name__ == "__main__":
    main()
