#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import os
import pickle
from typing import Any

from lightdb import LightDB
from redis.asyncio import Redis

from core.misc.apis import APIs


class User:
    """Class for user in database"""

    def __init__(self, db: "Database", user_id: str):
        self.__db = db
        self.__id = user_id

    @property
    def apis(self) -> APIs:
        return APIs(self.token, self.system.lower().replace("_", ""))

    @property
    def id(self):
        return self.__id

    def get(self, key: str, default: Any = None) -> Any:
        return self.__db.get_key(self.__id, key, default=default)

    def set(self, key: str, value: Any) -> None:
        self.__db.set_key(self.__id, key, value)

    def pop(self, key: str) -> Any:
        return self.__db.pop_key(self.__id, key)

    def pop_key(self, attr: str, key: str, default: Any = None) -> Any:
        attr_value = self.__db.get_key(self.__id, attr)
        if attr_value is None:
            return None
        value = attr_value.pop(key, default)
        self.__db.set_key(self.__id, attr, attr_value)
        return value

    def set_key(self, attr: str, key: str, value: Any) -> None:
        attr_value = self.__db.get_key(self.__id, attr)
        if attr_value is None:
            attr_value = {}
        attr_value[key] = value
        self.__db.set_key(self.__id, attr, attr_value)

    def get_key(self, attr: str, key: str, default: Any = None) -> Any:
        attr_value = self.__db.get_key(self.__id, attr)
        if attr_value is None:
            return default
        return attr_value.get(key, default)

    def save(self):
        self.__db.save()

    @property
    def token(self) -> str:
        return self.get("token")

    @token.setter
    def token(self, value: str) -> None:
        self.set("token", value)

    @property
    def system(self) -> str:
        return self.get("system")

    @system.setter
    def system(self, value: str) -> None:
        self.set("system", value)

    def __getattribute__(self, __name: str) -> Any:
        if __name.startswith("db_"):
            return self.get(__name[3:])
        elif __name == "id":
            return self.__id
        return super().__getattribute__(__name)

    def __setattr__(self, __name: str, __value: Any) -> None:
        if __name.startswith("db_"):
            self.set(__name[3:], __value)
        else:
            super().__setattr__(__name, __value)

    def __getitem__(self, __name: str) -> Any:
        return self.get(__name)

    def __setitem__(self, __name: str, __value: Any) -> None:
        self.set(__name, __value)

    def __delitem__(self, __name: str) -> None:
        self.pop(__name)

    @property
    def cache(self) -> dict:
        return self.__db.cache.get(self.__id, {})

    @cache.setter
    def cache(self, value: dict) -> None:
        self.__db.cache.set(self.__id, value)

    def cache_key(self, name: str, default: Any = None) -> str:
        return self.cache.get(name, default)

    def cache_set_key(self, name: str, value: Any) -> None:
        self.cache[name] = value
        self.__db.cache.save()


class Database(LightDB):
    """
    Main database class
    """
    __instance__ = None

    def __new__(cls):
        if cls.__instance__ is None:
            cls.__instance__ = super().__new__(cls)
        return cls.__instance__

    def __init__(self) -> None:
        super().__init__(location="files/users_db.json")
        self.settings = LightDB("files/settings.json")
        self.cache = LightDB("files/cache.json")
        self.redis = Redis.from_url(os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/") + "20")
        self.redis._queue = []

    def __getattribute__(self, __name: str) -> Any:
        return (
            self.get(__name[3:])
            if __name.startswith("db_")
            else self.settings.get(__name[9:])
            if __name.startswith("settings_")
            else self.redis.get(__name[5:])
            if __name.startswith("redis_")
            else super().__getattribute__(__name)
        )

    def __setattr__(self, __name: str, __value: Any) -> None:
        return (
            self.set(__name[3:], __value)
            if __name.startswith("db_")
            else self.settings.set(__name[9:], __value)
            if __name.startswith("settings_")
            else super().__setattr__(__name, __value)
        )

    def user(self, id: str | int) -> User:
        return User(self, str(id))

    @property
    def closed(self) -> bool:
        return self.settings.get("closed", False) # noqa

    @closed.setter
    def closed(self, value: bool) -> None:
        self.settings.set("closed", value)

    @property
    def admins(self) -> list[int]:
        return list(map(int, os.environ.get("ADMINS", "").split(",")))

    @admins.setter
    def admins(self, value: list[str]) -> None:
        self.settings.set("admins", value)

    @property
    def blocked_users(self) -> list[int]:
        return self.settings.get("blocked-users", []) # noqa

    @blocked_users.setter
    def blocked_users(self, value: list[int]) -> None:
        self.settings.set("blocked-users", value)

    async def new_feedback(self, data: dict):
        await self.redis.set(f"feedback:{data['number']}", pickle.dumps(data))

    async def get_feedback(self, number: int):
        return pickle.loads(await self.redis.get(f"feedback:{number}"))

    async def delete_feedback(self, number: int):
        data = await self.get_feedback(number)
        await self.redis.delete(f"feedback:{number}")
        return data


database = db = Database()
