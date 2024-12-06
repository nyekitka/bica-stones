from database import wrappers as wr

from typing import Callable, Dict, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from asyncio import Queue

class SignalMiddleware(BaseMiddleware):
    def __init__(self, lobby_ids: list[int]):
        super().__init__()
        self.__queues = {id: Queue() for id in lobby_ids}
        self.__picked = {id: 0 for id in lobby_ids}

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
        ) -> Any:
        data['queues'] = self.__queues
        data['picked'] = self.__picked
        result = await handler(event, data)
        if result is not None:
            self.__queues[result] = Queue()
            self.__picked[result] = 0
        return result

    def picked(self):
        return self.__picked

    def queues(self):
        return self.__queues