"""Configuration management for Chronicle."""

import os
from pathlib import Path
from typing import Optional
import yaml


class Config:
    """Chronicle configuration."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.

        Args:
            config_path: Path to config file. Defaults to ~/.ai-session/config.yaml
        """
        if config_path is None:
            home = Path.home()
            config_path = home / ".ai-session" / "config.yaml"

        self.config_path = Path(config_path)
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from file.

        Returns:
            Configuration dictionary
        """
        if not self.config_path.exists():
            return self._create_default_config()

        try:
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not load config from {self.config_path}: {e}")
            return {}

    def _create_default_config(self) -> dict:
        """Create default configuration file.

        Returns:
            Default configuration dictionary
        """
        default_config = {
            "repositories": [],
            "ai": {
                "gemini_api_key": None,
                "default_model": "gemini-2.5-flash-preview-09-2025",  # Latest model with separate 250/day quota
                "auto_summarize_sessions": False,
                "summarization_provider": "gemini",  # Default: Gemini with automatic model fallback
                "ollama_model": "qwen2.5:7b",  # Fallback for local processing
                "ollama_host": "http://localhost:11434",
            },
            "claude_code": {
                "current_provider": "anthropic",  # Current active provider
                "providers": {
                    "anthropic": {
                        "type": "oauth",
                        "description": "Official Anthropic Claude Code (OAuth)",
                    },
                    "zai": {
                        "type": "api_key",
                        "description": "Z.AI proxy (3x usage at lower cost)",
                        "api_key": None,
                        "base_url": "https://api.z.ai/api/anthropic",
                        "timeout_ms": 3000000,
                    },
                },
            },
            "retention": {
                "raw_data_days": 7,
                "summaries_days": 90,
            },
            "summarization": {
                "enabled": True,
                "max_summary_length": 500,
            },
            "remote_systems": {
                # Example:
                # "freebsd": {
                #     "hostname": "freebsd.example.com",
                #     "chronicle_path": "/usr/local/bin/chronicle",
                #     "user": "admin"  # Optional: defaults to current user
                # }
            },
        }

        # Create config directory if it doesn't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Write default config
        try:
            with open(self.config_path, "w") as f:
                yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
            print(f"✅ Created default config at {self.config_path}")
        except Exception as e:
            print(f"Warning: Could not create config file: {e}")

        return default_config

    def get(self, key: str, default=None):
        """Get configuration value.

        Args:
            key: Configuration key (supports dot notation, e.g. 'ai.gemini_api_key')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

            if value is None:
                return default

        return value

    def set(self, key: str, value):
        """Set configuration value.

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split(".")
        config = self._config

        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # Set the value
        config[keys[-1]] = value

        # Save to file
        self.save()

    def save(self):
        """Save configuration to file."""
        try:
            with open(self.config_path, "w") as f:
                yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            print(f"Warning: Could not save config: {e}")

    @property
    def gemini_api_key(self) -> Optional[str]:
        """Get Gemini API key.

        Checks in order:
        1. Environment variable GEMINI_API_KEY
        2. Config file ai.gemini_api_key

        Returns:
            Gemini API key or None
        """
        # Check environment variable first
        env_key = os.getenv("GEMINI_API_KEY")
        if env_key:
            return env_key

        # Check config file
        return self.get("ai.gemini_api_key")

    @property
    def default_model(self) -> str:
        """Get default Gemini model."""
        return self.get("ai.default_model", "gemini-2.0-flash-exp")

    @property
    def auto_summarize_sessions(self) -> bool:
        """Whether to auto-summarize sessions on exit."""
        return self.get("ai.auto_summarize_sessions", False)

    @property
    def summarization_provider(self) -> str:
        """Get summarization provider (gemini or ollama)."""
        return self.get("ai.summarization_provider", "gemini")

    @property
    def ollama_model(self) -> str:
        """Get Ollama model name."""
        return self.get("ai.ollama_model", "qwen2.5:32b")

    @property
    def ollama_host(self) -> str:
        """Get Ollama host URL."""
        return self.get("ai.ollama_host", "http://localhost:11434")

    @property
    def repositories(self) -> list:
        """Get list of tracked repositories."""
        return self.get("repositories", [])

    def add_repository(self, repo_path: str):
        """Add a repository to track.

        Args:
            repo_path: Path to repository
        """
        repos = self.repositories
        if repo_path not in repos:
            repos.append(repo_path)
            self.set("repositories", repos)

    # Claude Code provider management
    @property
    def current_claude_provider(self) -> str:
        """Get current Claude Code provider."""
        return self.get("claude_code.current_provider", "anthropic")

    def get_claude_provider(self, provider_name: str) -> Optional[dict]:
        """Get Claude provider configuration.

        Args:
            provider_name: Name of provider (anthropic, zai)

        Returns:
            Provider configuration dict or None
        """
        return self.get(f"claude_code.providers.{provider_name}")

    def list_claude_providers(self) -> dict:
        """Get all available Claude providers.

        Returns:
            Dictionary of provider configurations
        """
        return self.get("claude_code.providers", {})

    def set_claude_provider_api_key(self, provider_name: str, api_key: str):
        """Set API key for a Claude provider.

        Args:
            provider_name: Name of provider
            api_key: API key to set
        """
        self.set(f"claude_code.providers.{provider_name}.api_key", api_key)

    def set_current_claude_provider(self, provider_name: str):
        """Set current active Claude provider.

        Args:
            provider_name: Name of provider to activate
        """
        providers = self.list_claude_providers()
        if provider_name not in providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        self.set("claude_code.current_provider", provider_name)

    # Remote system management
    def get_remote_system(self, system_name: str) -> Optional[dict]:
        """Get remote system configuration.

        Args:
            system_name: Name of remote system (e.g., 'freebsd', 'linux')

        Returns:
            Remote system configuration dict or None
        """
        return self.get(f"remote_systems.{system_name}")

    def list_remote_systems(self) -> dict:
        """Get all configured remote systems.

        Returns:
            Dictionary of remote system configurations
        """
        return self.get("remote_systems", {})


# Global config instance
_config = None


def get_config() -> Config:
    """Get global config instance.

    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config()
    return _config
