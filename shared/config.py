"""
Centralized configuration management for Schoology Grade Scraper.
Loads non-sensitive settings from config.toml and credentials from .env files.
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv
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
    data_directory: str = "data"
    log_level: str = "INFO"
    max_retries: int = 3
    scrape_times: str = "21:00"  # Default fallback schedule


@dataclass
class LoggingConfig:
    """Logging behavior configuration."""
    enable_change_logging: bool = True
    change_log_retention_days: int = 90


@dataclass
class Config:
    """Master configuration container."""
    schoology: SchoologyConfig
    notifications: NotificationConfig
    app: AppConfig
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
        data_directory=toml_config.get('app', {}).get('data_directory', 'data'),
        log_level=toml_config.get('app', {}).get('log_level', 'INFO'),
        max_retries=toml_config.get('app', {}).get('max_retries', 3),
        scrape_times=os.getenv('SCRAPE_TIMES', '21:00')
    )
    
    logging_config = LoggingConfig(
        enable_change_logging=toml_config.get('logging', {}).get('enable_change_logging', True),
        change_log_retention_days=toml_config.get('logging', {}).get('change_log_retention_days', 90)
    )

    return Config(
        schoology=schoology_config,
        notifications=notification_config,
        app=app_config,
        logging=logging_config
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
