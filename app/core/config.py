import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "SECRET_KEY",
    "ENCRYPTION_KEY",
]

OPTIONAL_ENV_VARS = {
    "MODEL_NAME": "groq/llama-3.3-70b-versatile",
    "GOOGLE_API_KEY": None,
    "GEMINI_API_KEY": None,
    "GROQ_API_KEY": None,
    "MINMAX_API_KEY": None,
    "OPENROUTER_API_KEY": None,
}


class ConfigurationError(Exception):
    pass


def validate_env() -> None:
    missing_vars = []
    for var in REQUIRED_ENV_VARS:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)

    if missing_vars:
        raise ConfigurationError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(key, default)


DATABASE_URL = os.getenv("DATABASE_URL", "")
SECRET_KEY = os.getenv("SECRET_KEY", "")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "groq/llama-3.3-70b-versatile")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MINMAX_API_KEY = os.getenv("MINMAX_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

validate_env()
