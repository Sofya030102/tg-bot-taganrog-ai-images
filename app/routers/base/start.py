import re
import asyncio

from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject, or_f, and_f
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state

from app.utils.mongodb import MongoDB
from app.utils.mongo_user import UserData
import app.utils.payments as payments

router = Router()

class WriteMail(StatesGroup):
    write_mail = State()

async def get_main_keyboard(user_data: UserData):
    kb = ReplyKeyboardBuilder()
    kb.button(text='🖼️ Создать изображение')

    kb.button(text='👤 Мой аккаунт')
    #kb.button(text='🍿 Оплатить подписку')
    kb.button(text='⚙️ Настройки')

    kb.button(text='❓ Как это работает?')
    # kb.button(text="📚 Анализ PDF")

    # kb.button(text='📡 Перейти в Web-версию')
    kb.adjust(1, 2, 1) 

    return kb.as_markup(resize_keyboard=True)

###                        
### Start Command Callback  
###                         
@router.message(
    Command(commands={"start"}),
    F.chat.type == "private"
)
async def start_command_handler(
        message: Message, 
        command: CommandObject, 
        user_data: UserData
    ) -> None:
    user = message.from_user
    msg = """
<b>Добро пожаловать в ИИ генератор изображений!</b> 🦾

💡Этот бот подключен к нейросети и может создавать любые изображения по вашему запросу! 
"""
    markup = await get_main_keyboard(user_data)
    await message.answer(msg, reply_markup=markup, parse_mode="html")
    await asyncio.sleep(2)

    msg = """
🍿 <b>Попробуйте мне написать:</b>
 ~ Нарисуй кота в аквапарке
 ~ Нарисуй дом
 ~ Изобрази снежный пейзаж 
"""
    await message.answer(msg, parse_mode="html")


###
### Start With GPT Callback
###
@router.message(
    F.text == "🖼️ Создать изображение",
    F.chat.type == "private"
)
async def start_with_gpt_callback(message: Message, user_data: UserData) -> None:
    await message.answer("Напишите мне что угодно, и я это нарисую! Можете попросить нарисовать котика 🐱")

###
### How It's Work? FAQ Callback
###
@router.message(
    and_f(
        or_f(
            F.text == "❓ Как это работает?",
            Command(commands={"faq"}),
        ),
        F.chat.type == "private"
    )
)
async def how_its_work_callback(message: Message) -> None:
    user = message.from_user
    msg = """
❓<b>Как это работает:</b>
StableDiffusion — это нейросеть, которая может создавать изображения из текстовых описаний. Вы можете попросить ее создать что угодно: от пейзажей до портретов, от абстрактных картин до фотореалистичных изображений.

❓<b>Как получить что-то нормальное:</b>
- Опишите то, что вы хотите увидеть, как можно более подробно. Укажите размер, цветовую гамму, стиль и другие детали.
- Используйте ключевые слова для описания вашего изображения. Например: «природа», «пейзаж», «портрет», «абстрактное».
- Обращайте внимание на стиль, который вам нравится. Например: «реалистичный», «импрессионистский», «сюрреалистический».
- <i>Чем больше деталей вы опишите, тем более качественное изображение получите.</i>
"""
    await message.answer(text=msg, parse_mode="HTML")

@router.callback_query(
    F.data == "upload_pdf",
    F.chat.type == "private"
)
async def upload_pdf_callback(query: CallbackQuery) -> None:
    await query.answer()


###
### Web Version Callback
###
@router.message(
    and_f(
        or_f(
            F.text == "📡 Перейти в Web-версию",
            Command(commands={"web"})
        ),
        F.chat.type == "private"
    )
)
async def switch_to_web_callback(message: Message, user_data: UserData) -> None:
    msg = """
Нажмите на кнопку ниже, чтобы перейти в Web-версию ⤵️
"""
    kb = InlineKeyboardBuilder()
    kb.button(text="📡 Перейти в Web-версию", url="https://www.studgpt.ru/")
    await message.answer(msg, reply_markup=kb.as_markup(), parse_mode="HTML")

