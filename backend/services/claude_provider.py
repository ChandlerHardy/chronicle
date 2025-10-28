"""Claude Code provider switcher service."""

import json
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime


class ClaudeProviderSwitcher:
    """Manages switching between Claude Code providers."""

    def __init__(self, settings_path: Optional[Path] = None):
        """Initialize provider switcher.

        Args:
            settings_path: Path to Claude settings.json. Defaults to ~/.claude/settings.json
        """
        if settings_path is None:
            settings_path = Path.home() / ".claude" / "settings.json"

        self.settings_path = settings_path
        self.backup_dir = self.settings_path.parent / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _load_settings(self) -> dict:
        """Load current Claude settings.

        Returns:
            Settings dictionary
        """
        if not self.settings_path.exists():
            return {}

        try:
            with open(self.settings_path, "r") as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load settings from {self.settings_path}: {e}")

    def _save_settings(self, settings: dict):
        """Save Claude settings.

        Args:
            settings: Settings dictionary to save
        """
        # Ensure directory exists
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.settings_path, "w") as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed to save settings to {self.settings_path}: {e}")

    def backup_current_settings(self) -> Path:
        """Create a timestamped backup of current settings.

        Returns:
            Path to backup file
        """
        if not self.settings_path.exists():
            # No settings to backup
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"settings_{timestamp}.json"

        try:
            shutil.copy2(self.settings_path, backup_path)
            return backup_path
        except Exception as e:
            raise RuntimeError(f"Failed to backup settings: {e}")

    def restore_from_backup(self, backup_path: Path):
        """Restore settings from a backup.

        Args:
            backup_path: Path to backup file
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        try:
            shutil.copy2(backup_path, self.settings_path)
        except Exception as e:
            raise RuntimeError(f"Failed to restore from backup: {e}")

    def list_backups(self) -> list[Path]:
        """List all available backups.

        Returns:
            List of backup file paths, sorted by date (newest first)
        """
        backups = list(self.backup_dir.glob("settings_*.json"))
        return sorted(backups, reverse=True)

    def get_current_provider_type(self) -> str:
        """Detect current provider type from settings.

        Returns:
            "anthropic" if using OAuth, "zai" if using Z.AI, "unknown" otherwise
        """
        settings = self._load_settings()

        # Check for env object first (new format)
        env = settings.get("env", {})
        if env:
            base_url = env.get("ANTHROPIC_BASE_URL", "")
            if "z.ai" in base_url:
                return "zai"
            if env.get("ANTHROPIC_AUTH_TOKEN") or env.get("ANTHROPIC_BASE_URL"):
                return "custom"

        # Fallback to root-level settings (old format)
        base_url = settings.get("ANTHROPIC_BASE_URL", "")
        if "z.ai" in base_url:
            return "zai"

        # If ANTHROPIC_AUTH_TOKEN or ANTHROPIC_BASE_URL exists but not Z.AI, it's custom
        if settings.get("ANTHROPIC_AUTH_TOKEN") or settings.get("ANTHROPIC_BASE_URL"):
            return "custom"

        # Default is Anthropic OAuth
        return "anthropic"

    def switch_to_anthropic(self):
        """Switch to Anthropic OAuth provider.

        Removes Z.AI-specific settings, relying on Claude's built-in OAuth.
        """
        # Backup first
        self.backup_current_settings()

        # Load current settings
        settings = self._load_settings()

        # Remove the entire env object to clean up all custom provider settings
        settings.pop("env", None)

        # Also remove any direct root-level settings that might exist
        settings.pop("ANTHROPIC_AUTH_TOKEN", None)
        settings.pop("ANTHROPIC_BASE_URL", None)
        settings.pop("API_TIMEOUT_MS", None)

        # Save cleaned settings
        self._save_settings(settings)

    def switch_to_zai(self, api_key: str, base_url: str = "https://api.z.ai/api/anthropic", timeout_ms: int = 3000000):
        """Switch to Z.AI provider.

        Args:
            api_key: Z.AI API key
            base_url: Z.AI API base URL
            timeout_ms: API timeout in milliseconds
        """
        if not api_key:
            raise ValueError("Z.AI API key is required")

        # Backup first
        self.backup_current_settings()

        # Load current settings
        settings = self._load_settings()

        # Add Z.AI settings under env key
        if "env" not in settings:
            settings["env"] = {}

        settings["env"]["ANTHROPIC_AUTH_TOKEN"] = api_key
        settings["env"]["ANTHROPIC_BASE_URL"] = base_url
        settings["env"]["API_TIMEOUT_MS"] = str(timeout_ms)  # Must be string per Z.AI docs

        # Also add the model settings for GLM models
        settings["env"]["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = "glm-4.5-air"
        settings["env"]["ANTHROPIC_DEFAULT_SONNET_MODEL"] = "glm-4.6"
        settings["env"]["ANTHROPIC_DEFAULT_OPUS_MODEL"] = "glm-4.6"

        # Remove any direct root-level settings that might conflict
        settings.pop("ANTHROPIC_AUTH_TOKEN", None)
        settings.pop("ANTHROPIC_BASE_URL", None)
        settings.pop("API_TIMEOUT_MS", None)

        # Save updated settings
        self._save_settings(settings)

    def switch_to_custom(self, api_key: str, base_url: str, timeout_ms: Optional[int] = None):
        """Switch to a custom provider.

        Args:
            api_key: Custom provider API key
            base_url: Custom provider base URL
            timeout_ms: Optional API timeout in milliseconds
        """
        if not api_key or not base_url:
            raise ValueError("Both API key and base URL are required for custom provider")

        # Backup first
        self.backup_current_settings()

        # Load current settings
        settings = self._load_settings()

        # Add custom settings
        settings["ANTHROPIC_AUTH_TOKEN"] = api_key
        settings["ANTHROPIC_BASE_URL"] = base_url

        if timeout_ms:
            settings["API_TIMEOUT_MS"] = str(timeout_ms)
        else:
            settings.pop("API_TIMEOUT_MS", None)

        # Save updated settings
        self._save_settings(settings)

    def get_current_settings_info(self) -> dict:
        """Get information about current settings.

        Returns:
            Dictionary with current provider info
        """
        settings = self._load_settings()
        provider_type = self.get_current_provider_type()

        info = {
            "provider_type": provider_type,
            "settings_path": str(self.settings_path),
            "has_backup": len(self.list_backups()) > 0,
        }

        # Check for env object first (new format)
        env = settings.get("env", {})
        if env:
            if provider_type == "zai":
                info["base_url"] = env.get("ANTHROPIC_BASE_URL")
                info["has_api_key"] = bool(env.get("ANTHROPIC_AUTH_TOKEN"))
            elif provider_type == "custom":
                info["base_url"] = env.get("ANTHROPIC_BASE_URL")
                info["has_api_key"] = bool(env.get("ANTHROPIC_AUTH_TOKEN"))
        else:
            # Fallback to root-level settings (old format)
            if provider_type == "zai":
                info["base_url"] = settings.get("ANTHROPIC_BASE_URL")
                info["has_api_key"] = bool(settings.get("ANTHROPIC_AUTH_TOKEN"))
            elif provider_type == "custom":
                info["base_url"] = settings.get("ANTHROPIC_BASE_URL")
                info["has_api_key"] = bool(settings.get("ANTHROPIC_AUTH_TOKEN"))

        return info
