import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("terrawise.config")


def _parse_origins(raw: str):
    if not raw:
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


class Settings:
    PORT: int = int(os.getenv("PORT", 8000))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    COPERNICUS_CLIENT_ID: str = os.getenv("COPERNICUS_CLIENT_ID", "")
    COPERNICUS_CLIENT_SECRET: str = os.getenv("COPERNICUS_CLIENT_SECRET", "")
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
    ALLOWED_ORIGINS: list = _parse_origins(os.getenv("ALLOWED_ORIGINS", ""))


settings = Settings()

# --- TEMPORARY DIAGNOSTIC LOGGING (Render weather fallback debug) ---
# Safe to remove once the fallback is confirmed working in production.
# Never logs the key value itself, only whether it is configured.
logger.info("[WEATHER-DIAG] OPENWEATHER_API_KEY configured: %s", bool(settings.OPENWEATHER_API_KEY))
