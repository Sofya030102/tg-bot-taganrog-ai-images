from aiogram.filters import BaseFilter
from aiogram.types import Message

from app.utils.mongodb import MongoDB


class UserSettingsFilter(BaseFilter):
    img_model: str
    text_model: str
    dialogue_mode: bool
    stream_mode: bool
    language_code: str
    document: str
    gpt_role: str

    def __init__(
            self, 
            img_model: str = None,
            text_model: str = None,
            dialogue_mode: bool = None,
            stream_mode: bool = None,
            language_code: str = None,
            document: str = None,
            gpt_role: str = None
        ) -> None:
        self.img_model = img_model
        self.text_model = text_model
        self.dialogue_mode = dialogue_mode
        self.stream_mode = stream_mode
        self.language_code = language_code
        self.document = document
        self.gpt_role = gpt_role

    async def __call__(self, message: Message) -> bool:
        user_raw_data = await MongoDB.get_user(message.from_user.id)
        flag = True
        if self.img_model is not None and self.img_model != user_raw_data['settings']['image_model']:
            flag = False
        if self.text_model is not None and self.text_model != user_raw_data['settings']['text_model']:
            flag = False
        if self.dialogue_mode is not None and self.dialogue_mode != user_raw_data['settings']['dialogue_mode']:
            flag = False
        if self.stream_mode is not None and self.stream_mode != user_raw_data['settings']['stream_mode']:
            flag = False
        if self.language_code is not None and self.language_code != user_raw_data['settings']['language_code']:
            flag = False
        if self.document is not None and self.document != user_raw_data['settings']['document']:
            flag = False
        if self.gpt_role is not None and self.gpt_role != user_raw_data['settings']['gpt_role']:
            flag = False
        return flag