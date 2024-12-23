import bson

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandObject

from app.setup import handlers
from app.filters import RoleFilter
from app.utils.enums import UserRole
from app.utils.mongodb import MongoDB
from app.utils.mongo_user import UserData

router = Router()

@router.message(
    RoleFilter(required_role=UserRole.ADMIN),
    Command(commands={"test1"}),
)
async def bebra_handler(
    message: Message,
    command: CommandObject,
    user_data: UserData
) -> None:
    photo = open('settings.png', 'rb')
    await message.answer_photo(photo=photo)

@router.message(
    RoleFilter(required_role=UserRole.ADMIN),
    Command(commands={"chatid"}),
)
async def get_chat_id_handler(
    message: Message,
    command: CommandObject,
    user_data: UserData
) -> None:
    await message.reply(f"`{str(message.chat.id)}`", parse_mode="Markdown")

@router.message(
    RoleFilter(required_role=UserRole.ADMIN),
    Command(commands={"test"}),
)
async def test_command_handler(
    message: Message,
    command: CommandObject,
    user_data: UserData
) -> None:
    payment = await MongoDB.get_database().payments.find_one({"_id": bson.ObjectId('655f5ee58ef604a15feff120')})
    await handlers.payment_status_changed_handler(payment)

@router.message(
    RoleFilter(required_role=UserRole.ADMIN),
    Command(commands={"sub"})
)
async def test_sub_command_handler(
    message: Message,
    command: CommandObject,
    user_data: UserData
) -> None:
    await user_data.add_subscription("Test Subscription", "No", 150, 1)
    await message.reply('Added Test Subscription')