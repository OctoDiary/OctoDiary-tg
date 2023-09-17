from typing import Any

from lightdb import LightDB


class User:
    """Класс пользователя"""

    def __init__(self, db: "Database", user_id: str):
        self.__db = db
        self.__id = user_id
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.__db.get_key(self.__id, key, default=default)
    
    def set(self, key: str, value: Any) -> None:
        self.__db.set_key(self.__id, key, value)
    
    def pop(self, key: str) -> Any:
        return self.__db.pop_key(self.__id, key)
    
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
        return super().__getattribute__(__name)
    
    def __setattr__(self, __name: str, __value: Any) -> None:
        if __name.startswith("db_"):
            self.set(__name[3:], __value)
        else:
            super().__setattr__(__name, __value)


class Database(LightDB):
    """
    База данных бота
    """
    __instance__ = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance__ is None:
            cls.__instance__ = super().__new__(cls)
        return cls.__instance__


    def __init__(self):
        super().__init__("database.json")


    def __getattribute__(self, __name: str) -> Any:
        if __name.startswith("user_"):
            return User(self, self.get(__name[5:]))
        return super().__getattribute__(__name)

    def user(self, id: str) -> User:
        return User(self, id)
