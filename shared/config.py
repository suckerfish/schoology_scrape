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
    google_email: str
    google_password: str
    base_url: str = "https://lvjusd.schoology.com/"


@dataclass  
class AWSConfig:
    """AWS-specific configuration."""
    access_key_id: str
    secret_access_key: str
    region: str = "us-west-1"
    dynamodb_table_name: str = "SchoologyGrades"


@dataclass
class NotificationConfig:
    """Notification service configuration."""
    pushover_token: Optional[str] = None
    pushover_user_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    email_enabled: bool = True


@dataclass
class AppConfig:
    """Application-level configuration."""
    download_path: str = "."
    data_directory: str = "data"
    log_level: str = "INFO"
    cache_ttl_seconds: int = 300  # 5 minutes
    max_retries: int = 3
    retry_delay_seconds: int = 2


@dataclass
class Config:
    """Master configuration container."""
    schoology: SchoologyConfig
    aws: AWSConfig
    notifications: NotificationConfig
    app: AppConfig
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_required_fields()
    
    def _validate_required_fields(self):
        """Validate that all required configuration is present."""
        errors = []
        
        # Schoology validation
        if not self.schoology.google_email:
            errors.append("Missing required config: schoology.google_email")
        if not self.schoology.google_password:
            errors.append("Missing required config: schoology.google_password")
            
        # AWS validation
        if not self.aws.access_key_id:
            errors.append("Missing required config: aws.access_key_id")
        if not self.aws.secret_access_key:
            errors.append("Missing required config: aws.secret_access_key")
            
        if errors:
            raise ValueError(f"Configuration validation failed:\n" + "\n".join(errors))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return {
            "schoology": {
                "google_email": self.schoology.google_email,
                "base_url": self.schoology.base_url,
                # Note: Password intentionally excluded from serialization
            },
            "aws": {
                "region": self.aws.region,
                "dynamodb_table_name": self.aws.dynamodb_table_name,
                # Note: Credentials intentionally excluded from serialization
            },
            "notifications": {
                "pushover_enabled": bool(self.notifications.pushover_token),
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
        google_email=os.getenv('evan_google', ''),
        google_password=os.getenv('evan_google_pw', ''),
        base_url=toml_config.get('schoology', {}).get('base_url', 'https://lvjusd.schoology.com/')
    )
    
    aws_config = AWSConfig(
        access_key_id=os.getenv('aws_key', ''),
        secret_access_key=os.getenv('aws_secret', ''),
        region=toml_config.get('aws', {}).get('region', 'us-west-1'),
        dynamodb_table_name=toml_config.get('aws', {}).get('dynamodb_table_name', 'SchoologyGrades')
    )
    
    notification_config = NotificationConfig(
        pushover_token=os.getenv('pushover_token'),
        pushover_user_key=os.getenv('pushover_userkey'),
        gemini_api_key=os.getenv('gemini_key'),
        email_enabled=toml_config.get('notifications', {}).get('email_enabled', True)
    )
    
    app_config = AppConfig(
        download_path=toml_config.get('app', {}).get('download_path', '.'),
        data_directory=toml_config.get('app', {}).get('data_directory', 'data'),
        log_level=toml_config.get('app', {}).get('log_level', 'INFO'),
        cache_ttl_seconds=toml_config.get('app', {}).get('cache_ttl_seconds', 300),
        max_retries=toml_config.get('app', {}).get('max_retries', 3),
        retry_delay_seconds=toml_config.get('app', {}).get('retry_delay_seconds', 2)
    )
    
    return Config(
        schoology=schoology_config,
        aws=aws_config,
        notifications=notification_config,
        app=app_config
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
        print("✅ Configuration loaded successfully")
        print(f"📧 Schoology Email: {config.schoology.google_email}")
        print(f"🗄️  DynamoDB Table: {config.aws.dynamodb_table_name}")
        print(f"📱 Pushover Enabled: {bool(config.notifications.pushover_token)}")
        print(f"🤖 Gemini Enabled: {bool(config.notifications.gemini_api_key)}")
        print(f"📊 Cache TTL: {config.app.cache_ttl_seconds}s")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")