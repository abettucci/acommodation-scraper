"""Configuration management for Lambda functions."""

import os
import json
import boto3
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional


@dataclass
class Config:
    """Application configuration loaded from environment variables."""
    
    environment: str
    project_name: str
    google_places_secret_arn: str
    telegram_secret_arn: str
    
    # Cached secrets
    _google_api_key: Optional[str] = None
    _telegram_token: Optional[str] = None
    
    @property
    def google_api_key(self) -> str:
        """Get Google Places API key from Secrets Manager."""
        if self._google_api_key is None:
            self._google_api_key = self._get_secret(self.google_places_secret_arn)
        return self._google_api_key
    
    @property
    def telegram_token(self) -> str:
        """Get Telegram Bot token from Secrets Manager."""
        if self._telegram_token is None:
            self._telegram_token = self._get_secret(self.telegram_secret_arn)
        return self._telegram_token
    
    def _get_secret(self, secret_arn: str) -> str:
        """Retrieve secret value from AWS Secrets Manager."""
        client = boto3.client('secretsmanager')
        response = client.get_secret_value(SecretId=secret_arn)
        
        # Handle both string and JSON secrets
        secret = response.get('SecretString', '')
        try:
            secret_dict = json.loads(secret)
            # Return first value if it's a dict
            return list(secret_dict.values())[0] if secret_dict else secret
        except json.JSONDecodeError:
            return secret


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Get cached configuration instance."""
    return Config(
        environment=os.environ.get('ENVIRONMENT', 'dev'),
        project_name=os.environ.get('PROJECT_NAME', 'accommodation-scraper'),
        google_places_secret_arn=os.environ.get('GOOGLE_PLACES_SECRET_ARN', ''),
        telegram_secret_arn=os.environ.get('TELEGRAM_SECRET_ARN', ''),
    )
