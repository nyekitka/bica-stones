import json
from aiogram.types import User
from pymorphy3 import MorphAnalyzer

__messages_file = open('data/messages.json', encoding='utf-8')
Messages = json.load(__messages_file)
__messages_file.close()
morph = MorphAnalyzer()

def info_message():
    return Messages['info_message']

def no_lobbies(isadmin: bool):
    if isadmin:
        return Messages['no_lobby_for_admin']
    else:
        return Messages['no_lobby_for_user']

def no_such_lobby(lobby_id: int):
    return Messages['no_such_lobby'].format(lobby_id)

def lobby_is_running():
    return Messages['lobby_is_running']

def useless_start():
    return Messages['useless_start']

def welcome(name: str):
    return Messages['welcome'].format(name)

def choose_lobby():
    return Messages['choose_lobby']

def choose_round_time():
    return Messages['choose_round_time']

def choose_num_stones():
    return Messages['choose_num_stones']

def incorrect_number():
    return Messages['incorrect_number']

def incorrect_num_stones(n: int):
    return Messages['incorrect_num_stones'].format(n)

def incorrect_round_length(n: int):
    return Messages['incorrect_round_length'].format(n)

def lobby_created(n: int):
    return Messages['lobby_created'].format(n)

def lobby_entered(n: int, is_other: bool):
    if is_other:
        player_word = morph.parse('игрок')[0]
        agreed_word = player_word.make_agree_with_number(n).word
        return Messages['lobby_entered_for_others'].format(n, agreed_word)
    else:
        return Messages['lobby_entered'].format(n)

def leaving_lobby_without_being_in():
    return Messages['leaving_lobby_without_being_in']

def left_lobby(left: int, is_other: bool):
    if is_other:
        player_word = morph.parse('игрок')[0]
        agreed_word = player_word.make_agree_with_number(left).word
        return Messages['lobby_left_for_others'].format(left, agreed_word)
    else:
        return Messages['left_lobby']

def starting_not_being_in_lobby():
    return Messages['starting_not_being_in_lobby']

def not_enough_players_for_start():
    return Messages['not_enough_players_for_start']

def round_started(round: int, minutes: int, isadmin: bool):
    word = morph.parse('минута')[0].make_agree_with_number(minutes)
    if isadmin:
        return Messages['round_started_for_admin'].format(round, minutes, word.inflect({'gent'}).word)
    else:
        return Messages['round_started_for_user'].format(round, minutes, word.word)

def round_ended(round: int, stones_left: int, is_admin: bool):
    if stones_left > 0:
        word = morph.parse('камень')[0].make_agree_with_number(stones_left).word
        if is_admin:
            return Messages['round_ended_failure_for_admin'].format(round, stones_left, word)
        else:
            return Messages['round_ended_failure_for_players'].format(round, stones_left, word)
    else:
        if is_admin:
            return Messages['round_ended_success_for_admin'].format(round)
        else:
            return Messages['round_ended_success_for_admin'].format(round)

def choose_stone():
    return Messages['choose_stone']

def stone_left():
    return Messages['stone_left']

def stone_chosen(n: int):
    return Messages['stone_chosen'].format(n)

def game_over(is_admin: bool):
    if is_admin:
        return Messages['game_over_for_admin']
    else:
        return Messages['game_over_for_user']
    
def no_stone_to_pick():
    return Messages['no_stone_to_pick']

def choice_is_made():
    return Messages['choice_is_made']

def inactive_keyboard():
    return Messages['inactive_keyboard']

def game_is_already_finished():
    return Messages['game_is_already_finished']

def action_out_of_lobby():
    return Messages['action_out_of_lobby']

def request_for_admin(user: User):
    tag = f'[{user.full_name}](tg://user?id={user.id})'
    return Messages['request_for_admin'].format(tag)

def admin_list(admins: list[User]):
    list_message = ""
    for admin in admins:
        list_message += f'[{admin.full_name}](tg://user?id={admin.id})\n'
    return Messages['admin_list'].format(list_message)

def is_not_admin():
    return Messages['is_not_admin']

def invalid_request():
    return Messages['invalid_request']

def wait_for_acception():
    return Messages['wait_for_acception']

def request_accepted():
    return Messages['request_accepted']

def request_denied():
    return Messages['request_denied']

def wait_til_player_leave():
    return Messages['wait_til_player_leave']

def is_not_admin():
    return Messages['is_not_admin']

def fire_notice():
    return Messages['fire_notice']

def fire_success(name: str):
    return Messages['fire_success'].format(name)