"""Tests for Claude Code provider switcher service."""

import json
import tempfile
import pytest
from pathlib import Path
from datetime import datetime

from backend.services.claude_provider import ClaudeProviderSwitcher


@pytest.fixture
def temp_settings_dir():
    """Create a temporary .claude directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings_path = Path(tmpdir) / "settings.json"
        yield settings_path


@pytest.fixture
def switcher(temp_settings_dir):
    """Create ClaudeProviderSwitcher with temporary settings."""
    return ClaudeProviderSwitcher(temp_settings_dir)


# ============================================================================
# Provider Type Detection Tests
# ============================================================================


def test_get_current_provider_type_returns_anthropic_by_default(switcher):
    """When settings file doesn't exist, provider should default to anthropic."""
    provider_type = switcher.get_current_provider_type()
    assert provider_type == "anthropic"


def test_get_current_provider_type_detects_zai_from_base_url(switcher):
    """When ANTHROPIC_BASE_URL contains z.ai, provider should be detected as zai."""
    # Arrange
    settings = {
        "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
        "ANTHROPIC_AUTH_TOKEN": "test_token",
    }
    switcher._save_settings(settings)

    # Act
    provider_type = switcher.get_current_provider_type()

    # Assert
    assert provider_type == "zai"


def test_get_current_provider_type_detects_custom_provider(switcher):
    """When ANTHROPIC_BASE_URL is set but not z.ai, provider should be detected as custom."""
    # Arrange
    settings = {
        "ANTHROPIC_BASE_URL": "https://custom.api.com/v1",
        "ANTHROPIC_AUTH_TOKEN": "custom_token",
    }
    switcher._save_settings(settings)

    # Act
    provider_type = switcher.get_current_provider_type()

    # Assert
    assert provider_type == "custom"


def test_get_current_provider_type_detects_custom_with_auth_token_only(switcher):
    """When only ANTHROPIC_AUTH_TOKEN is set (without base URL), provider should be custom."""
    # Arrange
    settings = {"ANTHROPIC_AUTH_TOKEN": "custom_token"}
    switcher._save_settings(settings)

    # Act
    provider_type = switcher.get_current_provider_type()

    # Assert
    assert provider_type == "custom"


# ============================================================================
# Switch to Anthropic Tests
# ============================================================================


def test_switch_to_anthropic_removes_all_custom_settings(switcher):
    """Switching to anthropic should remove Z.AI and custom provider settings."""
    # Arrange
    settings = {
        "ANTHROPIC_AUTH_TOKEN": "z_ai_token",
        "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
        "API_TIMEOUT_MS": "3000000",
        "other_setting": "should_remain",
    }
    switcher._save_settings(settings)

    # Act
    switcher.switch_to_anthropic()

    # Assert
    loaded_settings = switcher._load_settings()
    assert "ANTHROPIC_AUTH_TOKEN" not in loaded_settings
    assert "ANTHROPIC_BASE_URL" not in loaded_settings
    assert "API_TIMEOUT_MS" not in loaded_settings
    assert loaded_settings["other_setting"] == "should_remain"


def test_switch_to_anthropic_creates_backup(switcher):
    """Switching to anthropic should create a timestamped backup."""
    # Arrange
    settings = {"ANTHROPIC_AUTH_TOKEN": "token"}
    switcher._save_settings(settings)
    initial_backup_count = len(switcher.list_backups())

    # Act
    switcher.switch_to_anthropic()

    # Assert
    backups = switcher.list_backups()
    assert len(backups) == initial_backup_count + 1


def test_switch_to_anthropic_idempotent(switcher):
    """Switching to anthropic twice should produce same result."""
    # Arrange
    settings = {
        "ANTHROPIC_AUTH_TOKEN": "token",
        "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
    }
    switcher._save_settings(settings)

    # Act
    switcher.switch_to_anthropic()
    first_settings = switcher._load_settings()
    switcher.switch_to_anthropic()
    second_settings = switcher._load_settings()

    # Assert
    assert first_settings == second_settings
    assert switcher.get_current_provider_type() == "anthropic"


def test_switch_to_anthropic_with_empty_settings(switcher):
    """Switching to anthropic when no settings exist should not raise error."""
    # Act & Assert (should not raise)
    switcher.switch_to_anthropic()
    assert switcher.get_current_provider_type() == "anthropic"


# ============================================================================
# Switch to Z.AI Tests
# ============================================================================


