from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton, 
                           InlineKeyboardButton, InlineKeyboardMarkup,
                           ReplyKeyboardRemove)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

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

def ingame_keyboard(isadmin: bool, picked: bool = False) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    if isadmin:
        builder.add(KeyboardButton(text='Выйти из лобби'))
    else:
        builder.add(KeyboardButton(text='Выбрать камень'))
        if picked:
            builder.add(KeyboardButton(text='Отойти от камня'))
    return builder.as_markup()