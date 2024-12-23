import asyncio
import logging
import app.logger as logger
import app.setup.handlers as handlers
import app.utils.payments as payments

from aiogram import Bot, Dispatcher

from app.settings import SETTINGS
from app.middlewares import DatabaseMiddleware, ErrorMiddleware
from app.routers import setup_error_handler
from app.routers import router as main_router
from app.setup.storage import get_events_isolation, get_storage
from app.utils.mongodb import MongoDB
from app.utils.payments import YookassaApi

logger.setup()

async def main():
    bot = Bot(SETTINGS.BOT_TOKEN.get_secret_value(), parse_mode="HTML")
    handlers.set_bot(bot)
    
    # Setup yookassa
    YookassaApi.setup(
        SETTINGS.YOOKASSA_ACCOUNT_ID.get_secret_value(),
        SETTINGS.YOOKASSA_SECRET_KEY.get_secret_value(),
    )

    # Setup database
    MongoDB.setup(
        SETTINGS.MONGODB_URL.get_secret_value(), 
        SETTINGS.MONGODB_DB.get_secret_value(),
    )

    dp = Dispatcher(
        storage=get_storage(),
        events_isolation=get_events_isolation(),
    )

    # Registering middlewares
    db_middleware = DatabaseMiddleware(MongoDB.get_database())
    dp.message.middleware(db_middleware)
    dp.callback_query.middleware(db_middleware)
    dp.chat_member.middleware(db_middleware)
    dp.errors.middleware(ErrorMiddleware())

    # Registering error handler
    setup_error_handler(SETTINGS.LOGGING_CHAT, bot)

    # Registering routers
    dp.include_router(main_router)
    
    # Starting polling
    loop = asyncio.get_running_loop()
    loop.create_task(
        dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()        
        ),
    )

    dp.startup.register(handlers.on_startup)
    
if __name__ == "__main__":
    logging.warning("Starting bot")
    loop = asyncio.new_event_loop()
    loop.create_task(main())
    loop.run_forever()
    logging.warning("Bot stopped")