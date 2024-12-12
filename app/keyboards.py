from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton, 
                           InlineKeyboardButton, InlineKeyboardMarkup,
                           ReplyKeyboardRemove, User)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from math import ceil

remove_keyboard = ReplyKeyboardRemove()

def start_keyboard(isadmin: bool) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text='Войти в лобби'))
    if isadmin:
        builder.add(KeyboardButton(text='Создать лобби'))
    return builder.as_markup()

def lobbies_keyboard(lobbies: list[int]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for id in lobbies:
        builder.add(InlineKeyboardButton(text=str(id), callback_data=f'enter {id}'))
    return builder.adjust(5).as_markup()

def inlobby_keyboard(isadmin: bool) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    if isadmin:
        builder.add(KeyboardButton(text='Начать игру'))
    builder.add(KeyboardButton(text='Выйти из лобби'))
    return builder.as_markup()

def ingame_keyboard(isadmin: bool) -> ReplyKeyboardMarkup | ReplyKeyboardRemove:
    if isadmin:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text='Выйти из лобби')]]
        )
    else:
        return ReplyKeyboardRemove()

def __list_for_stone(is_here: bool, info: list[int]) -> str:
    s = ''
    if is_here:
        s += '@ '
    s += ' '.join(map(str, info))
    return s

def field_keyboard(info: dict[int, tuple[int, list[int]]], max_stone: int, round: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=f'🏠 {__list_for_stone(*info[0])}', 
        callback_data=f'pick 0 {round}'
    )
    for key in range(1, max_stone + 1):
        if key in info.keys():
            builder.button(
                text=f'🪨 {__list_for_stone(*info[key])}',
                callback_data=f'pick {key} {round}'
            )
        else:
            builder.button(
                text='❌',
                callback_data=f'pick empty {round}'
            )
    builder.adjust(1, ceil(max_stone**0.5))
    return builder.as_markup()

def between_rounds_keyboard(isadmin: bool) -> ReplyKeyboardMarkup | ReplyKeyboardRemove:
    if isadmin:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text='Запустить новый раунд')],
                      [KeyboardButton(text='Закончить игру')],
                      [KeyboardButton(text='Выйти из лобби')]]
        )
    else:
        return ReplyKeyboardRemove()

def request_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
         InlineKeyboardButton(text='Принять', callback_data=f'accept {user_id}'),
         InlineKeyboardButton(text='Отклонить', callback_data=f'deny {user_id}')
        ]]
    )

def admins_list_keyboard(admins_list: list[User]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for admin in admins_list:
        builder.add(InlineKeyboardButton(
            text=f'Уволить {admin.full_name}',
            callback_data=f'fire {admin.id}'
        ))
    return builder.adjust(1).as_markup()