def test_switch_to_zai_requires_api_key(switcher):
    """Switching to Z.AI without API key should raise ValueError."""
    # Act & Assert
    with pytest.raises(ValueError, match="Z.AI API key is required"):
        switcher.switch_to_zai(api_key=None)

    with pytest.raises(ValueError, match="Z.AI API key is required"):
        switcher.switch_to_zai(api_key="")


def test_switch_to_zai_sets_correct_configuration(switcher):
    """Switching to Z.AI should set correct auth token, base URL, and timeout."""
    # Act
    switcher.switch_to_zai(api_key="test_zai_key")

    # Assert
    settings = switcher._load_settings()
    assert settings["ANTHROPIC_AUTH_TOKEN"] == "test_zai_key"
    assert settings["ANTHROPIC_BASE_URL"] == "https://api.z.ai/api/anthropic"
    assert settings["API_TIMEOUT_MS"] == "3000000"
    assert switcher.get_current_provider_type() == "zai"


def test_switch_to_zai_with_custom_base_url(switcher):
    """Switching to Z.AI should accept custom base URL."""
    # Act
    custom_url = "https://custom.z.ai.mirror/api/anthropic"
    switcher.switch_to_zai(api_key="test_key", base_url=custom_url)

    # Assert
    settings = switcher._load_settings()
    assert settings["ANTHROPIC_BASE_URL"] == custom_url


def test_switch_to_zai_with_custom_timeout(switcher):
    """Switching to Z.AI should accept custom timeout."""
    # Act
    switcher.switch_to_zai(api_key="test_key", timeout_ms=5000000)

    # Assert
    settings = switcher._load_settings()
    assert settings["API_TIMEOUT_MS"] == "5000000"


def test_switch_to_zai_creates_backup(switcher):
    """Switching to Z.AI should create a timestamped backup."""
    # Arrange
    switcher._save_settings({"existing": "setting"})
    initial_backup_count = len(switcher.list_backups())

    # Act
    switcher.switch_to_zai(api_key="test_key")

    # Assert
    backups = switcher.list_backups()
    assert len(backups) == initial_backup_count + 1


def test_switch_to_zai_preserves_other_settings(switcher):
    """Switching to Z.AI should preserve non-provider settings."""
    # Arrange
    settings = {
        "user_preference": "value",
        "theme": "dark",
        "ANTHROPIC_AUTH_TOKEN": "old_token",
    }
    switcher._save_settings(settings)

    # Act
    switcher.switch_to_zai(api_key="new_token")

    # Assert
    loaded_settings = switcher._load_settings()
    assert loaded_settings["user_preference"] == "value"
    assert loaded_settings["theme"] == "dark"


# ============================================================================
# Switch to Custom Provider Tests
# ============================================================================


def test_switch_to_custom_requires_api_key_and_url(switcher):
    """Switching to custom provider requires both API key and base URL."""
    # Act & Assert
    with pytest.raises(ValueError, match="Both API key and base URL are required"):
        switcher.switch_to_custom(api_key="key", base_url=None)

    with pytest.raises(ValueError, match="Both API key and base URL are required"):
        switcher.switch_to_custom(api_key=None, base_url="https://custom.api")

    with pytest.raises(ValueError, match="Both API key and base URL are required"):
        switcher.switch_to_custom(api_key="", base_url="https://custom.api")


def test_switch_to_custom_sets_correct_configuration(switcher):
    """Switching to custom provider should set API key and base URL."""
    # Act
    custom_url = "https://custom.llm.provider/v1"
    switcher.switch_to_custom(api_key="custom_key", base_url=custom_url)

    # Assert
    settings = switcher._load_settings()
    assert settings["ANTHROPIC_AUTH_TOKEN"] == "custom_key"
    assert settings["ANTHROPIC_BASE_URL"] == custom_url
    assert switcher.get_current_provider_type() == "custom"


def test_switch_to_custom_with_optional_timeout(switcher):
    """Switching to custom provider should accept optional timeout."""
    # Act
    switcher.switch_to_custom(
        api_key="custom_key",
        base_url="https://custom.api",
        timeout_ms=10000000
    )

    # Assert
    settings = switcher._load_settings()
    assert settings["API_TIMEOUT_MS"] == "10000000"


