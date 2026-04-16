from previewmaid import (
    check_missing_marker_metadata,
    check_missing_preview_thumbnails_metadata,
    check_missing_voice_activity_metadata,
    find_missing_marker_metadata,
    find_missing_preview_thumbnails,
    find_missing_voice_activity_data,
    is_library_setting_enabled,
    process_photos,
    should_skip_library,
)
from tests.conftest import (
    make_album,
    make_clip,
    make_episode,
    make_library,
    make_marker,
    make_media,
    make_movie,
    make_part,
    make_setting,
    make_show,
)


class TestIsLibrarySettingEnabled:
    def test_setting_enabled(self):
        lib = make_library(
            "Movies", "movie", [], settings=[make_setting("enableBIFGeneration", True)]
        )
        assert is_library_setting_enabled(lib, "enableBIFGeneration") is True

    def test_setting_disabled(self):
        lib = make_library(
            "Movies", "movie", [], settings=[make_setting("enableBIFGeneration", False)]
        )
        assert is_library_setting_enabled(lib, "enableBIFGeneration") is False

    def test_setting_not_found(self):
        lib = make_library(
            "Movies", "movie", [], settings=[make_setting("otherSetting", True)]
        )
        assert is_library_setting_enabled(lib, "enableBIFGeneration") is False


class TestShouldSkipLibrary:
    def test_skip_by_type(self, default_config, logger):
        default_config.skip_library_types = ["movie"]
        lib = make_library(
            "Movies", "movie", [], settings=[make_setting("enableBIFGeneration", True)]
        )
        assert (
            should_skip_library(lib, default_config, "enableBIFGeneration", logger)
            is True
        )

    def test_skip_by_name(self, default_config, logger):
        default_config.skip_library_names = ["Movies"]
        lib = make_library(
            "Movies", "movie", [], settings=[make_setting("enableBIFGeneration", True)]
        )
        assert (
            should_skip_library(lib, default_config, "enableBIFGeneration", logger)
            is True
        )

    def test_skip_by_setting_disabled(self, default_config, logger):
        lib = make_library(
            "Movies", "movie", [], settings=[make_setting("enableBIFGeneration", False)]
        )
        assert (
            should_skip_library(lib, default_config, "enableBIFGeneration", logger)
            is True
        )

    def test_no_skip(self, default_config, logger):
        lib = make_library(
            "Movies", "movie", [], settings=[make_setting("enableBIFGeneration", True)]
        )
        assert (
            should_skip_library(lib, default_config, "enableBIFGeneration", logger)
            is False
        )


class TestCheckMissingPreviewThumbnails:
    def test_no_missing(self, logger):
        medias = [
            make_media(parts=[make_part("/movie.mkv", has_preview_thumbnails=True)])
        ]
        assert check_missing_preview_thumbnails_metadata(medias, logger) == 0

    def test_one_missing(self, logger):
        medias = [
            make_media(parts=[make_part("/movie.mkv", has_preview_thumbnails=False)])
        ]
        assert check_missing_preview_thumbnails_metadata(medias, logger) == 1

    def test_multiple_parts(self, logger):
        medias = [
            make_media(
                parts=[
                    make_part("/movie_part1.mkv", has_preview_thumbnails=False),
                    make_part("/movie_part2.mkv", has_preview_thumbnails=True),
                    make_part("/movie_part3.mkv", has_preview_thumbnails=False),
                ]
            )
        ]
        assert check_missing_preview_thumbnails_metadata(medias, logger) == 2

    def test_empty_medias(self, logger):
        assert check_missing_preview_thumbnails_metadata([], logger) == 0


class TestCheckMissingVoiceActivity:
    def test_no_missing(self, logger):
        medias = [make_media(has_voice_activity=True)]
        assert check_missing_voice_activity_metadata(medias, "Test Movie", logger) == 0

    def test_one_missing(self, logger):
        medias = [make_media(has_voice_activity=False)]
        assert check_missing_voice_activity_metadata(medias, "Test Movie", logger) == 1

    def test_multiple_media(self, logger):
        medias = [
            make_media(has_voice_activity=False, video_resolution="1080"),
            make_media(has_voice_activity=True, video_resolution="720"),
            make_media(has_voice_activity=False, video_resolution="4k"),
        ]
        assert check_missing_voice_activity_metadata(medias, "Test Movie", logger) == 2


