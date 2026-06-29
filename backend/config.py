from functools import lru_cache
from pathlib import Path
import os

from pydantic import BaseModel


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseModel):
    app_name: str = "AI Recruiter Interview Assistant"
    database_url: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'backend' / 'data' / 'app.sqlite3'}"
    )
    upload_dir: Path = Path(
        os.getenv("UPLOAD_DIR", str(PROJECT_ROOT / "uploads" / "analysis"))
    )
    cors_origins: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
        if origin.strip()
    ]
    demo_user_email: str = os.getenv("DEMO_USER_EMAIL", "demo@ai-recruiter.local")
    demo_user_name: str = os.getenv("DEMO_USER_NAME", "Demo Recruiter")
    ai_provider: str = os.getenv("AI_PROVIDER", "deterministic")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    if settings.database_url.startswith("sqlite:///"):
        db_path = Path(settings.database_url.replace("sqlite:///", ""))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    return settings

