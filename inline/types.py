import asyncio
from datetime import datetime, timedelta
import functools
import inspect
from typing import Any, Callable

from pydantic import BaseModel


class ButtonCallback(BaseModel):
    data: str
    text: str
    callback: Callable[..., Any]
    callback_args: Any
    callback_kwargs: Any
    delete_time: datetime

    @classmethod
    def init(
        cls,
        data: str,
        text: str,
        callback: Callable[..., Any],
        *callback_args, **callback_kwargs
    ) -> "ButtonCallback":
        return cls(
            data=data,
            text=text,
            callback=callback,
            callback_args=callback_args,
            callback_kwargs=callback_kwargs,
            delete_time=datetime.now() + timedelta(minutes=20)
        )
    
    
    async def run_callback(self, *args, **kwargs):
        if not self.callback:
            return None
        elif inspect.iscoroutinefunction(self.callback):
            return await self.callback(
                *(self.callback_args+args), 
                **{**kwargs, **self.callback_kwargs}
            )
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                functools.partial(
                    self.callback,
                    *(self.callback_args+args),
                    **{**kwargs, **self.callback_kwargs}
                )
            )
    
    async def update_callback_args(self, *args, **kwargs):
        self.callback_args = args
        self.callback_kwargs = kwargs

