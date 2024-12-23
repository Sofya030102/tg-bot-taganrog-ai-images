# TODO: Переделать под OrderedDict (LRU)
# *удалять при этом под lock'ом

import io

from asyncio import Lock
from datetime import datetime
from aiogram.types import User

from .mongodb import MongoDB
from .mongo_user import UserData, Settings, Statistics
from .enums import UserRole, ActionOption

class UserCache:
    '''
    Represents the bot user's cache.
    '''
    aiogram_user: User
    db_user: UserData
    lock: Lock

    def __init__(self, user: User) -> None:
        self.user = user
        self.db_user = None
        self.lock = Lock()

    @property
    def banned(self) -> bool:
        return self.db_user.banned

    @property
    def role(self) -> UserRole:
        return self.db_user.role

    @property
    def settings(self) -> Settings:
        return self.db_user.settings

    @property
    def statistics(self) -> Statistics:
        return self.db_user.statistics

    async def load(self):
        '''
        Loads or creates a user in the database.
        Locks an object when in use.
        '''
        async with self.lock:
            if self.db_user is not None:
                return
            data = await MongoDB.get_user(self.user.id)
            if data:
                self.db_user = UserData(**data)
                self.db_user.last_update = datetime.now()
                self.db_user.username = self.user.username
                self.db_user.first_name = self.user.first_name
                self.db_user.last_name = self.user.last_name
                await self.save()
            if self.db_user is None:
                self.db_user = UserData(
                    _id = None,
                    user_id = self.user.id,
                    reg_date = datetime.now(),
                    last_update = datetime.now(),
                    username = self.user.username,
                    first_name = self.user.first_name,
                    last_name = self.user.last_name
                )
                result = await MongoDB.get_database().tg_users.insert_one(self.db_user.as_dict())
            data = await MongoDB.get_user(self.user.id)
            self.db_user = UserData(**data)

    async def save(self):
        '''
        Saves stored_data in the database.
        '''
        await MongoDB.update_user(self.db_user.as_dict())

class Cache:
    __cache = {}
    __last_purge = datetime.now()

    @classmethod
    async def get_user(cls, user) -> UserCache:
        '''
        Get the user from the cache. Loads if it was not found.
        '''
        user_cache = cls.__cache.get(user.id)
        if user_cache is None:
            user_cache = UserCache(user)
            await user_cache.load()
        cls.__cache[user.id] = user_cache
        return user_cache
        
    @classmethod
    async def purge(cls):
        '''
        Force clears the cache. 
        Use at your own risk, may cause errors.
        '''
        items = list(cls.__cache.items())
        cls.__cache = {}
        for key, value in items:
            async with value.lock:
                try:
                    del cls.__cache[key]
                except Exception as error:
                    pass
        cls.__last_purge = datetime.now()

    @classmethod
    async def clear_user(cls, user_id):
        '''
        Force clears the cache for a user. 
        Use at your own risk, may cause errors.
        '''
        if (cls.__cache.get(user_id) is not None):
            del cls.__cache[user_id]

    @classmethod
    def get_size(cls):
        return len(cls.__cache.keys())
    
    @classmethod
    def get_last_purge(cls):
        return cls.__last_purge
    
    @classmethod
    async def get_cache_contents(cls) -> io.StringIO:
        '''
        Get the cache contents as StringIO.
        '''
        buffer = io.StringIO()
        i = 0
        items = list(cls.__cache.items())
        for key, value in items:
            buffer.write(f'({i}) {key} {value.data.as_dict()}\n')
            i += 1
        return buffer