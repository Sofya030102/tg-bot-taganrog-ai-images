import httpx
import openai
import hashlib
import logging
import asyncio
import traceback

from datetime import datetime
from aiogram.types import Message
from httpx_socks import AsyncProxyTransport

from app.settings import SETTINGS
from app.utils.mongodb import MongoDB
from app.utils.mongo_user import UserData
from app.utils.queue import RequestQueue, RequestLimitter

transport = AsyncProxyTransport.from_url(SETTINGS.SOCKS_PROXY.get_secret_value())
httpx_client = httpx.AsyncClient(transport=transport)
client = openai.AsyncOpenAI(api_key=SETTINGS.OPENAI_KEY.get_secret_value(), http_client=httpx_client)

request_queue = RequestQueue((1, 2))

async def put_chat_completion(user_data: UserData, prompt: str, answer_message: Message, chat_id: str = None, replied_message_id: str = None):
    global request_queue
    if not (await RequestLimitter.put(user_data.user_id, 1)):
        return False
    data = {
        "user_data": user_data,
        "prompt": prompt,
        "answer_message": answer_message,
        "chat_id": chat_id,
        "replied_message_id": replied_message_id
    }
    request_queue.put_general(("chat_completion", data,))
    return True

async def _chat_completion(user_data: UserData, prompt: str, answer_message: Message, chat_id: str = None, replied_message_id: str = None):
    try:
        history = [{"role": "system", "content": "You are a helpful assistant."}]
        # If chat_id is None
        if chat_id is None:
            chat_id = user_data.user_id
        # If replied_message_id is not None
        if replied_message_id is not None:
            response = await MongoDB.db.completions.find_one({"chat_id": chat_id, "message_id": replied_message_id})
            if response is not None and response.get('model') == user_data.settings.text_model:
                history = response.get('history', history)
        # Salted ID
        hashed_id = hashlib.sha256(str(user_data.user_id).encode('utf-8')).hexdigest()
        # History
        history.append({"role": "user", "content": prompt})
        # Request
        response = await client.chat.completions.create(
            model=user_data.settings.text_model,
            messages=history,
            user=hashed_id
        )
        response_text = response.choices[0].message.content
        total_tokens = response.usage.total_tokens
        history.append({"role": "assistant", "content": response_text})
        # Save
        await MongoDB.db.completions.insert_one({
            "user": user_data._id,
            "chat_id": chat_id,
            "message_id": answer_message.message_id,
            "created": datetime.now(),
            "model": user_data.settings.text_model,
            "total_tokens": total_tokens,
            "history": history
        })
        await user_data.statistics.inc_text_prompts()
        await user_data.take_quota(1)
        # Return
        await answer_message.edit_text(response_text, parse_mode="Markdown")
    except Exception as e:
        logging(f'{e}\n{traceback.format_exc()}')
        await answer_message.edit_text("Произошла ошибка. Попробуйте еще раз.")
        raise e
    finally:
        await RequestLimitter.pop(user_data.user_id)    

async def executor():
    global request_queue
    loop = asyncio.get_running_loop()
    while True:
        try:
            request = await request_queue.get_request()
            if request is None: 
                await asyncio.sleep(0.03)
                continue
            type, data = request
            if type == "chat_completion":
                loop.create_task(_chat_completion(**data))
        except Exception as e:
            logging(f'{e}\n{traceback.format_exc()}')
        finally:
            await asyncio.sleep(0.5)