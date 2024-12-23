import asyncio

import datetime
from bson.objectid import ObjectId

from app.settings import SETTINGS

from .enums import *
from .mongodb import MongoDB

class Settings:
    _id: ObjectId
    action_option: ActionOption
    image_model: str
    text_model: str
    dialogue_mode: bool
    stream_mode: bool
    language_code: str
    document: str
    gpt_role: str
    dialogue_id: str

    def __init__(
            self,
            _id: ObjectId,
            action_option: ActionOption = ActionOption.GPT,
            image_model: str = None,
            text_model: str = SETTINGS.DEFAULT_GPT_MODEL,
            dialogue_mode: bool = False,
            dialogue_id: str = None,
            stream_mode: bool = False,
            language_code: str = None,
            document: str = None,
            gpt_role: str = None
        ) -> None:
        self._id = _id
        self.action_option = ActionOption(action_option)
        self.image_model = image_model
        self.text_model = text_model
        self.dialogue_mode = dialogue_mode
        self.dialogue_id = dialogue_id
        self.stream_mode = stream_mode
        self.language_code = language_code
        self.document = document
        self.gpt_role = gpt_role
    
    def as_dict(self) -> dict:
        return {
            'action_option': self.action_option.value,
            'image_model': self.image_model,
            'text_model': self.text_model,
            'dialogue_mode': self.dialogue_mode,
            'dialogue_id': self.dialogue_id,
            'stream_mode': self.stream_mode,
            'language_code': self.language_code,
            'document': self.document,
            'gpt_role': self.gpt_role
        }
    
    async def set_dialogue_id(self, dialogue_id: str, sync_with_db=True):
        if sync_with_db:
            result = await MongoDB.update_field(
                _id = self._id, 
                path = ('settings', 'dialogue_id'), 
                value = ObjectId(dialogue_id)
            )
            if not isinstance(result, ObjectId) and not result == None:
                raise ValueError('[set_dialogue_id] Value returned from db is incorrect!')
        self.dialogue_id = result

    async def set_stream_mode(self, stream_mode: bool, sync_with_db=True): 
        if sync_with_db:
            result = await MongoDB.update_field(
                _id = self._id, 
                path = ('settings', 'stream_mode'), 
                value = stream_mode
            )
            if not isinstance(result, bool) and not result == None:
                raise ValueError('[set_stream_mode] Value returned from db is incorrect!')
        self.stream_mode = result

    async def set_document(self, document: str, sync_with_db=True): 
        if sync_with_db:
            result = await MongoDB.update_field(
                _id = self._id, 
                path = ('settings', 'document'), 
                value = document
            )
            if not isinstance(result, str) and not result == None:
                raise ValueError('[set_document] Value returned from db is incorrect!')
        self.document = result

    async def set_gpt_role(self, gpt_role: str, sync_with_db=True):
        if sync_with_db:
            result = await MongoDB.update_field(
                _id = self._id, 
                path = ('settings', 'gpt_role'), 
                value = gpt_role
            )
            if not isinstance(result, str) and not result == None:
                raise ValueError('[set_gpt_role] Value returned from db is incorrect!')
        self.gpt_role = result

    async def set_action_option(self, option: ActionOption, sync_with_db=True):
        if sync_with_db:
            result = await MongoDB.update_field(
                _id = self._id, 
                path = ('settings', 'action_option'), 
                value = option.value
            )
            option = ActionOption(result)
            if not isinstance(option, ActionOption) and not result == None:
                raise ValueError('[set_action] Value returned from db is incorrect!')
        self.action_option = option
    
    async def set_image_model(self, model: str, sync_with_db=True):
        if sync_with_db:
            result = await MongoDB.update_field(
                _id = self._id, 
                path = ('settings', 'image_model'), 
                value = model
            )
        if not isinstance(result, str) and not result == None:
            raise ValueError('[set_image_model] Value returned from db is incorrect!')        
        self.image_model = result

    async def set_text_model(self, model: str, sync_with_db=True):
        if sync_with_db:
            result = await MongoDB.update_field(
                _id = self._id, 
                path = ('settings', 'text_model'), 
                value = model
            )
        if not isinstance(result, str) and not result == None:
            raise ValueError('[set_text_model] Value returned from db is incorrect!')
        self.text_model = result

    async def set_dialogue_mode(self, enabled: bool, sync_with_db=True):
        if sync_with_db:
            result = await MongoDB.update_field(
                _id = self._id, 
                path = ('settings', 'dialogue_mode'), 
                value = enabled
            )
            print(result)
            if not isinstance(result, bool) and not result == None:
                raise ValueError('[set_dialogue_mode] Value returned from db is incorrect!')
        self.dialogue_mode = result

    def __str__(self) -> str:
        return str(self.__dict__)

