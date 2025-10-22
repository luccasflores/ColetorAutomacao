from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    user_agent: str = os.getenv("USER_AGENT", "companies-scraper/0.1 (+https://github.com/luccasflores)")
    max_concurrency: int = int(os.getenv("MAX_CONCURRENCY", "4"))
    delay_ms_min: int = int(os.getenv("REQUEST_DELAY_MS_MIN", "300"))
    delay_ms_max: int = int(os.getenv("REQUEST_DELAY_MS_MAX", "900"))
    timeout_ms: int = int(os.getenv("TIMEOUT_MS", "30000"))

SETTINGS = Settings()