def test_switch_to_custom_without_timeout_removes_existing(switcher):
    """Switching to custom without timeout should remove existing timeout setting."""
    # Arrange
    settings = {
        "ANTHROPIC_AUTH_TOKEN": "old_token",
        "ANTHROPIC_BASE_URL": "https://old.api",
        "API_TIMEOUT_MS": "5000000",
    }
    switcher._save_settings(settings)

    # Act
    switcher.switch_to_custom(
        api_key="new_key",
        base_url="https://new.api",
        timeout_ms=None
    )

    # Assert
    loaded_settings = switcher._load_settings()
    assert "API_TIMEOUT_MS" not in loaded_settings
    assert loaded_settings["ANTHROPIC_AUTH_TOKEN"] == "new_key"


# ============================================================================
# Backup and Restore Tests
# ============================================================================


def test_backup_current_settings_creates_timestamped_file(switcher):
    """Creating backup should create a file with timestamp in name."""
    # Arrange
    settings = {"test": "settings"}
    switcher._save_settings(settings)

    # Act
    backup_path = switcher.backup_current_settings()

    # Assert
    assert backup_path is not None
    assert backup_path.exists()
    assert "settings_" in backup_path.name
    assert backup_path.name.endswith(".json")


def test_backup_current_settings_returns_none_when_no_settings(switcher):
    """Backing up when settings file doesn't exist should return None."""
    # Act
    backup_path = switcher.backup_current_settings()

    # Assert
    assert backup_path is None


def test_backup_preserves_exact_content(switcher):
    """Backup should be an exact copy of settings file."""
    # Arrange
    settings = {
        "ANTHROPIC_AUTH_TOKEN": "test_token",
        "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
        "nested": {"key": "value", "number": 42},
    }
    switcher._save_settings(settings)

    # Act
    backup_path = switcher.backup_current_settings()

    # Assert
    with open(backup_path, "r") as f:
        backup_content = json.load(f)
    assert backup_content == settings


def test_restore_from_backup_overwrites_current_settings(switcher):
    """Restoring from backup should overwrite current settings."""
    # Arrange
    original_settings = {"setting1": "value1"}
    switcher._save_settings(original_settings)
    backup_path = switcher.backup_current_settings()

    # Change settings
    new_settings = {"setting2": "value2"}
    switcher._save_settings(new_settings)

    # Act
    switcher.restore_from_backup(backup_path)

    # Assert
    restored_settings = switcher._load_settings()
    assert restored_settings == original_settings


def test_restore_from_backup_raises_if_file_not_found(switcher):
    """Restoring from non-existent backup should raise FileNotFoundError."""
    # Arrange
    non_existent_backup = Path("/tmp/non_existent_backup_12345.json")

    # Act & Assert
    with pytest.raises(FileNotFoundError, match="Backup file not found"):
        switcher.restore_from_backup(non_existent_backup)


def test_list_backups_returns_sorted_by_date_newest_first(switcher):
    """List backups should return files sorted by date, newest first."""
    import time

    # Arrange
    switcher._save_settings({"test": "1"})
    backup1 = switcher.backup_current_settings()
    time.sleep(1.1)  # Ensure different timestamp

    switcher._save_settings({"test": "2"})
    backup2 = switcher.backup_current_settings()
    time.sleep(1.1)  # Ensure different timestamp

    switcher._save_settings({"test": "3"})
    backup3 = switcher.backup_current_settings()

    # Act
    backups = switcher.list_backups()

    # Assert
    assert len(backups) == 3
    assert backups[0] == backup3  # Newest first
    assert backups[1] == backup2
    assert backups[2] == backup1  # Oldest last


def test_list_backups_returns_empty_when_no_backups(switcher):
    """List backups should return empty list when no backups exist."""
    # Act
    backups = switcher.list_backups()

    # Assert
    assert backups == []


def test_backup_directory_created_automatically(switcher):
    """Backup directory should be created automatically during initialization."""
    # The backup directory is created in __init__ to ensure it exists
    # before any backup operations are performed.
    # This is a defensive practice to catch permission issues early.

    # Assert
    assert switcher.backup_dir.exists()


# ============================================================================
# Settings I/O Tests
# ============================================================================


def test_load_settings_returns_empty_dict_when_file_missing(switcher):
    """Loading settings when file doesn't exist should return empty dict."""
    # Act
    settings = switcher._load_settings()

    # Assert
    assert settings == {}


def test_load_settings_handles_corrupted_json(switcher):
    """Loading corrupted JSON should raise RuntimeError."""
    # Arrange
    switcher.settings_path.parent.mkdir(parents=True, exist_ok=True)
    with open(switcher.settings_path, "w") as f:
        f.write("{corrupted json")

    # Act & Assert
    with pytest.raises(RuntimeError, match="Failed to load settings"):
        switcher._load_settings()


