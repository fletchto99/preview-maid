from unittest.mock import MagicMock, patch


from previewmaid import Config, find_missing_metadata, setup_logging
from conftest import (
    make_library,
    make_media,
    make_movie,
    make_part,
    make_setting,
)


class TestFindMissingMetadata:
    def test_full_scan_with_missing_thumbnails(self, default_config, logger):
        movie = make_movie(
            "Test Movie", [make_media(parts=[make_part("/movie.mkv", False)])]
        )
        lib = make_library(
            "Movies",
            "movie",
            [movie],
            settings=[make_setting("enableBIFGeneration", True)],
        )

        mock_plex = MagicMock()
        mock_plex.friendlyName = "Test Server"
        mock_plex.library.sections.return_value = [lib]

        with patch("previewmaid.PlexServer", return_value=mock_plex):
            find_missing_metadata(default_config, logger)

    def test_connection_failure(self, default_config, logger):
        with patch(
            "previewmaid.PlexServer", side_effect=Exception("Connection refused")
        ):
            find_missing_metadata(default_config, logger)

    def test_all_features_enabled(self, logger):
        config = Config(
            plex_url="http://localhost:32400",
            plex_token="test",
            find_missing_thumbnail_previews=True,
            find_missing_voice_activity=True,
            find_missing_intro_markers=True,
            find_missing_credits_markers=True,
            find_missing_ad_markers=True,
            run_once=True,
            run_time="00:00",
        )
        movie = make_movie(
            "Test Movie",
            [make_media(parts=[make_part("/m.mkv", True)], has_voice_activity=True)],
            markers=[],
        )
        lib = make_library(
            "Movies",
            "movie",
            [movie],
            settings=[
                make_setting("enableBIFGeneration", True),
                make_setting("enableVoiceActivityGeneration", True),
                make_setting("enableIntroMarkerGeneration", True),
                make_setting("enableCreditsMarkerGeneration", True),
                make_setting("enableAdMarkerGeneration", True),
            ],
        )

        mock_plex = MagicMock()
        mock_plex.friendlyName = "Test Server"
        mock_plex.library.sections.return_value = [lib]

        with patch("previewmaid.PlexServer", return_value=mock_plex):
            find_missing_metadata(config, logger)

    def test_empty_library(self, default_config, logger):
        lib = make_library(
            "Movies", "movie", [], settings=[make_setting("enableBIFGeneration", True)]
        )

        mock_plex = MagicMock()
        mock_plex.friendlyName = "Test Server"
        mock_plex.library.sections.return_value = [lib]

        with patch("previewmaid.PlexServer", return_value=mock_plex):
            find_missing_metadata(default_config, logger)


class TestSetupLogging:
    def test_console_only(self, tmp_path):
        logger = setup_logging(debug=False, log_directory=str(tmp_path / "nonexistent"))
        assert logger.name == "preview_maid"
        assert len(logger.handlers) == 1

    def test_with_file_logging(self, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        (log_dir / "preview_maid.log").touch()
        logger = setup_logging(debug=False, log_directory=str(log_dir))
        assert len(logger.handlers) == 2

    def test_debug_mode(self, tmp_path):
        logger = setup_logging(debug=True, log_directory=str(tmp_path / "nonexistent"))
        assert logger.level == 10  # DEBUG

    def test_idempotent(self, tmp_path):
        log_dir = str(tmp_path / "nonexistent")
        setup_logging(debug=False, log_directory=log_dir)
        logger = setup_logging(debug=False, log_directory=log_dir)
        assert len(logger.handlers) == 1
