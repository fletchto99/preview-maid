from previewmaid import load_config, validate_config, parse_bool_env


class TestParseBoolEnv:
    def test_true_values(self, monkeypatch):
        for val in ("True", "true", "1", "t", "TRUE", "T"):
            monkeypatch.setenv("TEST_BOOL", val)
            assert parse_bool_env("TEST_BOOL") is True

    def test_false_values(self, monkeypatch):
        for val in ("False", "false", "0", "f", "no", ""):
            monkeypatch.setenv("TEST_BOOL", val)
            assert parse_bool_env("TEST_BOOL") is False

    def test_default_value(self, monkeypatch):
        monkeypatch.delenv("TEST_BOOL", raising=False)
        assert parse_bool_env("TEST_BOOL") is False
        assert parse_bool_env("TEST_BOOL", "True") is True


class TestLoadConfig:
    def test_loads_defaults(self, monkeypatch):
        monkeypatch.delenv("PLEX_URL", raising=False)
        monkeypatch.delenv("PLEX_TOKEN", raising=False)
        monkeypatch.delenv("SKIP_LIBRARY_TYPES", raising=False)
        monkeypatch.delenv("SKIP_LIBRARY_NAMES", raising=False)
        monkeypatch.delenv("DEBUG", raising=False)
        monkeypatch.delenv("RUN_ONCE", raising=False)
        monkeypatch.delenv("RUN_TIME", raising=False)
        monkeypatch.delenv("FIND_MISSING_THUMBNAIL_PREVIEWS", raising=False)
        monkeypatch.delenv("FIND_MISSING_VOICE_ACTIVITY", raising=False)
        monkeypatch.delenv("FIND_MISSING_INTRO_MARKERS", raising=False)
        monkeypatch.delenv("FIND_MISSING_CREDITS_MARKERS", raising=False)
        monkeypatch.delenv("FIND_MISSING_AD_MARKERS", raising=False)

        config = load_config()
        assert config.plex_url == ""
        assert config.plex_token == ""
        assert config.find_missing_thumbnail_previews is True
        assert config.find_missing_voice_activity is False
        assert config.run_once is False
        assert config.run_time == "00:00"
        assert config.skip_library_types == []
        assert config.skip_library_names == []

    def test_loads_env_values(self, monkeypatch):
        monkeypatch.setenv("PLEX_URL", "http://plex:32400")
        monkeypatch.setenv("PLEX_TOKEN", "abc123")
        monkeypatch.setenv("FIND_MISSING_VOICE_ACTIVITY", "True")
        monkeypatch.setenv("RUN_ONCE", "1")
        monkeypatch.setenv("RUN_TIME", "03:30")
        monkeypatch.setenv("SKIP_LIBRARY_TYPES", "movie,photo")
        monkeypatch.setenv("SKIP_LIBRARY_NAMES", "Music,  Audiobooks ")

        config = load_config()
        assert config.plex_url == "http://plex:32400"
        assert config.plex_token == "abc123"
        assert config.find_missing_voice_activity is True
        assert config.run_once is True
        assert config.run_time == "03:30"
        assert config.skip_library_types == ["movie", "photo"]
        assert config.skip_library_names == ["Music", "Audiobooks"]

    def test_strips_whitespace_from_lists(self, monkeypatch):
        monkeypatch.setenv("SKIP_LIBRARY_TYPES", " movie , show ")
        monkeypatch.setenv("SKIP_LIBRARY_NAMES", "")
        config = load_config()
        assert config.skip_library_types == ["movie", "show"]
        assert config.skip_library_names == []


class TestValidateConfig:
    def test_valid_config(self, default_config):
        errors = validate_config(default_config)
        assert errors == []

    def test_missing_plex_url(self, default_config):
        default_config.plex_url = ""
        errors = validate_config(default_config)
        assert any("PLEX_URL" in e for e in errors)

    def test_missing_plex_token(self, default_config):
        default_config.plex_token = ""
        errors = validate_config(default_config)
        assert any("PLEX_TOKEN" in e for e in errors)

    def test_no_features_enabled(self, default_config):
        default_config.find_missing_thumbnail_previews = False
        errors = validate_config(default_config)
        assert any("must be enabled" in e for e in errors)

    def test_invalid_library_type(self, default_config):
        default_config.skip_library_types = ["movie", "invalid"]
        errors = validate_config(default_config)
        assert any('"invalid" invalid' in e for e in errors)

    def test_valid_library_types(self, default_config):
        default_config.skip_library_types = ["movie", "show", "photo"]
        errors = validate_config(default_config)
        assert errors == []

    def test_invalid_run_time(self, default_config):
        default_config.run_time = "25:00"
        errors = validate_config(default_config)
        assert any("RUN_TIME" in e for e in errors)

    def test_valid_run_time_with_seconds(self, default_config):
        default_config.run_time = "14:30:45"
        errors = validate_config(default_config)
        assert errors == []

    def test_multiple_errors(self, default_config):
        default_config.plex_url = ""
        default_config.plex_token = ""
        default_config.find_missing_thumbnail_previews = False
        default_config.run_time = "invalid"
        errors = validate_config(default_config)
        assert len(errors) == 4
