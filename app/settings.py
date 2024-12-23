from os import getenv
from pydantic import SecretStr
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: SecretStr = SecretStr(getenv('BOT_TOKEN'))
    MONGODB_URL: SecretStr = SecretStr(getenv('MONGODB_URL'))
    MONGODB_DB: SecretStr = SecretStr(getenv('MONGODB_DB'))
    OPENAI_KEY: SecretStr = SecretStr(getenv('OPENAI_KEY'))
    SENTRY_URL: SecretStr = SecretStr(getenv('SENTRY_URL'))
    SOCKS_PROXY: SecretStr = SecretStr(getenv('SOCKS_PROXY'))
    HTTP_PROXY: SecretStr = SecretStr(getenv('HTTP_PROXY'))

    GEMINI_API_KEY: SecretStr = SecretStr(getenv('GEMINI_API_KEY'))
    LOGGING_CHAT: str = getenv('LOGGING_CHAT')

    CHAT_COMPLETION_MAX_TOKENS: int = int(getenv('CHAT_COMPLETION_MAX_TOKENS'))
    CHAT_COMPLETION_TIMEOUT: int = int(getenv('CHAT_COMPLETION_TIMEOUT'))
    CHAT_COMPLETION_STREAM_INTERVAL: float = float(getenv('CHAT_COMPLETION_STREAM_INTERVAL'))
    DEFAULT_GPT_MODEL: str = getenv('DEFAULT_GPT_MODEL')
    DEFAULT_IMG_MODEL: str = getenv('DEFAULT_IMG_MODEL')

    YOOKASSA_ACCOUNT_ID: SecretStr = SecretStr(getenv('YOOKASSA_ACCOUNT_ID'))
    YOOKASSA_SECRET_KEY: SecretStr = SecretStr(getenv('YOOKASSA_SECRET_KEY'))
    DEFAULT_SUBSCRIPTION: str = getenv('DEFAULT_SUBSCRIPTION')

    FAL_AI_API_KEY: SecretStr = SecretStr(getenv('FAL_AI_API_KEY'))

SETTINGS = Settings()