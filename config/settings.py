from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_provider: str = Field("groq", alias="LLM_PROVIDER")
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    mistral_api_key: str | None = Field(default=None, alias="MISTRAL_API_KEY")
    ollama_url: str = Field("http://localhost:11434", alias="OLLAMA_URL")
    database_url: str = Field("sqlite:///./audit_mvp.db", alias="DATABASE_URL")
    max_file_size_mb: int = Field(50, alias="MAX_FILE_SIZE_MB")
    upload_dir: str = Field("uploads", alias="UPLOAD_DIR")
    output_dir: str = Field("outputs", alias="OUTPUT_DIR")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