###
### Profile Callback
###
@router.message(
    and_f(
        or_f(
            F.text == "👤 Мой аккаунт",
            Command(commands={"profile"})
        ),
        F.chat.type == "private"
    )
)
async def my_profile_callback(message: Message, user_data: UserData) -> None:
    sub = await MongoDB.get_subscription_by_name(user_data.subscription.name)
    quota = sub.get('quota', 0)
    remains = user_data.subscription.quota
    msg = f"""
<b>👨‍💻 Добро пожаловать,</b> {message.from_user.full_name}
├ Ваш юзернейм: <code>{message.from_user.username}</code>
├ Ваш ID: <code>{message.from_user.id}</code>
├ Ваш email: <code>{user_data.email}</code>
└ Язык бота: <code>'RU'</code>

💳 <b>Подписка:</b> {user_data.subscription.name}
├ <code>{quota}</code> запросов в день
└ Осталось на сегодня <code>{remains}</code> запросов

<i>* Запросы обновляются в 00:00 по московскому времени.</i>
"""
    
    kb = InlineKeyboardBuilder()
    #kb.button(text="✨ Увеличить количество запросов", callback_data="switch_to_subscriptions")
    await message.answer(msg, reply_markup=kb.as_markup(), parse_mode="HTML")

###
### Subscriptions Callback
###
@router.message(
    and_f(
        or_f(
            F.text == "🍿 Оплатить подписку",
            Command(commands={"subscriptions"})
        ),
        F.chat.type == "private"
    )
)
@router.callback_query(
    F.data == "switch_to_subscriptions"
)
async def buy_subscription_callback(message: Message, user_data: UserData) -> None:
    msg = """
<b>🔍Тариф СТАРТ</b>
├ <code>100</code> запросов в день
├ Доступ к нейросети ChatGPT
├ Передовые решения
├ Распознание текста из фото 
└ Создание изображений

<b>💎 Тариф ПРОДВИНУТЫЙ</b> 
├ <code>500</code> запросов в день
├ Доступ к GPT-4
├ Передовые решения
├ Анализ PDF-документов
├ Распознание текста из фото 
├ Доступ к новым beta-возможностям
└ Техническая поддержка
"""
    kb = InlineKeyboardBuilder()
    kb.button(text="Старт - 199 руб./месяц", callback_data="buy_start_subscription" if user_data.subscription.name == "Бесплатная" else "already_subscribed")
    kb.button(text="💎 Продвинутый - 499 руб./месяц", callback_data="buy_pro_subscription" if user_data.subscription.name in ['Бесплатная', 'Старт'] else "already_subscribed")
    kb.adjust(1, 1)
    if type(message) == CallbackQuery:
        await message.message.edit_text(msg, reply_markup=kb.as_markup(), parse_mode="HTML")
    else:
        await message.answer(text=msg, parse_mode="HTML", reply_markup=kb.as_markup())

@router.callback_query(
    F.data == "already_subscribed"
)
async def already_subscribed_callback(query: CallbackQuery, user_data: UserData) -> None:
    kb = InlineKeyboardBuilder()
    kb.button(text="Назад", callback_data="switch_to_subscriptions")
    await query.message.edit_text("😅 Вы уже имеете равную или лучшую подписку!", reply_markup=kb.as_markup(), parse_mode="HTML")


