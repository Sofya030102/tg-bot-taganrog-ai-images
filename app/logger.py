import logging
import sentry_sdk

from sys import stdout
from logging import DEBUG, INFO, WARN, ERROR, FATAL
from logging import basicConfig, StreamHandler
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from app.settings import SETTINGS

def setup():
    logging_level = INFO
    # Setting up logging
    basicConfig(
        level=logging_level,
        format="%(asctime)s - %(levelname)s - [%(module)s] - %(message)s",
        handlers=[
            StreamHandler(stdout)
        ]
    )
    # Setting up sentry
    sentry_sdk.init(
        dsn=SETTINGS.SENTRY_URL.get_secret_value(),
        integrations=[
            AioHttpIntegration(),
        ],
        traces_sample_rate=1.0,
    )