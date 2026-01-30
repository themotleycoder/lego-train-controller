"""
Configuration management for LEGO Train Controller service.

Uses Pydantic Settings for type-safe environment variable loading.
All configuration can be overridden via environment variables or .env file.
"""
import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host address")
    port: int = Field(default=8000, description="Server port")

    # Security Configuration
    api_keys: str = Field(
        default="",
        description="Comma-separated list of valid API keys"
    )
    allowed_origins: str = Field(
        default="*",
        description="Comma-separated list of allowed CORS origins"
    )

    @property
    def api_keys_list(self) -> List[str]:
        """Parse API keys as list."""
        if not self.api_keys:
            return []
        return [key.strip() for key in self.api_keys.split(",") if key.strip()]

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse allowed origins as list."""
        if not self.allowed_origins:
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
    require_auth: bool = Field(
        default=True,
        description="Require API key authentication for all endpoints"
    )

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    log_format: str = Field(default="json", description="Log format (json or text)")
    log_file: Optional[str] = Field(default=None, description="Log file path (None for stdout only)")

    # Bluetooth Configuration
    bluetooth_reset_on_startup: bool = Field(
        default=True,
        description="Reset Bluetooth adapter on service startup"
    )
    max_train_connections: int = Field(default=10, description="Maximum number of simultaneous train connections")
    max_switch_connections: int = Field(default=10, description="Maximum number of simultaneous switch connections")

    # LEGO Hub Constants
    lego_service_uuid: str = Field(
        default="00001623-1212-efde-1623-785feabcd123",
        description="LEGO Hub BLE service UUID"
    )
    lego_char_uuid: str = Field(
        default="00001624-1212-efde-1623-785feabcd123",
        description="LEGO Hub BLE characteristic UUID"
    )
    lego_manufacturer_id: int = Field(default=919, description="LEGO manufacturer ID for BLE advertising")

    # Timing Configuration
    status_update_interval: float = Field(
        default=0.1,
        description="Status polling interval in seconds for active devices"
    )
    inactive_device_threshold: float = Field(
        default=5.0,
        description="Time in seconds before marking device as inactive"
    )
    command_retry_delay: float = Field(
        default=0.5,
        description="Base delay in seconds between command retries"
    )
    max_command_retries: int = Field(default=3, description="Maximum number of command retry attempts")

    # Validation Ranges
    power_min: int = Field(default=-100, description="Minimum train power value")
    power_max: int = Field(default=100, description="Maximum train power value")
    valid_switch_names: str = Field(
        default="A,B,C,D",
        description="Valid switch name letters (comma-separated)"
    )
    valid_switch_positions: str = Field(
        default="STRAIGHT,DIVERGING",
        description="Valid switch positions (comma-separated)"
    )

    @property
    def valid_switch_names_list(self) -> List[str]:
        """Parse valid switch names as list."""
        return [name.strip() for name in self.valid_switch_names.split(",") if name.strip()]

    @property
    def valid_switch_positions_list(self) -> List[str]:
        """Parse valid switch positions as list."""
        return [pos.strip() for pos in self.valid_switch_positions.split(",") if pos.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get the global settings instance.

    Returns:
        Settings: The application settings
    """
    return settings
