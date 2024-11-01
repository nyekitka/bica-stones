import json
from typing import Tuple
from pymorphy3 import MorphAnalyzer

__messages_file = open('data/messages.json', encoding='utf-8')
Messages = json.load(__messages_file)
__messages_file.close()
morph = MorphAnalyzer()

def info_message(round: int, stones: dict[int, tuple[bool, list[int]]]):
    info_str = ''
    sorted_keys = sorted(stones)
    for stone in sorted_keys:
        is_here, players = stones[stone]
        players.sort()
        status=''
        if is_here:
            status = 'вы и '
        if len(players) > 0:
            if len(players) > 1:
                status += 'игроки '
            else:
                status += 'игрок '
        else:
            if is_here:
                status = 'вы'
            else:
                status = 'никого нет'
        status += ', '.join(map(str, players))
        info_str += f'{stone} 🗿 \\- {status}\n'
    return Messages['info_message'].format(round, info_str)

def no_lobbies(isadmin: bool):
    if isadmin:
        return Messages['no_lobby_for_admin']
    else:
        return Messages['no_lobby_for_user']

def lobby_is_running():
    return Messages['lobby_is_running']

def useless_start():
    return Messages['useless_start']

def welcome(name: str):
    return Messages['welcome'].format(name)

def choose_lobby():
    return Messages['choose_lobby']

def choose_num_stones():
    return Messages['choose_num_stones']

def incorrect_number():
    return Messages['incorrect_number']

def incorrect_num_stones(n: int):
    return Messages['incorrect_num_stones'].format(n)

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
        return Messages['left_lobby'].format(left)

def starting_not_being_in_lobby():
    return Messages['starting_not_being_in_lobby']

def round_started(round: int):
    return Messages['round_started'].format(round)

def round_ended(round: int):
    return Messages['round_ended'].format(round, round + 1)

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