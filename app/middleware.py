from database import wrappers as wr

from typing import Callable, Dict, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from asyncio import Queue

class SignalMiddleware(BaseMiddleware):
    def __init__(self, lobby_ids: list[int]):
        super().__init__()
        self.__queues = {id: Queue() for id in lobby_ids}

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
        ) -> Any:
        if len(self.__queues) != 0:
            if 'queues' not in data.keys():
                data['queues'] = self.__queues.copy()
            else:
                data['queues'] |= self.__queues
        result = await handler(event, data)
        if result is not None:
            self.__queues[result] = Queue()
        return result