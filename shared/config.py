"""
Centralized configuration management for Schoology Grade Scraper.
Loads non-sensitive settings from config.toml and credentials from .env files.
"""
import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import logging
import sys

# Handle Python version compatibility for TOML
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass
class SchoologyConfig:
    """Schoology-specific configuration."""
    api_key: Optional[str] = None
    api_secret: Optional[str] = None


@dataclass
class NotificationConfig:
    """Notification service configuration."""
    gemini_api_key: Optional[str] = None
    email_enabled: bool = True
    email_sender: Optional[str] = None
    email_password: Optional[str] = None
    email_receiver: Optional[str] = None


@dataclass
class AppConfig:
    """Application-level configuration."""
    download_path: str = "."
    data_directory: str = "data"
    log_level: str = "INFO"
    cache_ttl_seconds: int = 300  # 5 minutes
    max_retries: int = 3
    retry_delay_seconds: int = 2
    scrape_times: str = "21:00"  # Default fallback schedule


@dataclass
class StorageConfig:
    """Storage behavior configuration."""
    conditional_save: bool = True      # Only save data when changes are detected
    force_save_on_error: bool = True   # Fail-safe: save data if change detection fails


@dataclass
class LoggingConfig:
    """Logging behavior configuration."""
    enable_change_logging: bool = True
    enable_raw_diff_logging: bool = False  # Debug only - can generate large files
    change_log_retention_days: int = 90
    raw_diff_log_retention_days: int = 7


@dataclass
class Config:
    """Master configuration container."""
    schoology: SchoologyConfig
    notifications: NotificationConfig
    app: AppConfig
    storage: StorageConfig
    logging: LoggingConfig
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_required_fields()
    
    def _validate_required_fields(self):
        """Validate that all required configuration is present."""
        errors = []

        # Schoology validation - require API credentials
        if not (self.schoology.api_key and self.schoology.api_secret):
            errors.append("Missing Schoology API credentials: provide SCHOOLOGY_API_KEY and SCHOOLOGY_API_SECRET")

        if errors:
            raise ValueError(f"Configuration validation failed:\n" + "\n".join(errors))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return {
            "schoology": {
                "api_enabled": bool(self.schoology.api_key and self.schoology.api_secret),
            },
            "notifications": {
                "gemini_enabled": bool(self.notifications.gemini_api_key),
                "email_enabled": self.notifications.email_enabled,
            },
            "app": {
                "download_path": self.app.download_path,
                "data_directory": self.app.data_directory,
                "log_level": self.app.log_level,
                "cache_ttl_seconds": self.app.cache_ttl_seconds,
                "max_retries": self.app.max_retries,
                "retry_delay_seconds": self.app.retry_delay_seconds,
                "scrape_times": self.app.scrape_times,
            },
            "storage": {
                "conditional_save": self.storage.conditional_save,
                "force_save_on_error": self.storage.force_save_on_error,
            },
            "logging": {
                "enable_change_logging": self.logging.enable_change_logging,
                "enable_raw_diff_logging": self.logging.enable_raw_diff_logging,
                "change_log_retention_days": self.logging.change_log_retention_days,
                "raw_diff_log_retention_days": self.logging.raw_diff_log_retention_days,
            }
        }


def load_config(env_file: Optional[str] = None, config_file: str = "config.toml") -> Config:
    """
    Load configuration from TOML file and environment variables.
    
    Args:
        env_file: Optional path to .env file. If None, uses default discovery.
        config_file: Path to TOML configuration file.
        
    Returns:
        Validated Config instance.
        
    Raises:
        ValueError: If required configuration is missing or invalid.
        FileNotFoundError: If config.toml file is not found.
    """
    # Load environment variables (for sensitive credentials)
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()  # Auto-discover .env file
    
    # Load TOML configuration file (for non-sensitive settings)
    try:
        with open(config_file, 'rb') as f:
            toml_config = tomllib.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file '{config_file}' not found. Please create it with application settings.")
    except Exception as e:
        raise ValueError(f"Failed to parse TOML configuration file '{config_file}': {e}")
    
    # Build configuration from TOML + environment variables
    schoology_config = SchoologyConfig(
        api_key=os.getenv('SCHOOLOGY_API_KEY'),
        api_secret=os.getenv('SCHOOLOGY_API_SECRET'),
    )
    
    notification_config = NotificationConfig(
        gemini_api_key=os.getenv('gemini_key'),
        email_enabled=toml_config.get('notifications', {}).get('email_enabled', True),
        email_sender=os.getenv('email_sender'),
        email_password=os.getenv('email_password'),
        email_receiver=os.getenv('email_receiver')
    )
    
    app_config = AppConfig(
        download_path=toml_config.get('app', {}).get('download_path', '.'),
        data_directory=toml_config.get('app', {}).get('data_directory', 'data'),
        log_level=toml_config.get('app', {}).get('log_level', 'INFO'),
        cache_ttl_seconds=toml_config.get('app', {}).get('cache_ttl_seconds', 300),
        max_retries=toml_config.get('app', {}).get('max_retries', 3),
        retry_delay_seconds=toml_config.get('app', {}).get('retry_delay_seconds', 2),
        scrape_times=os.getenv('SCRAPE_TIMES', '21:00')
    )
    
    storage_config = StorageConfig(
        conditional_save=toml_config.get('storage', {}).get('conditional_save', True),
        force_save_on_error=toml_config.get('storage', {}).get('force_save_on_error', True)
    )

    logging_config = LoggingConfig(
        enable_change_logging=toml_config.get('logging', {}).get('enable_change_logging', True),
        enable_raw_diff_logging=toml_config.get('logging', {}).get('enable_raw_diff_logging', False),
        change_log_retention_days=toml_config.get('logging', {}).get('change_log_retention_days', 90),
        raw_diff_log_retention_days=toml_config.get('logging', {}).get('raw_diff_log_retention_days', 7)
    )

    return Config(
        schoology=schoology_config,
        notifications=notification_config,
        app=app_config,
        storage=storage_config,
        logging=logging_config
    )


def setup_logging(config: Config) -> None:
    """Configure logging based on configuration."""
    logging.basicConfig(
        level=getattr(logging, config.app.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/application.log', mode='a')
        ]
    )


# Global configuration instance (lazy-loaded)
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """
    Get the global configuration instance.
    Loads configuration on first access.
    
    Returns:
        Global Config instance.
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = load_config()
    return _config_instance


def reset_config() -> None:
    """Reset the global configuration instance. Useful for testing."""
    global _config_instance
    _config_instance = None


if __name__ == "__main__":
    # Test configuration loading
    try:
        config = load_config()
        print("Configuration loaded successfully")
        print(f"Gemini Enabled: {bool(config.notifications.gemini_api_key)}")
        print(f"Cache TTL: {config.app.cache_ttl_seconds}s")
        print(f"Conditional Save: {config.storage.conditional_save}")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")