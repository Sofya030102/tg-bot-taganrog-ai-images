import asyncio
import app.utils.payments as payments

from datetime import datetime, timedelta
from bson import ObjectId
from aiogram import Bot
from app.settings import SETTINGS
from app.utils.mongodb import MongoDB
from app.utils.cache import Cache

from app.utils.gemini import executor as gemini_executor
from app.utils.openai import executor as openai_executor
from app.utils.falai import executor as falai_executor

BOT = None

def set_bot(bot: Bot):
    global BOT
    BOT = bot

async def payment_status_changed_handler(payment: dict):
    sub = await MongoDB.get_subscription_by_name(payment.get('product'))
    user_data = await MongoDB.get_user(payment.get('user_id'))
    if payment.get('status') == 'succeeded':
        await BOT.send_message(SETTINGS.LOGGING_CHAT, f"""New subscriber {user_data['first_name']} (<code>{user_data['user_id']}</code>)\nSubscription {payment.get('product')}: {payment.get('price')} RUB""", parse_mode="HTML")
        msg = f"""
<b>😍 Вы успешно оплатили тариф {payment.get('product')}!</b>
Теперь вам ежедневно доступно <code>{sub.get('quota')}</code> запросов в течение <code>{sub.get('expire_days')}</code> дней.
"""    
    
        await BOT.send_message(user_data['user_id'], msg)
        await MongoDB.update_field(
            _id=user_data['_id'], 
            path=('subscription', ),
            value={
                "name": payment.get('product'),
                "description": sub.get('description'),
                "quota": sub.get('quota'),
                "expire_datetime": datetime.now() + timedelta(sub.get('expire_days')),
            })
        await Cache.clear_user(user_data['user_id'])

async def on_startup():
    loop = asyncio.get_running_loop()
    payments.register_payment_status_changed_handler(payment_status_changed_handler)
    loop.create_task(payments.check_payment_loop())
    loop.create_task(gemini_executor())
    loop.create_task(openai_executor())
    loop.create_task(falai_executor())