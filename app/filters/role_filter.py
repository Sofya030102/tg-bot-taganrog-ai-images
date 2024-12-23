from aiogram.filters import BaseFilter
from aiogram.types import Message

from app.utils.cache import Cache
from app.utils.enums import UserRole

class RoleFilter(BaseFilter):
    required_role: UserRole | list

    def __init__(self, required_role: UserRole | list):
        ''' required_value: UserRole | List[UserRole] '''
        self.required_role = required_role

    async def __call__(self, message: Message) -> bool:
        cached_user = await Cache.get_user(message.from_user)
        if isinstance(self.required_role, UserRole):
            return cached_user.role == self.required_role
        elif isinstance(self.required_role, list):
            return cached_user.role in self.required_role
        return False