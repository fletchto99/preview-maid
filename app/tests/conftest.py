import logging
from types import SimpleNamespace

import pytest

from previewmaid import Config


@pytest.fixture
def default_config():
    return Config(
        plex_url="http://localhost:32400",
        plex_token="test-token",
        find_missing_thumbnail_previews=True,
        find_missing_voice_activity=False,
        find_missing_intro_markers=False,
        find_missing_credits_markers=False,
        find_missing_ad_markers=False,
        run_once=True,
        run_time="00:00",
        skip_library_types=[],
        skip_library_names=[],
        debug=False,
    )


@pytest.fixture
def logger():
    log = logging.getLogger("test_preview_maid")
    log.handlers.clear()
    log.setLevel(logging.DEBUG)
    return log


def make_part(file_path, has_preview_thumbnails=True):
    part = SimpleNamespace()
    part.file = file_path
    part.hasPreviewThumbnails = has_preview_thumbnails
    return part


def make_media(parts=None, has_voice_activity=True, video_resolution="1080"):
    media = SimpleNamespace()
    media.parts = parts or []
    media.hasVoiceActivity = has_voice_activity
    media.videoResolution = video_resolution
    return media


def make_marker(marker_type):
    marker = SimpleNamespace()
    marker.type = marker_type
    return marker


def make_episode(title, media, markers=None, parent_index=1, index=1):
    ep = SimpleNamespace()
    ep.type = "episode"
    ep.title = title
    ep.media = media
    ep.markers = markers or []
    ep.parentIndex = parent_index
    ep.index = index
    return ep


def make_show(title, episodes):
    show = SimpleNamespace()
    show.type = "show"
    show.title = title
    show.episodes = lambda: episodes
    return show


def make_movie(title, media, markers=None):
    movie = SimpleNamespace()
    movie.type = "movie"
    movie.title = title
    movie.media = media
    movie.markers = markers or []
    return movie


def make_library(title, lib_type, items, settings=None):
    lib = SimpleNamespace()
    lib.type = lib_type
    lib.title = title
    lib.all = lambda: items
    lib.settings = lambda: settings or []
    return lib


def make_setting(setting_id, value=True):
    setting = SimpleNamespace()
    setting.id = setting_id
    setting.value = value
    return setting


def make_album(sub_albums=None, clips=None):
    album = SimpleNamespace()
    album.albums = lambda: sub_albums or []
    album.clips = lambda: clips or []
    return album


def make_clip(media):
    clip = SimpleNamespace()
    clip.media = media
    return clip
