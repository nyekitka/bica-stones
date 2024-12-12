from aiogram import types, Bot

from typing import Optional, Union

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

async def get_users(
    bot: Bot,
    user_ids: list[int]
) -> list[types.User]:
    users = []
    for id in user_ids:
        user = await bot.get_chat(id)
        users.append(user)
    return users