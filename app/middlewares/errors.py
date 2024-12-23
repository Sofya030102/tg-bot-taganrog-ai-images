from datetime import datetime
from typing import Callable, Any, Awaitable, Dict

from aiogram.types.error_event import ErrorEvent
from aiogram import BaseMiddleware

from pymongo.database import Database
from app.utils.cache import Cache

class ErrorMiddleware(BaseMiddleware):
    def __init__(
            self
        ) -> None:
        pass

    async def __call__(
        self,
        handler: Awaitable[Any],
        event: ErrorEvent,
        data: Dict[str, Any]
    ) -> Any:        
        return await handler(event, data)