from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Text generation (Groq)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Vision (Gemini) — used ONLY for image description
    gemini_api_key: str = ""
    vision_model: str = "models/gemini-2.5-flash-image"

    # OCR
    tesseract_path: str = "C:/Program Files/Tesseract-OCR/tesseract.exe"

    log_level: str = "DEBUG"
    # When true, API may return exception text in JSON `detail` (dev only; do not enable in public prod).
    app_debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

