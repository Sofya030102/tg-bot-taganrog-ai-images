


import httpx
import traceback
import logging
import asyncio
import fal
import base64
import io
from aiogram.types import BufferedInputFile, InputFile

from datetime import datetime
from aiogram.types import Message

from app.settings import SETTINGS
from app.utils.queue import RequestQueue, RequestLimitter
from app.utils.mongodb import MongoDB
from app.utils.mongo_user import UserData

httpx_client = httpx.AsyncClient(proxies=SETTINGS.HTTP_PROXY.get_secret_value())
httpx_client_no_proxy = httpx.AsyncClient()

request_queue = RequestQueue((1, 2))

async def put_chat_completion(user_data: UserData, prompt: str, answer_message: Message, chat_id: str = None, replied_message_id: str = None):
    print("_chat_completion task prestart")
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
        print(response.content)
        raise httpx.HTTPStatusError(response.status_code, response.content)
    return response

async def _chat_completion(user_data: UserData, prompt: str, answer_message: Message, chat_id: str = None, replied_message_id: str = None):
    print("_chat_completion task")
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
        # If replied_message_id is None - first message
        else:
            prompt = f"""
Act as stable diffusion prompt generator. Answer only prompts in plain text and carefully follow this instruction.\n
Translate all words to english. Only use english. Do not use verbs, write tags.\n
User input: {prompt}\n
Add style keywords as: photorealistic, 4k, best quality
Final prompt:\n"""
        contents.append({"role": "user", "parts":[{"text": prompt}]})
        print("Contents: ", contents)
        # Request
        response = await _chat_completion_request(contents)
        print(response.json())
        response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        total_tokens = 0
        contents.append({"role": "model", "parts":[{"text": response_text}]})

        print("Response text: ", response_text)

        # Заменить таганрог
        response_text = response_text.replace("Taganrog", "Taganrog a city with a harbor")
        response_text = response_text.replace("taganrog", "Taganrog a city with a harbor")
        response_text = response_text.replace("Таганрог", "Taganrog a city with a harbor")
        response_text = response_text.replace("таганрог", "Taganrog a city with a harbor")

        loraUrl = ""

        if response_text.find("corpus g") != -1:
            loraUrl = "https://ictis.ru/corpus_g.safetensors"
        elif response_text.find("Taganrog") != -1:
            loraUrl = "https://github.com/AlexBSoft/sd-models/raw/main/KamennayaLestnica_400s_lr0002_512px.safetensors"
        elif response_text.find("KamennayaLestnica") != -1:
            loraUrl = "https://github.com/AlexBSoft/sd-models/raw/main/KamennayaLestnica_400s_lr0002_512px.safetensors"
        

        await answer_message.edit_text(response_text)
        # Отправляем response_text в генератор изображений
        result = await httpx_client_no_proxy.post(
            url=f"https://fal.run/fal-ai/fast-lcm-diffusion",
            headers={"Content-Type": "application/json", "Authorization": f"Key {SETTINGS.FAL_AI_API_KEY.get_secret_value().strip()}"},
            json={
                "model_name": "runwayml/stable-diffusion-v1-5",
                "prompt": response_text, 
                "negative_prompt": "nsfw, nude, sexual",
                "image_size": "square",
                "num_inference_steps": 12,
                "guidance_scale": 1.5,
                "sync_mode": True,
                "num_images": 1,
                "enable_safety_checker": True,
                "safety_checker_version": "v1",
                "format": "jpeg",
                "LoraWeight": {
                    "path": loraUrl,
                    "scale": 1
                }
            },
            timeout=60
        )
        falai_res = result.json()['images']
        print("falai result: ", falai_res)
        
        # falai_res[0]["url"] is base64 encoded image string

        image_buf = io.BytesIO(base64.b64decode(falai_res[0]["url"].replace("data:image/jpeg;base64,", "")))
        image = BufferedInputFile(file=image_buf.getvalue(), filename="image.jpg")
        
        newmessage = await answer_message.answer_photo(photo=image, caption=response_text, parse_mode="Markdown")
        await answer_message.delete()
        #await answer_message.
        #await bot.send_photo(chat_id=chat_id, photo=falai_res[0])

        # Save
        await MongoDB.db.completions.insert_one({
            "user": user_data._id,
            "chat_id": chat_id,
            "message_id": newmessage.message_id,
            "created": datetime.now(),
            "model": "iamgine",
            "image_generator": "falai",
            "total_tokens": total_tokens,
            "contents": contents,
            "falai_res": falai_res[0]
        })
        await user_data.statistics.inc_text_prompts()
        await user_data.take_quota(1)
        # Return
        #await answer_message.edit_text(response_text, parse_mode="Markdown")
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
                loop.create_task(_chat_completion(**data)) # TOOD: image generation
        except Exception as e:
            logging(f'{e}\n{traceback.format_exc()}')
        finally:
            await asyncio.sleep(0.2)