from typing import Callable, Dict, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from asyncio import Queue

class SignalMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
    
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
        ) -> Any:
        result = await handler(event, data)
        if result is not None:
            if 'queues' not in data.keys():
                data['queues'] = {result : Queue()}
            else:
                data['queues'][result] = Queue()
        return result