from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    port: int = int(os.getenv("PORT", "8080"))
    google_api_key_present: bool = bool(os.getenv("GOOGLE_API_KEY"))
    google_genai_use_vertexai: str = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")
    service_name: str = os.getenv("SERVICE_NAME", "relieflink-hackathon")


def get_settings() -> Settings:
    return Settings()
