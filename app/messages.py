import json
from typing import Tuple

__messages_file = open('data/exceptions.json', encoding='utf-8')
Messages = json.load(__messages_file)
__messages_file.close()


def info_message(round: int, stones: dict[int, tuple[int, list[int]]]):
    info_str = ''
    stones = sorted(stones)
    for stone, info_stone in stones.items():
        is_here, players = info_stone
        players.sort()
        status = 'нет'
        if is_here:
            status = 'вы'
        if len(players) > 0:
            status += ' и '
            if len(players) > 1:
                status += 'игроки'
            else:
                status += 'игрок '
        status += ', '.join(map(str, players))
        info_str += f'{stone} 🗿 - {status}\n'
    return Messages['info_message'].format(round, info_str)

def lobby_is_running():
    return Messages['lobby_is_running']

def lobby_is_full():
    return Messages['lobby_is_full']

def useless_start():
    return Messages['useless_start']

def welcome(name: str):
    return Messages['welcome'].format(name)

def choose_lobby():
    return Messages['choose_lobby']

def choose_num_players():
    return Messages['choose_num_players']

def choose_num_stones():
    return Messages['choose_num_stones']

def incorrect_number():
    return Messages['incorrect_number']

def incorrect_num_players(n: int):
    return Messages['incorrect_num_players'].format(n)

def incorrect_num_stones(n: int):
    return Messages['incorrect_num_stones'].format(n)

def lobby_created(n: int):
    return Messages['lobby_created'].format(n)

def lobby_entered(n: int):
    return Messages['lobby_entered'].format(n)

def lobby_entered_for_others(n: int):
    return Messages['lobby_entered_for_others'].format(n)

def leaving_lobby_without_being_in():
    return Messages['leaving_lobby_without_being_in']

def left_lobby(n: int):
    return Messages['left_lobby'].format(n)

def lobby_left_for_others(left: int):
    return Messages['lobby_left_for_others'].format(left)

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

def game_over_for_user():
    return Messages['game_over_for_user']

def game_over_for_admin():
    return Messages['game_over_for_admin']