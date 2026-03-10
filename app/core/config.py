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
    "MODEL_NAME": "openai/gpt-4o",
    "OPENAI_API_KEY": None,
    "ANTHROPIC_API_KEY": None,
    "GEMINI_API_KEY": None,
    "DEEPSEEK_API_KEY": None,
    "MISTRAL_API_KEY": None,
    "XAI_API_KEY": None,
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
MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-4o")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
XAI_API_KEY = os.getenv("XAI_API_KEY")

validate_env()
