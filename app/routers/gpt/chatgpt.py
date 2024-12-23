from aiogram import F, Router
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums.chat_member_status import ChatMemberStatus

from app.settings import SETTINGS
from app.filters import UserSettingsFilter

from app.utils.mongo_user import UserData
from app.utils.openai import *

router = Router()

@router.message(
    UserSettingsFilter(
        stream_mode = False,
        text_model='gpt-3.5-turbo'
    ),
    F.chat.type == "private"
)
async def gpt_message_handler(message: Message, user_data: UserData) -> None:
    # Only if user is chat member
    user = message.from_user
    member = await message.bot.get_chat_member(-1002076481867, user.id)
    if member is None or member.status in [ChatMemberStatus.KICKED, ChatMemberStatus.LEFT, ChatMemberStatus.RESTRICTED]:
        msg = """
💬Подпишитесь на официальный канал @studgpt, чтобы получить доступ к бесплатным запросам.   

<i>P.S. Там мы сейчас разыгрываем подписки Telegram Premium ⭐️</i>
"""     
        kb = InlineKeyboardBuilder()
        kb.button(text="✨ Подписаться", url="https://t.me/studgpt")
        await message.answer(msg, reply_markup=kb.as_markup(), parse_mode="HTML")
        return
    # If user has quota
    if not user_data.subscription.has_quota():
        msg = f"""
<b>😢 Вы достигли лимита запросов на сегодня.</b>
Приобритите тариф, чтобы увеличить количество доступных ежедневных запросов.
"""
        kb = InlineKeyboardBuilder()
        kb.button(text="✨ Увеличить количество запросов", callback_data="switch_to_subscriptions")
        await message.answer(msg, parse_mode="HTML", reply_markup=kb.as_markup())
        return
    # If user send photo
    if message.photo:
        if user_data.settings.text_model != 'gpt4':
            kb = InlineKeyboardBuilder()
            kb.button(text="Выбрать модель", callback_data="settings_text_generation")
            await message.answer('Модель ChatGPT-3.5 Turbo не поддерживает анализ изображений!', reply_markup=kb.as_markup())
            return
        await message.answer("🛠 Функция анализа изображений GPT4 в разработке!")
        return
    # Starting generating response
    msg = await message.reply("⏳ Запрос выполняется, пожалуйста, подождите...")
    # If user send text
    ok = await put_chat_completion(
        user_data=user_data, 
        prompt=message.text, 
        answer_message=msg,
        replied_message_id=message.reply_to_message.message_id if message.reply_to_message else None
    )
    if not ok: 
        await msg.edit_text("❗️<b>Мы уже выполняем ваш запрос</b>", parse_mode="HTML")
        await asyncio.sleep(5)
        await msg.delete()