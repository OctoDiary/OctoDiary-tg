#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import asyncio
import functools
import inspect
from datetime import datetime, timedelta
from typing import Any, Callable, Union

from pydantic import BaseModel, Field

ReplyMarkup = Union[
    dict, list[dict], list[list[dict]],
    "ButtonCallback", list["ButtonCallback"], list[list["ButtonCallback"]]
]


class ButtonCallback(BaseModel):
    data: str
    text: str
    callback: Callable[..., Any]
    callback_args: Any
    callback_kwargs: Any
    delete_time: datetime | None
    reusable: bool = False

    @classmethod
    def init(
            cls,
            data: str,
            text: str,
            callback: Callable[..., Any],
            disable_deadline: bool = False,
            reusable: bool = False,
            delete_time: datetime | None = None,
            *callback_args, **callback_kwargs
    ) -> "ButtonCallback":
        return cls(
            data=data,
            text=text,
            callback=callback,
            callback_args=callback_args,
            callback_kwargs=callback_kwargs,
            delete_time=(
                delete_time if delete_time else datetime.now() + timedelta(minutes=20)
            ) if not disable_deadline else None,
            reusable=reusable
        )

    async def run_callback(self, *args, **kwargs):
        if not self.callback:
            return None
        elif inspect.iscoroutinefunction(self.callback):
            return await self.callback(
                *(self.callback_args + args),
                **{**kwargs, **self.callback_kwargs}
            )
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                functools.partial(
                    self.callback,
                    *(self.callback_args + args),
                    **{**kwargs, **self.callback_kwargs}
                )
            )

    async def update_callback_args(self, *args, **kwargs):
        self.callback_args = args
        self.callback_kwargs = kwargs


class AdditionalButtons(BaseModel):
    up_buttons: ReplyMarkup = Field([])
    below_buttons: ReplyMarkup = Field([])
