"""
Configuration module for Samantha CLI.
Loads settings from environment variables and .env files.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for Samantha CLI."""
    
    # NLP Service Configuration
    NLP_SERVICE_URL: str = os.getenv(
        "NLP_SERVICE_URL", 
        "http://localhost:8000"
    )
    
    # CLI Configuration
    CLI_TIMEOUT: float = float(os.getenv(
        "CLI_TIMEOUT", 
        "30.0"
    ))
    
    CLI_LOG_LEVEL: str = os.getenv(
        "CLI_LOG_LEVEL", 
        "INFO"
    )
    
    # Application Configuration
    APP_NAME: str = os.getenv(
        "APP_NAME", 
        "Samantha CLI"
    )
    
    APP_VERSION: str = os.getenv(
        "APP_VERSION", 
        "1.0.0"
    )
    
    @classmethod
    def get_nlp_service_url(cls) -> str:
        """Get the NLP service URL."""
        return cls.NLP_SERVICE_URL
    
    @classmethod
    def get_cli_timeout(cls) -> float:
        """Get the CLI timeout in seconds."""
        return cls.CLI_TIMEOUT
    
    @classmethod
    def get_cli_log_level(cls) -> str:
        """Get the CLI log level."""
        return cls.CLI_LOG_LEVEL
    
    @classmethod
    def get_app_name(cls) -> str:
        """Get the application name."""
        return cls.APP_NAME
    
    @classmethod
    def get_app_version(cls) -> str:
        """Get the application version."""
        return cls.APP_VERSION

# Global configuration instance
config = Config()
