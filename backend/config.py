"""
config.py — Application settings loaded from environment variables.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API keys (empty = use mock data)
    egen_api_key: str = ""
    kma_api_key: str = ""
    traffic_api_key: str = ""

    # Cache TTLs in seconds
    cache_ttl_egen: int = 60
    cache_ttl_kma: int = 300
    cache_ttl_traffic: int = 120

    # API base URLs
    egen_base_url: str = "https://apis.data.go.kr/B552657/ErmctInfoInqireService"
    kma_base_url: str = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"
    traffic_base_url: str = "https://apis.data.go.kr/B553077/api/open/sdpx"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def use_egen(self) -> bool:
        return bool(self.egen_api_key)

    @property
    def use_kma(self) -> bool:
        return bool(self.kma_api_key)

    @property
    def use_traffic(self) -> bool:
        return bool(self.traffic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
