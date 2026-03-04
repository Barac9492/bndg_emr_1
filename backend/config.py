"""
config.py — Application settings with enhanced validation and security.
"""

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API keys (empty = use mock data)
    egen_api_key: str = Field("", description="E-Gen API key")
    kma_api_key: str = Field("", description="KMA weather API key")  
    traffic_api_key: str = Field("", description="Traffic API key")

    # Cache TTLs in seconds
    cache_ttl_egen: int = Field(60, ge=30, le=3600)
    cache_ttl_kma: int = Field(300, ge=60, le=3600)
    cache_ttl_traffic: int = Field(120, ge=30, le=3600)

    # API base URLs
    egen_base_url: str = "https://apis.data.go.kr/B552657/ErmctInfoInqireService"
    kma_base_url: str = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"
    traffic_base_url: str = "https://apis.data.go.kr/B553077/api/open/sdpx"

    # Security settings
    max_requests_per_minute: int = Field(100, ge=10, le=1000)
    enable_debug: bool = Field(False, description="Enable debug mode")
    
    # Environment
    environment: str = Field("development", regex="^(development|staging|production)$")

    model_config = {
        "env_file": ".env", 
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }

    @validator('egen_api_key', 'kma_api_key', 'traffic_api_key')
    def validate_api_keys(cls, v: str) -> str:
        if v and len(v) < 10:
            raise ValueError("API key too short")
        return v

    @property
    def use_egen(self) -> bool:
        return bool(self.egen_api_key)

    @property
    def use_kma(self) -> bool:
        return bool(self.kma_api_key)

    @property
    def use_traffic(self) -> bool:
        return bool(self.traffic_api_key)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()