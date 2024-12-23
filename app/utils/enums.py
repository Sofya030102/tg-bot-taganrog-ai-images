from enum import Enum

class UserRole(Enum):
    USER = 'user'
    ADMIN = 'admin'

    def __str__(self) -> str:
        return self.value

class ActionOption(Enum):
    GPT = 'gpt'
    SD = 'sd'