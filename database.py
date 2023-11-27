#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from typing import Any

from lightdb import LightDB


class User:
    """Class for user in database"""

    def __init__(self, db: "Database", user_id: str):
        self.__db = db
        self.__id = user_id

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
        super().__init__(location="users_db.json")
        self.settings = LightDB("settings.json")

    def __getattribute__(self, __name: str) -> Any:
        return (
            self.get(__name[3:])
            if __name.startswith("db_")
            else self.settings.get(__name[9:])
            if __name.startswith("settings_")
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
        return self.settings.get("closed", False)

    @closed.setter
    def closed(self, value: bool) -> None:
        self.settings.set("closed", value)

    @property
    def admins(self) -> list[str]:
        return self.settings.get("admins", [5184725450, 692755648])

    @admins.setter
    def admins(self, value: list[str]) -> None:
        self.settings.set("admins", value)

    @property
    def blocked_users(self) -> list[int]:
        return self.settings.get("blocked-users", [])
