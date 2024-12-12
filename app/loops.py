from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

import asyncio
import logging
from datetime import datetime, timedelta

from . import keyboards, messages
from database import wrappers as wr


async def move_loop(
    bot: Bot, 
    lobby: wr.Lobby,
    queue: asyncio.Queue
) -> bool:
    logging.debug('Running new move')
    users = await lobby.users()
    for user in users:
        if not user.is_admin() and user.status() != 'agent':
            try:
                info = await lobby.field_for_user(user)
                logging.debug(f'{user.id} - {info}')
            except wr.ActionException as ex:
                logging.error(str(ex))
            await bot.send_message(
                chat_id=user.id,
                text=messages.info_message(),
                reply_markup=keyboards.field_keyboard(info, lobby.default_stones_cnt, lobby.round())
            )
    logging.debug('Starting to wait a signal')
    sig = await queue.get()
    logging.debug('Sleeping 5 seconds')
    await asyncio.sleep(5)
    logging.debug('Ending move')
    await lobby.end_move()
    return sig == 'end'
    
async def round_loop(
        bot: Bot,
        lobby: wr.Lobby,
        queue: asyncio.Queue
) -> None:
    logging.debug('Starting a new round')
    await lobby.start_round()
    users = await lobby.users()
    minutes = int(lobby.round_duration_ms/60000)
    round = lobby.round()
    for user in users:
        if user.status() != 'agent':
            await bot.send_message(
                chat_id = user.id,
                text = messages.round_started(round, minutes, user.is_admin()),
                parse_mode='MarkdownV2',
                reply_markup=keyboards.ingame_keyboard(user.is_admin())
            )
    logging.debug('Making a scheduler')
    scheduler = AsyncIOScheduler()
    scheduler.start()
    end_time = datetime.now() + timedelta(minutes=minutes)
    scheduler.add_job(
        func=round_ended,
        trigger=DateTrigger(end_time),
        args=[queue]
    )
    is_finished = False
    while lobby.stones_left() > 0 and not is_finished:
        logging.debug('Making a new move')
        is_finished = await move_loop(bot, lobby, queue)
    while not queue.empty():
        queue.get_nowait()
    stones_left = lobby.stones_left()
    for user in users:
        if user.status() != 'agent':
            await bot.send_message(
                chat_id=user.id,
                text=messages.round_ended(lobby.round(), stones_left, user.is_admin()),
                reply_markup=keyboards.between_rounds_keyboard(user.is_admin())
            )
    await lobby.end_round()

async def round_ended(
    queue: asyncio.Queue
) -> None:
    logging.debug('Time is up. Sending a signal')
    await queue.put("end")