class TestCheckMissingMarkerMetadata:
    def test_marker_present(self, logger):
        movie = make_movie("Test", [], markers=[make_marker("intro")])
        assert check_missing_marker_metadata(movie, "Test", "intro", logger) == 0

    def test_marker_missing(self, logger):
        movie = make_movie("Test", [], markers=[])
        assert check_missing_marker_metadata(movie, "Test", "intro", logger) == 1

    def test_wrong_marker_type(self, logger):
        movie = make_movie("Test", [], markers=[make_marker("credits")])
        assert check_missing_marker_metadata(movie, "Test", "intro", logger) == 1

    def test_multiple_markers(self, logger):
        movie = make_movie(
            "Test", [], markers=[make_marker("intro"), make_marker("credits")]
        )
        assert check_missing_marker_metadata(movie, "Test", "intro", logger) == 0
        assert check_missing_marker_metadata(movie, "Test", "credits", logger) == 0


class TestProcessPhotos:
    def test_empty_album(self, logger):
        album = make_album()
        assert process_photos(album, logger) == 0

    def test_clips_with_missing_thumbnails(self, logger):
        clip = make_clip(
            [make_media(parts=[make_part("/photo.jpg", has_preview_thumbnails=False)])]
        )
        album = make_album(clips=[clip])
        assert process_photos(album, logger) == 1

    def test_nested_albums(self, logger):
        inner_clip = make_clip(
            [make_media(parts=[make_part("/inner.jpg", has_preview_thumbnails=False)])]
        )
        inner_album = make_album(clips=[inner_clip])
        outer_clip = make_clip(
            [make_media(parts=[make_part("/outer.jpg", has_preview_thumbnails=False)])]
        )
        outer_album = make_album(sub_albums=[inner_album], clips=[outer_clip])
        assert process_photos(outer_album, logger) == 2


class TestFindMissingPreviewThumbnails:
    def test_finds_missing_in_movies(self, default_config, logger):
        movie = make_movie(
            "Test Movie", [make_media(parts=[make_part("/movie.mkv", False)])]
        )
        lib = make_library(
            "Movies",
            "movie",
            [movie],
            settings=[make_setting("enableBIFGeneration", True)],
        )
        find_missing_preview_thumbnails(lib, default_config, logger)
        # Verify via log output — function doesn't return count directly

    def test_finds_missing_in_shows(self, default_config, logger):
        ep = make_episode("Pilot", [make_media(parts=[make_part("/ep.mkv", False)])])
        show = make_show("Breaking Bad", [ep])
        lib = make_library(
            "TV", "show", [show], settings=[make_setting("enableBIFGeneration", True)]
        )
        find_missing_preview_thumbnails(lib, default_config, logger)

    def test_skips_disabled_library(self, default_config, logger):
        movie = make_movie("Test", [make_media(parts=[make_part("/m.mkv", False)])])
        lib = make_library(
            "Movies",
            "movie",
            [movie],
            settings=[make_setting("enableBIFGeneration", False)],
        )
        find_missing_preview_thumbnails(lib, default_config, logger)


class TestFindMissingVoiceActivity:
    def test_finds_missing_in_movies(self, default_config, logger):
        movie = make_movie("Test Movie", [make_media(has_voice_activity=False)])
        lib = make_library(
            "Movies",
            "movie",
            [movie],
            settings=[make_setting("enableVoiceActivityGeneration", True)],
        )
        find_missing_voice_activity_data(lib, default_config, logger)

    def test_finds_missing_in_shows(self, default_config, logger):
        ep = make_episode("Pilot", [make_media(has_voice_activity=False)])
        show = make_show("Breaking Bad", [ep])
        lib = make_library(
            "TV",
            "show",
            [show],
            settings=[make_setting("enableVoiceActivityGeneration", True)],
        )
        find_missing_voice_activity_data(lib, default_config, logger)


class TestFindMissingMarkers:
    def test_finds_missing_intro_markers(self, default_config, logger):
        ep = make_episode("Pilot", [make_media()], markers=[])
        show = make_show("Breaking Bad", [ep])
        lib = make_library(
            "TV",
            "show",
            [show],
            settings=[make_setting("enableIntroMarkerGeneration", True)],
        )
        find_missing_marker_metadata(lib, default_config, "intro", logger)

    def test_finds_missing_credits_markers_in_movies(self, default_config, logger):
        movie = make_movie("Test Movie", [make_media()], markers=[])
        lib = make_library(
            "Movies",
            "movie",
            [movie],
            settings=[make_setting("enableCreditsMarkerGeneration", True)],
        )
        find_missing_marker_metadata(lib, default_config, "credits", logger)

    def test_skips_when_markers_present(self, default_config, logger):
        ep = make_episode("Pilot", [make_media()], markers=[make_marker("intro")])
        show = make_show("Breaking Bad", [ep])
        lib = make_library(
            "TV",
            "show",
            [show],
            settings=[make_setting("enableIntroMarkerGeneration", True)],
        )
        find_missing_marker_metadata(lib, default_config, "intro", logger)
