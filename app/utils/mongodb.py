import logging
import asyncio

from bson import ObjectId
from typing import Iterable

from datetime import datetime
from pymongo.database import Database
from motor.motor_asyncio import AsyncIOMotorClient

class MongoDB:
    client: AsyncIOMotorClient
    db: Database

    @classmethod
    def setup(
            cls, 
            mongodb_url: str, 
            mongodb_db: str
        ) -> None:
        cls.client = AsyncIOMotorClient(mongodb_url) 
        cls.db = cls.client.get_database(mongodb_db)

        try:
            cls.client.admin.command('ping')
            logging.info('Connected to MongoDB')
        except Exception as e:
            logging.error(f'Exception while connecting to MongoDB: {e}')
    
    @classmethod
    async def __update_field(cls, _id: ObjectId, path: Iterable[str], value: any):
        '''
        {a: {b: True} }\n
        path to `b`: ('a', 'b')
        '''
        path_str = '.'.join(path)
        await MongoDB.get_database().tg_users.update_one(
            filter = {"_id": _id}, 
            update = {"$set": {path_str: value}}
        )
    
    @classmethod
    async def __get_field(cls, _id: ObjectId, path: Iterable[str], value: any):
        '''
        {a: {b: True} }\n
        path to `b`: ('a', 'b')
        '''
        path_str = '.'.join(path)
        result = await MongoDB.get_database().tg_users.find_one(
            filter = {"_id": _id},
            projection = {"_id": False, path_str: True}
        )
        if result is None:
            return result
        for a in path:
            result = result[a]
        return result

    @classmethod
    async def get_user(cls, user_id: int) -> dict:
        data = await cls.db.tg_users.find_one({"user_id": user_id})
        return data
    
    @classmethod
    async def update_user(cls, data: dict):
        result = await cls.db.tg_users.update_one({"_id": data['_id']}, {"$set": data})
        return result
    
    @classmethod
    async def set_last_update(cls, _id: ObjectId):
        loop = asyncio.get_running_loop()
        loop.create_task(cls.__update_field(_id, ['last_update'], datetime.now()))
    
    @classmethod
    async def update_field(cls, _id: ObjectId, path: Iterable[str], value: any):
        '''
        {a: {b: True} }\n
        path to `b`: ('a', 'b')
        '''
        await cls.__update_field(_id, path, value)
        # await cls.set_last_update(_id)
        result = await cls.__get_field(_id, path, value)
        return result
    
    @classmethod
    async def increment_field(cls, _id: ObjectId, path: Iterable[str], value: any):
        '''
        {a: {b: True} }\n
        path to `b`: ('a', 'b')
        '''
        path_str = '.'.join(path)
        await MongoDB.get_database().tg_users.update_one(
            filter = {"_id": _id}, 
            update = {"$inc": {path_str: value}}
        )
        # await cls.set_last_update(_id)
        result = await MongoDB.get_database().tg_users.find_one(
            filter = {"_id": _id},
            projection = {"_id": False, path_str: True}
        )
        for a in path:
            result = result[a]
        return result
        
    @classmethod
    async def get_subscription_by_name(cls, name: str) -> dict:
        result = await cls.db.subscriptions.find_one({"name": name})
        return result
    
    @classmethod
    async def get_subscription_by_id(cls, _id: ObjectId) -> dict:
        result = await cls.db.subscriptions.find_one({"_id": ObjectId(_id)})
        return result

    @classmethod
    async def insert_payment(cls, user_id: str, payment_id: str, status: str, product: str, price: int):
        result = await cls.db.payments.insert_one({"user_id": user_id, "created": datetime.now(), "payment_id": payment_id, "status": status, "product": product, "price": price})
        return result
    
    @classmethod
    async def get_pending_payments(cls):
        result = []
        async for payment in cls.db.payments.find({"status": "pending"}):
            result.append(payment)
        return result
    
    @classmethod
    async def update_payment(cls, payment_id: str, status: str):
        result = await cls.db.payments.update_one({"payment_id": payment_id}, {"$set": {"status": status}})
        return result
    
    @classmethod
    async def get_dialogue_history(cls, dialogue_id: str):
        result = await cls.db.gpt_logs.find_one({'_id': ObjectId(dialogue_id)})
        return result
    
    @classmethod
    async def save_dialogue(cls, data: dict):
        result = await cls.db.gpt_logs.update_one(data)
        return result
 
    @classmethod
    def get_database(cls) -> Database:
        return cls.db