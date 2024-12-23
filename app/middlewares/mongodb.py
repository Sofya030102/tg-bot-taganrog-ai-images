from datetime import datetime
from typing import Callable, Any, Awaitable, Dict

from aiogram.enums.chat_member_status import ChatMemberStatus
from aiogram.types import Message
from aiogram import BaseMiddleware

from pymongo.database import Database
from app.utils.mongo_user import UserData
from app.utils.mongodb import MongoDB

class DatabaseMiddleware(BaseMiddleware):
    db: Database

    def __init__(
            self, 
            db: Database
        ) -> None:
        self.db = db

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        message = event.message if not hasattr(event, 'chat') else event
        user = event.from_user

        user_data = None
        raw_user_data = await MongoDB.get_user(user.id)
        # If user is not in database
        if (raw_user_data == None):
            text  = "<b>Бот запущен в тестовом режиме!</b>\n"
            text += "Подпишитесь на канал @studgpt, чтобы своевременно получать иформацию об обновлениях. "
            text += "Там же можно оставить отзыв о работе бота."
            await message.answer(text)
            user_data = UserData(
                _id = None,
                user_id = user.id,
                reg_date = datetime.now(),
                last_update = datetime.now(),
                username = user.username,
                first_name = user.first_name,
                last_name = user.last_name
            )
            await MongoDB.get_database().tg_users.insert_one(user_data.as_dict())
        
        # If user in database
        else:
            user_data = UserData(**raw_user_data)
        
        # User are banned
        if user_data.banned == True:
            await message.answer('Ваш аккаунт был деактивирован. Если вы считаете что это произошло по ошибке - свяжитесь с администратором.')
            return
        
        # Get user sub
        sub = await MongoDB.get_subscription_by_name(user_data.subscription.name)

        # Reset quota
        if user_data.last_update.date() < datetime.now().date():
            await MongoDB.update_field(
                _id = user_data._id,
                path = ('subscription', 'quota'),
                value = sub.get('quota')
            )
            await MongoDB.set_last_update(user_data._id)
            # NOTE: Сообщение о сбросе квоты
            await message.answer(f"Вам снова доступно {sub.get('quota')} запросов!")
        
        # Return data
        data['user_data'] = user_data
        data['subscription'] = sub
        return await handler(event, data)