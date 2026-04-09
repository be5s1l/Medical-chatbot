from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    huggingface_token: str = ""
    chroma_db_path: str = "./data/chroma_db"
    tesseract_path: str = "C:/Program Files/Tesseract-OCR/tesseract.exe"
    log_level: str = "DEBUG"
    emergency_keywords: str = "chest pain,stroke,unconscious"
    # LLM backend selection
    llm_provider: str = "openai"  # openai | ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"
    # When true, API may return exception text in JSON `detail` (dev only; do not enable in public prod).
    app_debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def emergency_keywords_list(self) -> list[str]:
        return [k.strip().lower() for k in self.emergency_keywords.split(",") if k.strip()]


settings = Settings()

