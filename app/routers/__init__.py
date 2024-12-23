import traceback

from datetime import datetime

from aiogram import Router
from aiogram.types import Chat

from aiogram.types.error_event import ErrorEvent
from aiogram.types import BufferedInputFile

from .admin.admin import router as admin_router
from .base.start import router as start_router
from .gpt.chatgpt import router as chatgpt_router
from .gpt.gemini import router as gemini_router
from .gpt.imagine import router as imagine_router

__chat = None
__bot = None

router = Router()

router.include_router(start_router)
router.include_router(admin_router)
router.include_router(imagine_router)
router.include_router(gemini_router)
router.include_router(chatgpt_router)

async def safe_warnings_hook(text: str):
    global __chat, __bot
    try:
        await __bot.send_message(
            chat_id = __chat,
            text = text
        )
    except Exception as e:
        traceback.print_exc()

async def error_handler(event: ErrorEvent):
    '''
    Handler for unexpected errors
    '''
    global __chat, __bot

    message = event.update.message
    if message:
        msg  = 'При выполнении вашего запроса произошла ошибка. '
        msg += 'Попробуйте снова через несколько секунд. '
        msg += 'При повторной ошибке сообщите в поддержку.'
        await message.answer(msg)

    msg  = f'⚠️ <b>Exception:</b> <code>{type(event.exception).__name__}</code>\n'
    if message:
        user = message.from_user
        msg += f'<b>User:</b> {user.full_name}(<code>{user.id}</code>)\n<b>Chat:</b> <code>{message.chat.id}</code>\n'
    msg += str(event.exception).replace('<', '').replace('>', '')

    await __bot.send_document(
        chat_id = __chat,
        document = BufferedInputFile(
            traceback.format_exc().encode('utf-8'), 
            f"traceback.txt"
        ),
        caption = msg
    )

def setup_error_handler(chat_id, bot):
    global __chat, __bot
    __chat = chat_id
    __bot = bot
    router.errors.register(error_handler)
    