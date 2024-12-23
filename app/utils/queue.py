import asyncio
import logging

from typing import Tuple
from queue import Queue

from asyncio import Lock

class RequestLimitter():
    storage: dict
    lock: Lock
    
    @classmethod
    def init(cls):
        cls.storage = {}
        cls.lock = Lock()

    @classmethod
    async def put(cls, user_id: int, max_requests: int):
        async with cls.lock:
            if cls.storage.get(user_id) is None:
                cls.storage[user_id] = 0
            if cls.storage[user_id] >= max_requests:
                return False
            cls.storage[user_id] += 1
            return True
    
    @classmethod
    async def pop(cls, user_id: int):
        async with cls.lock:
            if cls.storage.get(user_id) is None:
                return
            cls.storage[user_id] -= 1

RequestLimitter.init()

class RequestQueue():
    general_size: int
    premium_size: int
    
    general_queue: Queue
    premium_queue: Queue
    
    lock: Lock
    ratio: Tuple[int, int]
    
    def __init__(self, ratio: Tuple[int, int]) -> None:
        self.general_size = 0
        self.premium_size = 0
        
        self.general_queue = Queue()
        self.premium_queue = Queue()
        
        self.ratio = ratio
        
        self.cur_general_count = 0
        self.cur_premium_count = 0

        self.lock = Lock()
    
    async def get_request(self):
        async with self.lock:
            if self.cur_general_count >= self.ratio[0] and \
                    self.cur_premium_count >= self.ratio[1]:
                self.cur_general_count = 0
                self.cur_premium_count = 0

            if self.cur_general_count < self.ratio[0]:
                self.cur_general_count += 1
                if self.general_size:
                    return self.get_general()
            if self.cur_premium_count < self.ratio[1]:
                self.cur_premium_count += 1
                if self.premium_size:
                    return self.get_premium()
        
            return None
    
    def get_total_size(self) -> int:
        return self.general_queue.qsize() +\
            self.premium_queue.qsize()
    
    def get_general(self):
        request = self.general_queue.get_nowait()
        self.general_size -= 1
        return request
    
    def get_premium(self):
        request = self.premium_queue.get_nowait()
        self.premium_size -= 1
        return request
    
    def put_general(self, request):
        self.general_queue.put_nowait(request)
        self.general_size += 1
        
    def put_premium(self, request):
        self.premium_queue.put_nowait(request)
        self.premium_size += 1