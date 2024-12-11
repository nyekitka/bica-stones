from aiogram import types, F, Router, Bot
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command, CommandStart
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

import asyncio
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Union
from random import randint

from . import keyboards, messages
from database import wrappers as wr

async def send_message_to_all_users(
    bot: Bot,
    lobby: wr.Lobby,
    message: str,
    roles: list[str] = ['player'],
    reply_markup: Optional[
        Union[
            types.InlineKeyboardMarkup,
            types.ReplyKeyboardMarkup,
            types.ForceReply,
            types.ReplyKeyboardRemove
        ]
    ] = None,
    parse_mode: Optional[str] = None
) -> None:
    users = await lobby.users()
    for user in users:
        if user.status() in roles:
            await bot.send_message(
                chat_id=user.id,
                text=message,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )

async def send_document_to_all_users(
    bot: Bot,
    lobby: wr.Lobby,
    document: Optional[types.InputFile],
    caption: Optional[str] = None,
    roles: list[str] = ['player'],
    reply_markup: Optional[
        Union[
            types.InlineKeyboardMarkup,
            types.ReplyKeyboardMarkup,
            types.ForceReply,
            types.ReplyKeyboardRemove
        ]
    ] = None,
    parse_mode: Optional[str] = None
) -> None:
    users = await lobby.users()
    for user in users:
        if user.status() in roles:
            await bot.send_document(
                chat_id=user.id,
                document=document,
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )