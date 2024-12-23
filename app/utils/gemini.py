import httpx
import traceback
import logging
import asyncio

from datetime import datetime
from aiogram.types import Message

from app.settings import SETTINGS
from app.utils.queue import RequestQueue, RequestLimitter
from app.utils.mongodb import MongoDB
from app.utils.mongo_user import UserData

httpx_client = httpx.AsyncClient(proxies=SETTINGS.HTTP_PROXY.get_secret_value())

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

async def put_analyze_photo(user_data: UserData, prompt: str, base64_photo: str, answer_message: Message, chat_id: str = None):
    global request_queue
    if not (await RequestLimitter.put(user_data.user_id, 1)):
        return False
    data = {
        "user_data": user_data,
        "prompt": prompt,
        "base64_photo": base64_photo,
        "answer_message": answer_message,
        "chat_id": chat_id
    }
    request_queue.put_general(("analyze_photo", data,))
    return True

async def _chat_completion_request(contents: list):
    response = await httpx_client.post(
        url=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={SETTINGS.GEMINI_API_KEY.get_secret_value().strip()}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": contents, 
            "safetySettings": [
                {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE",
                },
                {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE",
                },
                {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE",
                },
                {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE",
                },
            ],
        },
        timeout=60
    )
    if response.status_code != 200:
        raise httpx.HTTPStatusError(response.status_code, response.content)
    return response

async def _analyze_photo_request(contents: list):
    response = await httpx_client.post(
        url=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={SETTINGS.GEMINI_API_KEY.get_secret_value().strip()}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": contents,
            "safetySettings": [
                {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE",
                },
                {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE",
                },
                {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE",
                },
                {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE",
                },
            ],
        },
        timeout=60
    )
    if response.status_code != 200:
        raise httpx.HTTPStatusError(response.status_code, response.content)
    return response

async def _chat_completion(user_data: UserData, prompt: str, answer_message: Message, chat_id: str = None, replied_message_id: str = None):
    try:
        contents = []
        # If chat_id is None
        if chat_id is None:
            chat_id = user_data.user_id
        # If replied_message_id is not None
        if replied_message_id is not None:
            response = await MongoDB.db.completions.find_one({"chat_id": chat_id, "message_id": replied_message_id})
            if response is not None and response.get('model') == 'gemini-pro':
                contents = response.get('contents', contents)
        contents.append({"role": "user", "parts":[{"text": prompt}]})
        # Request
        response = await _chat_completion_request(contents)
        print(response.json())
        response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        total_tokens = 0
        contents.append({"role": "model", "parts":[{"text": response_text}]})
        # Save
        await MongoDB.db.completions.insert_one({
            "user": user_data._id,
            "chat_id": chat_id,
            "message_id": answer_message.message_id,
            "created": datetime.now(),
            "model": "gemini-pro",
            "total_tokens": total_tokens,
            "contents": contents
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

async def _analyze_photo(user_data: UserData, prompt: str, base64_photo: str, answer_message: Message, chat_id: str = None):
    try:
        contents = [{"role": "user", "parts":[{"text": prompt}, {"inline_data": {"mime_type":"image/jpeg","data": base64_photo}}]}]
        # If chat_id is None
        if chat_id is None:
            chat_id = user_data.user_id
        # Request
        response = await _analyze_photo_request(contents)
        response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        total_tokens = 0
        contents.append({"role": "model", "parts":[{"text": response_text}]})
        # Save
        await MongoDB.db.completions.insert_one({
            "user": user_data._id,
            "chat_id": chat_id,
            "message_id": answer_message.message_id,
            "created": datetime.now(),
            "model": "gemini-pro-vision",
            "total_tokens": total_tokens,
            "contents": contents
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
            elif type == "analyze_photo":
                loop.create_task(_analyze_photo(**data))
        except Exception as e:
            logging(f'{e}\n{traceback.format_exc()}')
        finally:
            await asyncio.sleep(0.2)
        