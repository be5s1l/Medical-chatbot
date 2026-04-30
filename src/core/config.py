from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

class Settings(BaseSettings):
    # Text generation (Gemini)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    log_level: str = "INFO"
    app_lang: Literal["en", "ar"] = "ar" # default language for the app if not specified
    # When true, API may return exception text in JSON `detail` (dev only; do not enable in public prod).
    app_debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