class Statistics:
    _id: ObjectId
    image_prompts: int
    text_prompts: int

    def __init__(
            self,
            _id: ObjectId,
            image_prompts: int = 0,
            text_prompts: int = 0
        ) -> None:
        self._id = _id
        self.image_prompts = image_prompts
        self.text_prompts = text_prompts

    async def inc_text_prompts(self):
        result = await MongoDB.increment_field(
            _id = self._id, 
            path = ('statistics', 'text_prompts'), 
            value = 1
        )
        if not isinstance(result, int):
            raise ValueError('[inc_text_prompts] Value returned from db is incorrect!')
        self.text_prompts = result
        
    def as_dict(self) -> dict:
        return {
            'image_prompts': self.image_prompts,
            'text_prompts': self.text_prompts
        }

    def __str__(self) -> str:
        return str(self.__dict__)

class Subscription:
    _id: ObjectId
    name: str
    description: str
    quota: int
    expire_datetime: datetime

    def __init__(
            self,
            _id: ObjectId,
            name: str = "Бесплатная",
            description: str = "Стандартная подписка",
            quota: int = 10,
            expire_datetime: datetime = datetime.datetime.now() + datetime.timedelta(2000)
        ) -> None:
        self._id = _id
        self.name = name
        self.description = description
        self.quota = quota
        self.expire_datetime = expire_datetime        
    
    def is_free(self) -> bool:
        return self.name == "Бесплатная"

    def take_quota(self, difference: int = 1) -> bool:
        '''
        Returns how many tokens was used
        '''
        if self.quota < difference:
            return False
        self.quota -= difference
        return True
    
    def has_quota(self) -> bool:
        '''
        Returns True if user has quota
        '''
        return self.quota > 0

    def as_dict(self) -> dict:
        return {
            'name': self.name,
            'description': self.description,
            'quota': self.quota,
            'expire_datetime': self.expire_datetime
        }

    def __str__(self) -> str:
        return str(self.__dict__)
    
class UserData:
    '''
    Represents user data that is stored in the database.
    '''
    user_id: int
    reg_date: datetime
    last_update: datetime
    username: str
    first_name: str
    last_name: str 
    role: UserRole
    banned: bool
    email: str
    subscription: Subscription
    settings: Settings
    statistics: Statistics
    lock: asyncio.Lock

    def __init__(
            self,
            user_id: int,
            reg_date: datetime,
            last_update: datetime,
            username: str,
            first_name: str,
            last_name: str,
            role: UserRole | str = UserRole.USER,
            banned: bool = False,
            subscription: dict = {},
            settings: dict = {},
            statistics: dict = {},
            email: str = None,
            _id: ObjectId = None
        ) -> None:
        self._id = _id
        self.user_id = user_id
        self.reg_date = reg_date
        self.last_update = last_update
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.role = UserRole(role)
        self.banned = banned
        self.email = email
        self.subscription = Subscription(_id, **subscription)
        self.settings = Settings(_id, **settings)
        self.statistics = Statistics(_id, **statistics)
        self.lock = asyncio.Lock()
    
    async def has_quota(self):
        async with self.lock:
            return self.subscription.has_quota()

    async def add_subscription(
            self, 
            name: str,
            description: str,
            quota: int,
            expire_after_days: int
        ) -> None:
        async with self.lock:
            expire = datetime.datetime.now() + datetime.timedelta(expire_after_days)
            sub = Subscription(self._id, name, description, quota, expire)
            result = await MongoDB.update_field(
                _id = self._id,
                path = ('subscription', ),
                value = self.subscription.as_dict()
            )
            if type(result) != dict:
                raise ValueError('[add_subscription] Value returned from db is incorrect!')
            self.subscription = Subscription(self._id, **result)

    async def take_quota(self, difference: int = 1) -> bool:
        '''
        Takes quota from subscription
        Returns True if successful, otherwise False
        '''
        async with self.lock:
            if not self.subscription.has_quota():
                return False
            if not self.subscription.take_quota(difference):
                return False
            result = await MongoDB.update_field(
                _id = self._id,
                path = ('subscription', ),
                value = self.subscription.as_dict()
            )
            if type(result) != dict:
                raise ValueError('[take_quota] Value returned from db is incorrect!')
            self.subscription = Subscription(self._id, **result)
    
    async def set_mail(self, email: str) -> None:
        async with self.lock:
            result = await MongoDB.update_field(
                _id = self._id,
                path = ('email', ),
                value = email
            )
            if type(result) != str:
                raise ValueError('[set_mail] Value returned from db is incorrect!')
            self.email = email

    def as_dict(self) -> dict:
        '''
        Returns the dict that is stored in the database.
        '''
        data = {}
        if self._id is not None:
            data['_id'] = self._id
        data.update(
            {
                'user_id': self.user_id,
                'reg_date': self.reg_date,
                'last_update': self.last_update,
                'username': self.username,
                'first_name': self.first_name,
                'last_name': self.last_name,
                'email': self.email,
                'role': self.role.value,
                'banned': self.banned,
                'subscription': self.subscription.as_dict(),
                'settings': self.settings.as_dict(),
                'statistics': self.statistics.as_dict()
            }
        )
        return data
    
    def set_id(self, id: ObjectId) -> None:
        '''
        This method is used only when creating a new user.
        Do not use it for other purposes. May cause serious 
        errors in the database!
        '''
        self._id = id

    def __str__(self) -> str:
        return str(self.__dict__)