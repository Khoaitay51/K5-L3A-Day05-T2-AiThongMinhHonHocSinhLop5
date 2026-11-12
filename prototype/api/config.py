import os
from dotenv import load_dotenv

# Search for .env in current dir and parent dirs
load_dotenv(".env")
load_dotenv("/app/.env")
load_dotenv("../.env")
load_dotenv("../../.env")

class Settings:
    @property
    def GEMINI_API_KEY(self) -> str:
        # Load from .env with override=True to pick up any changes in .env file
        if os.path.exists(".env"):
            load_dotenv(".env", override=True)
        if os.path.exists("/app/.env"):
            load_dotenv("/app/.env", override=True)
        return os.getenv("GEMINI_API_KEY", "")

    @property
    def GEMINI_MODEL(self) -> str:
        return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    @property
    def EMBEDDING_MODEL(self) -> str:
        return os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")

    @property
    def POSTGRES_USER(self) -> str:
        return os.getenv("POSTGRES_USER", "postgres")

    @property
    def POSTGRES_PASSWORD(self) -> str:
        return os.getenv("POSTGRES_PASSWORD", "postgres")

    @property
    def POSTGRES_DB(self) -> str:
        return os.getenv("POSTGRES_DB", "study_t2_db")

    @property
    def POSTGRES_HOST(self) -> str:
        return os.getenv("POSTGRES_HOST", "db")

    @property
    def POSTGRES_PORT(self) -> int:
        return int(os.getenv("POSTGRES_PORT", "5432"))

    @property
    def API_PORT(self) -> int:
        return int(os.getenv("API_PORT", "8000"))

    @property
    def DEBUG(self) -> bool:
        return os.getenv("DEBUG", "True").lower() in ("true", "1")

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()