###
### Buy Subscription Callback
###
@router.callback_query(
    or_f(
        F.data == "buy_start_subscription",
        F.data == "buy_pro_subscription"
    )
)
async def buy_subscription_callback(query: CallbackQuery, user_data: UserData, state: FSMContext) -> None:
    await query.answer()
    if (user_data.email == "" or user_data.email is None):
        await state.set_state(WriteMail.write_mail)
        kb = InlineKeyboardBuilder()
        kb.button(text="Отмена", callback_data="cancel_states")
        await query.message.edit_text("<b>👨‍💻 Пришлите свой адрес электронной почты ⤵️</b>\nЭто необходимо для доставки чека после приобретения подписки.", reply_markup=kb.as_markup(), parse_mode="HTML")
        return
    if query.data == "buy_start_subscription":
        sub = await MongoDB.get_subscription_by_name("Старт")
    elif query.data == "buy_pro_subscription":
        sub = await MongoDB.get_subscription_by_name("Продвинутый")
    
    msg = f"""
<b>💳 Приобретение тарифа {sub.get('name')}</b>
Для оплаты тарифа нажмите на кнопку под этим сообщением. Платеж будет автоматически обработан в течение пары минут.

📚Переходя по ссылке вы соглашаетесь с <a href="https://www.studgpt.ru/terms">условиями использования</a>.

Тарифы продляются на месяц после истечения подписки.

<i>Если оплата прошла, но вы так и не получили тариф, обратитесь в техническую поддержку</i>
"""
    # If user already have payment
    payment = await MongoDB.db.payments.find_one({"user_id": query.from_user.id, "status": "pending", "product": sub.get('name')})
    if payment is not None:
        y_payment = await payments.YookassaApi.get_payment(payment.get('payment_id'))
        print(y_payment)
        if y_payment.status == payments.PaymentStatus.CANCELED:
            await MongoDB.update_payment(y_payment.id, 'canceled')
        else:
            kb = InlineKeyboardBuilder()
            kb.button(text="Оплатить", url=f"https://yoomoney.ru/checkout/payments/v2/contract?orderId={payment.get('payment_id')}")
            await query.message.answer(msg, reply_markup=kb.as_markup())
            return
    # Create new payment
    payment = await payments.create_subscription_payment(query.from_user.id, sub['_id'], user_data.email)
    kb = InlineKeyboardBuilder()
    kb.button(text="Оплатить", url=payment.url)
    await query.message.answer(msg, reply_markup=kb.as_markup())

###
### Write mail Callback
###
@router.callback_query(
    F.data == "write_mail",
    StateFilter(default_state)
)
async def write_mail_callback(query: CallbackQuery, user_data: UserData, state: FSMContext) -> None:
    await query.answer()
    await state.set_state(WriteMail.write_mail)
    kb = InlineKeyboardBuilder()
    kb.button(text="Отмена", callback_data="cancel_states")
    await query.message.edit_text("<b>👨‍💻 Пришлите свой адрес электронной почты:</b>", reply_markup=kb.as_markup(), parse_mode="HTML")

