"""Tests for configuration management."""

import os
import tempfile
from pathlib import Path
import pytest

from backend.core.config import Config


@pytest.fixture
def temp_config():
    """Create a temporary config file for testing."""
    # Create a temp file path but don't create the file yet
    # This allows Config to create it with default config
    temp_dir = tempfile.mkdtemp()
    config_path = Path(temp_dir) / "config.yaml"

    config = Config(config_path=str(config_path))

    yield config

    # Cleanup
    if config_path.exists():
        config_path.unlink()
    Path(temp_dir).rmdir()


# ============================================================================
# Remote System Configuration Tests
# ============================================================================

def test_default_config_includes_remote_systems(temp_config):
    """Default config should include empty remote_systems section."""
    remote_systems = temp_config.get("remote_systems", None)
    assert remote_systems is not None
    assert isinstance(remote_systems, dict)


def test_set_remote_system_hostname(temp_config):
    """Can set remote system hostname."""
    temp_config.set("remote_systems.freebsd.hostname", "freebsd.example.com")

    hostname = temp_config.get("remote_systems.freebsd.hostname")
    assert hostname == "freebsd.example.com"


def test_set_remote_system_chronicle_path(temp_config):
    """Can set remote system Chronicle path."""
    temp_config.set("remote_systems.freebsd.chronicle_path", "/usr/local/bin/chronicle")

    path = temp_config.get("remote_systems.freebsd.chronicle_path")
    assert path == "/usr/local/bin/chronicle"


def test_set_multiple_remote_systems(temp_config):
    """Can configure multiple remote systems."""
    temp_config.set("remote_systems.freebsd.hostname", "freebsd.example.com")
    temp_config.set("remote_systems.freebsd.chronicle_path", "/usr/local/bin/chronicle")

    temp_config.set("remote_systems.linux.hostname", "linux.example.com")
    temp_config.set("remote_systems.linux.chronicle_path", "/home/user/.local/bin/chronicle")

    freebsd_host = temp_config.get("remote_systems.freebsd.hostname")
    linux_host = temp_config.get("remote_systems.linux.hostname")

    assert freebsd_host == "freebsd.example.com"
    assert linux_host == "linux.example.com"


def test_get_remote_system_config(temp_config):
    """Can get full remote system config."""
    temp_config.set("remote_systems.freebsd.hostname", "freebsd.example.com")
    temp_config.set("remote_systems.freebsd.chronicle_path", "/usr/local/bin/chronicle")
    temp_config.set("remote_systems.freebsd.user", "admin")

    freebsd_config = temp_config.get_remote_system("freebsd")

    assert freebsd_config is not None
    assert freebsd_config["hostname"] == "freebsd.example.com"
    assert freebsd_config["chronicle_path"] == "/usr/local/bin/chronicle"
    assert freebsd_config["user"] == "admin"


def test_get_remote_system_nonexistent(temp_config):
    """Getting non-existent remote system returns None."""
    result = temp_config.get_remote_system("nonexistent")
    assert result is None


def test_list_remote_systems(temp_config):
    """Can list all configured remote systems."""
    temp_config.set("remote_systems.freebsd.hostname", "freebsd.example.com")
    temp_config.set("remote_systems.linux.hostname", "linux.example.com")

    systems = temp_config.list_remote_systems()

    assert isinstance(systems, dict)
    assert "freebsd" in systems
    assert "linux" in systems
    assert systems["freebsd"]["hostname"] == "freebsd.example.com"
    assert systems["linux"]["hostname"] == "linux.example.com"


def test_list_remote_systems_empty(temp_config):
    """List remote systems returns empty dict when none configured."""
    systems = temp_config.list_remote_systems()
    assert systems == {}


def test_remote_system_config_persists(temp_config):
    """Remote system config persists after save/reload."""
    temp_config.set("remote_systems.freebsd.hostname", "freebsd.example.com")
    temp_config.set("remote_systems.freebsd.chronicle_path", "/usr/local/bin/chronicle")
    temp_config.save()

    # Reload config from same file
    reloaded_config = Config(config_path=temp_config.config_path)

    hostname = reloaded_config.get("remote_systems.freebsd.hostname")
    path = reloaded_config.get("remote_systems.freebsd.chronicle_path")

    assert hostname == "freebsd.example.com"
    assert path == "/usr/local/bin/chronicle"


# ============================================================================
# Existing Configuration Tests (to ensure we don't break anything)
# ============================================================================

def test_get_with_dot_notation(temp_config):
    """Config.get() supports dot notation."""
    temp_config.set("ai.gemini_api_key", "test_key_123")

    result = temp_config.get("ai.gemini_api_key")
    assert result == "test_key_123"


def test_get_with_default(temp_config):
    """Config.get() returns default for non-existent keys."""
    result = temp_config.get("nonexistent.key", "default_value")
    assert result == "default_value"


def test_set_creates_nested_dict(temp_config):
    """Config.set() creates nested dictionaries as needed."""
    temp_config.set("deeply.nested.key", "value")

    result = temp_config.get("deeply.nested.key")
    assert result == "value"


def test_config_file_created(temp_config):
    """Config file is created on disk."""
    assert temp_config.config_path.exists()