def test_save_settings_creates_parent_directories(switcher):
    """Save settings should create parent directories if needed."""
    # Arrange
    new_settings_path = switcher.settings_path.parent / "subdir" / "settings.json"
    switcher.settings_path = new_settings_path
    assert not new_settings_path.parent.exists()

    # Act
    switcher._save_settings({"test": "settings"})

    # Assert
    assert new_settings_path.exists()
    assert new_settings_path.parent.exists()


def test_save_settings_pretty_prints_json(switcher):
    """Saved JSON should be indented for readability."""
    # Arrange
    settings = {"key1": "value1", "key2": {"nested": "value"}}

    # Act
    switcher._save_settings(settings)

    # Assert
    with open(switcher.settings_path, "r") as f:
        content = f.read()
    assert "\n" in content  # Should have newlines from indentation
    assert "  " in content  # Should have indentation


# ============================================================================
# Get Current Settings Info Tests
# ============================================================================


def test_get_current_settings_info_for_anthropic_provider(switcher):
    """Getting settings info for Anthropic provider should only include provider_type."""
    # Arrange
    switcher._save_settings({})  # Empty settings = Anthropic

    # Act
    info = switcher.get_current_settings_info()

    # Assert
    assert info["provider_type"] == "anthropic"
    assert "settings_path" in info
    assert "has_backup" in info


def test_get_current_settings_info_for_zai_provider(switcher):
    """Getting settings info for Z.AI provider should include base_url and has_api_key."""
    # Arrange
    switcher.switch_to_zai(api_key="test_key")

    # Act
    info = switcher.get_current_settings_info()

    # Assert
    assert info["provider_type"] == "zai"
    assert info["base_url"] == "https://api.z.ai/api/anthropic"
    assert info["has_api_key"] is True


def test_get_current_settings_info_masks_api_key(switcher):
    """Settings info should not expose the actual API key."""
    # Arrange
    switcher.switch_to_zai(api_key="secret_api_key_12345")

    # Act
    info = switcher.get_current_settings_info()

    # Assert
    assert "secret_api_key_12345" not in str(info)
    assert info["has_api_key"] is True  # Only indicates presence


def test_get_current_settings_info_for_custom_provider(switcher):
    """Getting settings info for custom provider should include provider details."""
    # Arrange
    switcher.switch_to_custom(
        api_key="custom_key",
        base_url="https://custom.api/v1"
    )

    # Act
    info = switcher.get_current_settings_info()

    # Assert
    assert info["provider_type"] == "custom"
    assert info["base_url"] == "https://custom.api/v1"
    assert info["has_api_key"] is True


# ============================================================================
# Integration Tests
# ============================================================================


def test_switching_between_providers_maintains_backup_history(switcher):
    """Switching between providers should maintain complete backup history."""
    import time

    # Arrange
    switcher._save_settings({"initial": "state"})

    # Act - switch to Z.AI
    switcher.switch_to_zai(api_key="zai_key")
    backup_count_after_zai = len(switcher.list_backups())
    time.sleep(1.1)  # Ensure different timestamp

    # Switch to custom
    switcher.switch_to_custom(api_key="custom_key", base_url="https://custom.api")
    backup_count_after_custom = len(switcher.list_backups())
    time.sleep(1.1)  # Ensure different timestamp

    # Switch back to Anthropic
    switcher.switch_to_anthropic()
    final_backup_count = len(switcher.list_backups())

    # Assert
    assert backup_count_after_zai == 1
    assert backup_count_after_custom == 2
    assert final_backup_count == 3


def test_complete_workflow_switch_and_restore(switcher):
    """Test complete workflow: set Anthropic → switch to Z.AI → restore."""
    # Arrange - Start with Anthropic
    initial_settings = {"user_settings": "preserved"}
    switcher._save_settings(initial_settings)
    initial_provider = switcher.get_current_provider_type()

    # Act - Switch to Z.AI
    switcher.switch_to_zai(api_key="zai_key")
    zai_provider = switcher.get_current_provider_type()
    backup_for_restore = switcher.list_backups()[0]

    # Switch back
    switcher.restore_from_backup(backup_for_restore)
    restored_provider = switcher.get_current_provider_type()
    restored_settings = switcher._load_settings()

    # Assert
    assert initial_provider == "anthropic"
    assert zai_provider == "zai"
    assert restored_provider == "anthropic"
    assert restored_settings["user_settings"] == "preserved"