###
### Cancel states Callback
###
@router.callback_query(
    F.data == "cancel_states"
)
async def cancel_states_callback(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.clear()
    await query.message.delete()

###
### Write mail handler
###
@router.message(
    StateFilter(WriteMail.write_mail),
    F.chat.type == "private"
)
async def write_mail_handler(message: Message, user_data: UserData, state: FSMContext) -> None:
    if not re.match(r"[^@]+@[^@]+\.[^@]+", message.text):
        kb = InlineKeyboardBuilder()
        kb.button(text="Попробовать еще раз", callback_data="write_mail")
        await message.answer("<b>❗️ Некорректный адрес электронной почты!</b>", reply_markup=kb.as_markup())
        await state.clear()
        return
    await user_data.set_mail(message.text)
    kb = InlineKeyboardBuilder()
    kb.button(text="✨ Приобрести подписку", callback_data="switch_to_subscriptions")
    await message.answer("<b>✅ Электронная почта установлена!</b>", reply_markup=kb.as_markup(), parse_mode="HTML")
    await state.clear()

###
### Settings Callback
###
@router.message(
    and_f(
        or_f(
            F.text == "⚙️ Настройки",
            Command(commands={"settings"})
        ),
        F.chat.type == "private"
    )
)
@router.callback_query(
    F.data == "switch_to_settings"
)
async def settings_callback(message: Message, user_data: UserData) -> None:
#     kb = InlineKeyboardBuilder()
#     kb.button(text="📕 Документы PDF", callback_data="settings_select_pdf")
#     kb.button(text="👨‍💻 Генерация текста", callback_data="settings_text_generation")
#     kb.button(text="🌅 Генерация изображений", callback_data="settings_image_generation")
#     kb.adjust(1, 1, 1)

#     msg = """
# ⚡️ <b>Выберите необходимый раздел настроек</b>

# - <b>Загружайте PDF документы для анализа.</b> Это позволит вам подключить его содержимое к языковой модели, чтобы получить лучшие результаты генерации ответов от нейросети.

# - <b>Отправляйте боту изображения.</b> Вы можете отправлять боту любые изображения, нейросеть сгенерирует ответ с учетом содержимого картинки.

# <i>Часть функций может быть недоступна на вашем тарифе, для получения полного доступа к боту приобретите тариф /subscriptions.</i>
# """
#     if type(message) == CallbackQuery:
#         await message.message.edit_text(msg, reply_markup=kb.as_markup(), parse_mode="HTML")
#     else:
#         await message.answer(msg, reply_markup=kb.as_markup(), parse_mode="HTML")
    msg = f"""
<b>⚡️ Выберите модель</b> 

🔥 <b>StableDiffusion</b> {"✔️" if user_data.settings.text_model == 'imagine' else ''}
├ Быстрая модель для генерации изображений
└ Хорошее качество

Новые модели появятся скоро!
"""
    kb = InlineKeyboardBuilder()
    kb.button(text="StableDiffusion", callback_data="set_langmodel_imagine")
    #kb.button(text="GPT 3.5 Turbo", callback_data="set_langmodel_gpt-3.5-turbo")
    #kb.button(text="GPT 4", callback_data="set_langmodel_gpt4", )
    # kb.button(text="Назад", callback_data="switch_to_settings")
    kb.adjust(1, 1)
    await message.answer(msg, reply_markup=kb.as_markup(), parse_mode="HTML")


###
### Settings Text Generation Callback
###
@router.callback_query(
    or_f(
        F.data == "settings_text_generation",
        F.data.startswith("set_langmodel_")
    )
)
async def settings_text_generation_callback(query: CallbackQuery, user_data: UserData) -> None:
    await query.answer()

    if query.data.startswith("set_langmodel_"):
        model = query.data.split("_")[-1]
        if model == 'gpt4':
            await query.answer("Временно недоступно...")
            return
        if model == user_data.settings.text_model:
            return
        await user_data.settings.set_text_model(model)
        
    msg = f"""
<b>⚡️ Выберите языковую модель</b> 

🔥 <b>Gemini</b> {"✔️" if user_data.settings.text_model == 'gemini' else ''}
├ Новая модель от компании Google
└ Анализ изображений

🥶 <b>ChatGPT 3.5 Turbo</b> {"✔️" if user_data.settings.text_model == 'gpt-3.5-turbo' else ''}
├ Популярная модель
└ Решает сложные задачи

🥶 <b>ChatGPT 4</b> {"✔️" if user_data.settings.text_model == 'gpt4' else ''} (<i>временно недоступна</i>)
├ Самая совершенная модель
└ Анализ изображений
"""
    kb = InlineKeyboardBuilder()
    kb.button(text="Gemini", callback_data="set_langmodel_gemini")
    kb.button(text="GPT 3.5 Turbo", callback_data="set_langmodel_gpt-3.5-turbo")
    kb.button(text="GPT 4", callback_data="set_langmodel_gpt4", )
    # kb.button(text="Назад", callback_data="switch_to_settings")
    kb.adjust(3, 1)
    await query.message.edit_text(msg, reply_markup=kb.as_markup(), parse_mode="HTML")

###
### Settings Image Generation Callback
###
@router.callback_query(
    F.data == "settings_image_generation"
)
async def settings_image_generation_callback(query: CallbackQuery, user_data: UserData) -> None:
    await query.answer()
    await query.message.answer("🛠 В разработке")