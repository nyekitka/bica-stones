import datetime
import string
from collections import deque

import numpy as np
import pandas as pd
import logging
import os
import time
from typing import Optional

from psycopg import DatabaseError

from data.exception import ActionException, _NO_SUCH_ELEMENT, _DATA_DELETED, _NOT_SYNCHRONIZED_WITH_DATABASE, \
    _GAME_IS_RUNNING, _ALREADY_IN_LOBBY, _NOT_IN_LOBBY, _GAME_IS_NOT_RUNNING, _ALREADY_CHOSEN_STONE, init_exceptions, \
    _NO_SUCH_STONE, _MAX_POSSIBLE_PLAYERS
from database.query import connection_pool, do_request



def gen_rnd_matrix(lines: int, columns: int = None) -> tuple[tuple[int, ...], ...]:
    """
    Generates matrix of ids for players in lobby.
    """
    if columns is None:
        columns = lines
    order = list(range(1, columns + 1))
    result = []
    for _ in range(lines):
        np.random.shuffle(order)
        result.append(tuple(order))
    return tuple(result)


_START_ROUND_VALUE = 0
_DEFAULT_ROUND_DURATION = 120
_DEFAULT_MOVE_DURATION = 15


def player_naming_generator():
    """
    Generates players names like A, B, C ... AA, AB, AC...
    """
    queue = deque([''])
    while True:
        if len(queue) == 0:
            raise ActionException(_MAX_POSSIBLE_PLAYERS)
        elem = queue.popleft()
        for sym in string.ascii_uppercase:
            value = elem + sym
            yield value
            try:
                queue.append(value)
            except:
                pass


class Lobby:
    # TODO: номер раунда в логах, все остальные функции

    """
    Class-wrapper of SQL relation "lobby"
    """
    __instances: dict[int, 'Lobby'] = {}

    def __init__(self, lobby_id: int, stones_set: dict[int, set] = None, stones_namings: dict[int, list[int]] = None,
                 move_max_duration_ms: int = _DEFAULT_MOVE_DURATION,
                 round_duration_ms: int = _DEFAULT_ROUND_DURATION, default_stones_cnt: int = 1, current_stones: int = 1, num_players: int = 0,
                 status: str = 'created',
                 round_num: int = _START_ROUND_VALUE,
                 move_number: int = 0):
        self.__lobby_id = lobby_id
        self.__num_players = num_players
        self.__status = status
        self.__round = round_num
        self.__deleted = False
        self.__current_stones_cnt = current_stones
        self.__default_stones_cnt = default_stones_cnt
        self.__move_max_duration_ms = move_max_duration_ms
        self.__move_number = move_number
        self.__round_duration_ms = round_duration_ms
        self.__stones_namings = stones_namings
        self.__stones_set = stones_set if stones_set is not None else {1: set(range(1, default_stones_cnt + 1))}

    def __new__(cls, lobby_id: int, stones_set: dict[int, set] = None,
                stones_namings: dict[int, list[int]] = None, move_max_duration_ms: int = _DEFAULT_MOVE_DURATION,
                round_duration_ms: int = _DEFAULT_ROUND_DURATION, default_stones_cnt: int = 1, current_stones: int = 1, num_players: int = 0,
                status: str = 'created',
                round_num: int = _START_ROUND_VALUE,
                move_number: int = 0):
        if lobby_id in cls.__instances:
            logging.debug(f"Lobby {lobby_id} already exists")
            return cls.__instances[lobby_id]

        logging.debug(f"Lobby {lobby_id} created")
        instance = super(Lobby, cls).__new__(cls)
        cls.__instances[lobby_id] = instance
        return instance

    @classmethod
    async def get_lobby(cls, lobby_id: int):
        if lobby_id in cls.__instances:
            return cls.__instances[lobby_id]
        db_lobby = await do_request(
            f"SELECT move_max_duration_ms, round_duration_ms, default_stones_cnt, current_stones_cnt, num_players, status, round "
            f"FROM public.\"lobby\" WHERE id = {lobby_id}")
        if db_lobby:
            stones_set = await do_request("""
                                            SELECT move_num, stones from lobby_%s.\"stones_list\" WHERE round_num=%s;
                                        """ % (lobby_id, db_lobby[0][-1]))
            stones_set = {round_stones[0]: set(list(map(int, round_stones[1].split(',')))) for round_stones in
                          stones_set}
            if db_lobby[0][-2] != 'created':
                stones_namings = await do_request("""
                SELECT * FROM lobby_%s.\"stones_namings\";
                """ % (lobby_id,))
                stones_namings = {int(naming[0]): naming[1:] for naming in stones_namings}
            else:
                stones_namings = None

            instance = cls(lobby_id, stones_set, stones_namings, *db_lobby[0])
            instance.__database_consistent = True
            return instance
        raise ActionException(_NO_SUCH_ELEMENT)

    @classmethod
    async def make_lobby(cls, stones: int, round_duration_ms: int = _DEFAULT_ROUND_DURATION,
                         move_max_duration_ms: int = _DEFAULT_MOVE_DURATION):
        """
        Creates a new lobby in the database and returns Lobby object
        """
        async with connection_pool.connection() as conn:
            try:
                cursor = conn.cursor()

                await cursor.execute(
                    """SELECT id FROM public.\"lobby\";""")
                result = await cursor.fetchall()
                result = [row[0] for row in result]
                if not result:
                    next_id = 1
                elif list(range(1, max(result) + 1)) == sorted(result):
                    next_id = max(result) + 1
                else:
                    for i in range(1, max(result) + 1):
                        if i not in result:
                            next_id = i
                            break

                await cursor.execute(
                    """INSERT INTO public.\"lobby\" (id, num_players, status, round, default_stones_cnt, current_stones_cnt, move_max_duration_ms, round_duration_ms) 
                    VALUES (%s, %s, \'%s\', %s, %s, %s, %s, %s) RETURNING *;""" %
                    (next_id, 0, 'created', _START_ROUND_VALUE, stones, stones, move_max_duration_ms, round_duration_ms))
                result = await cursor.fetchall()

                await cursor.execute(
                    """CREATE SCHEMA lobby_%s;""" %
                    (result[0][0]))
                await cursor.execute(
                    """CREATE TABLE lobby_%s.\"logs\"
                    (
                        date_time timestamp default current_timestamp,
                        player_id bigint not null,
                        stone_id int,
                        round_number int not null,
                        move_number int not null
                    );""" %
                    (result[0][0]))
                await cursor.execute(
                    """CREATE TABLE lobby_%s.\"player_list\"
                    (
                        id SERIAL primary key,
                        player_id bigint not null unique
                    );""" %
                    (result[0][0]))
                await cursor.execute(
                    """CREATE TABLE lobby_%s.\"stones_list\"
                    (
                        round_num int not null,
                        move_num int not null,
                        stones varchar(512) not null
                    );""" %
                    (result[0][0]))
            except DatabaseError as e:
                await conn.rollback()
                raise ActionException(e.sqlstate) from e
            except Exception as e:
                await conn.rollback()
                raise ActionException() from e
            finally:
                await cursor.close()
            await conn.commit()
        lobby_id = result[0][0]
        self = cls(lobby_id, default_stones_cnt=stones, current_stones=stones, move_max_duration_ms=move_max_duration_ms,
                   round_duration_ms=round_duration_ms)
        self.__database_consistent = True
        return self

    @staticmethod
    async def lobby_ids(is_for_admin: bool = False):
        """
        Returns list of ids of all lobbies in the database
        """
        if is_for_admin:
            db_lobbies = await do_request(f"SELECT id FROM public.\"lobby\" where status NOT IN ('finished');")
        else:
            db_lobbies = await do_request(f"SELECT id FROM public.\"lobby\" where status IN ('created');")
        return [lobbies[0] for lobbies in db_lobbies]

    async def num_players_with_chosen_stone(self):
        """
        Returns number of players with chosen stone
        """
        db_num_players = await do_request(
            """SELECT count(1) FROM lobby_%s.\"logs\" WHERE stone_id is not null and round_number = %s and move_number = %s;"""
            % (self.__lobby_id, self.__round, self.__move_number))
        return db_num_players[0][0]

    @property
    def move_max_duration_ms(self):
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        return self.__move_max_duration_ms

    @property
    def default_stones_cnt(self):
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        return self.__default_stones_cnt

    @property
    def round_duration_ms(self):
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        return self.__round_duration_ms

    async def join_user(self, user):
        """
        Tries to join a given user to the lobby.
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        if not (self.__status == 'created' or (user.is_admin() and self.__status != 'finished')):
            raise ActionException(_GAME_IS_RUNNING)
        if await user.lobby():
            raise ActionException(_ALREADY_IN_LOBBY)
        async with connection_pool.connection() as conn:
            try:
                cursor = conn.cursor()

                await cursor.execute("""
                                UPDATE public.\"user\"
                                SET current_lobby_id = %s
                                WHERE public.\"user\".tg_id = %s;
                                """ % (self.__lobby_id, user.id))
                await cursor.execute("""
                                INSERT INTO lobby_%s.\"player_list\" (player_id)
                                VALUES(%s);
                                """ % (self.__lobby_id, user.id,))
                if not user.is_admin():
                    await cursor.execute("""
                                    UPDATE public.\"lobby\"
                                    SET num_players = num_players + 1
                                    WHERE public.\"lobby\".id = %s;
    
                                    """ % (self.__lobby_id,))
                    self.__num_players += 1
                user.set_lobby(self)
            except DatabaseError as e:
                await conn.rollback()
                raise ActionException(e.sqlstate) from e
            except Exception as e:
                await conn.rollback()
                raise ActionException() from e
            finally:
                await cursor.close()
            await conn.commit()

    async def users(self):
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        result = await do_request(
            f"SELECT player_id FROM lobby_{self.__lobby_id}.\"player_list\"")
        user_list = [await User.add_or_get(user[0]) for user in result]
        user_list = list(filter(lambda player: player.status() != 'agent', user_list))
        return user_list

    async def players(self):
        user_list = await self.users()
        return [player for player in user_list if not player.is_admin()]

    async def kick_user(self, user):
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        if user.id not in list(map(lambda x: x.id, await self.users())):
            raise ActionException(_NO_SUCH_ELEMENT)
        async with connection_pool.connection() as conn:
            try:
                cursor = conn.cursor()
                await cursor.execute("""
                                UPDATE public.\"user\"
                                SET current_lobby_id = NULL
                                WHERE public.\"user\".tg_id = %s;
                                """ % (user.id,))

                await cursor.execute("""
                                DELETE from lobby_%s.\"player_list\"
                                WHERE player_id=%s;
                                """ % (self.__lobby_id, user.id,))

                if not user.is_admin():
                    await cursor.execute("""
                                    UPDATE public.\"lobby\"
                                    SET num_players = num_players - 1
                                    WHERE public.\"lobby\".id = %s;
                                    """ % (self.__lobby_id,))

                    self.__num_players -= 1
            except DatabaseError as e:
                await conn.rollback()
                raise ActionException(e.sqlstate) from e
            except Exception as e:
                await conn.rollback()
                raise ActionException() from e
            finally:
                await cursor.close()
            await conn.commit()

    async def real_to_fake_stone_name(self, user_id, stone_id):
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        if not self.__stones_namings:
            raise ActionException(_NO_SUCH_ELEMENT)
        return self.__stones_namings[user_id][stone_id - 1]

    async def fake_to_real_stone_name(self, user_id, stone_id):
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        if not self.__stones_namings:
            raise ActionException(_NO_SUCH_ELEMENT)
        result = self.__stones_namings[user_id].index(stone_id)
        if result == -1:
            raise ActionException(_NO_SUCH_ELEMENT)
        return result + 1

    async def start_game(self):
        """
        Tries to start a game
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        if self.__status != 'created':
            raise ActionException(_GAME_IS_RUNNING)
        async with connection_pool.connection() as conn:
            try:
                cursor = conn.cursor()

                await cursor.execute("""
                                UPDATE public.\"lobby\"
                                SET status = 'waiting', round = %s
                                WHERE public.\"lobby\".id = %s;
                                """ % (self.__round, self.__lobby_id))
                user_list = await self.players()
                namings_generator = player_naming_generator()
                player_namings = [next(namings_generator) for _ in range(self.__num_players)]
                np.random.shuffle(player_namings)

                await cursor.execute(
                    """DROP TABLE IF EXISTS lobby_%s.\"player_namings\";""" %
                    (self.__lobby_id,))
                await cursor.execute(
                    """CREATE TABLE IF NOT EXISTS lobby_%s.\"player_namings\"
                    (
                       player_id bigint not null,
                       naming varchar(16) not null
                    );""" %
                    (self.__lobby_id,))

                for i, player_naming in enumerate(player_namings):
                    await cursor.execute(
                        """INSERT INTO lobby_%s.\"player_namings\"
                        VALUES (%s, '%s');""" %
                        (self.__lobby_id, user_list[i].id, player_naming))

                self.__status = 'waiting'
            except DatabaseError as e:
                await conn.rollback()
                raise ActionException(e.sqlstate) from e
            except Exception as e:
                await conn.rollback()
                raise ActionException() from e
            finally:
                await cursor.close()
            await conn.commit()

    async def start_round(self):
        """
        Tries to start a new round
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        if self.__status != 'waiting':
            raise ActionException(_GAME_IS_RUNNING)
        async with connection_pool.connection() as conn:
            try:
                cursor = conn.cursor()
                self.__current_stones_cnt = self.__default_stones_cnt
                stones_matrix = gen_rnd_matrix(self.__num_players, self.__current_stones_cnt)
                user_list = await self.players()

                self.__stones_namings = {}
                await cursor.execute("""
                       DROP TABLE IF EXISTS lobby_%s.\"stones_namings\";
                       """ % (self.__lobby_id,))

                columns_stones = ',\n'.join(
                    [f"\"{str(stone_num)}\" int not null" for stone_num in range(1, self.__current_stones_cnt + 1)])

                await cursor.execute(
                    """CREATE TABLE IF NOT EXISTS lobby_%s.\"stones_namings\"
                    (
                       player_id bigint not null,
                       %s
                    );""" %
                    (self.__lobby_id, columns_stones,))
                for stones_namings, user in zip(stones_matrix, user_list):
                    self.__stones_namings[user.id] = stones_namings
                    await cursor.execute("""
                           INSERT INTO lobby_%s.\"stones_namings\" 
                           VALUES(%s, %s);
                           """ % (self.__lobby_id, user.id, ','.join(map(str, stones_namings))))

                await cursor.execute(
                    """INSERT INTO lobby_%s.\"stones_list\" (round_num, move_num, stones) VALUES
                    (
                        %s,
                        %s,
                        '%s'
                    );""" %
                    (self.__lobby_id, self.__round + 1, 1, ','.join(list(map(str, range(1, self.__current_stones_cnt + 1))))))

                await cursor.execute("""
                                UPDATE public.\"lobby\"
                                SET status = 'started', round = %s, current_stones_cnt = %s
                                WHERE public.\"lobby\".id = %s;
                                """ % (self.__round + 1, self.__default_stones_cnt, self.__lobby_id))
                self.__status = 'started'
                self.__round += 1
                self.__move_number = 1
                self.__stones_set = {1: set(range(1, self.__default_stones_cnt + 1))}
                await self.start_move_logs()
            except DatabaseError as e:
                await conn.rollback()
                raise ActionException(e.sqlstate) from e
            except Exception as e:
                await conn.rollback()
                raise ActionException() from e
            finally:
                await cursor.close()
            await conn.commit()

    async def end_game(self):
        """
        Tries to stop a game
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        if self.__status == 'created':
            raise ActionException(_GAME_IS_NOT_RUNNING)
        async with connection_pool.connection() as conn:
            try:
                cursor = conn.cursor()
                for player in await self.users():
                    await cursor.execute("""
                                            UPDATE public.\"user\"
                                            SET current_lobby_id = NULL
                                            WHERE public.\"user\".tg_id = %s;
                                            """ % (player.id,))
                    player.set_lobby(None)

                await cursor.execute("""
                                 UPDATE public.\"lobby\"
                                 SET status = 'finished', num_players = 0
                                 WHERE public.\"lobby\".id = %s;
                                 """ % (self.__lobby_id,))
                await cursor.execute("""
                                         TRUNCATE table lobby_%s.\"player_list\";
                                         """ % (self.__lobby_id,))
                self.__status = 'finished'
                self.__num_players = 0
            except DatabaseError as e:
                await conn.rollback()
                raise ActionException(e.sqlstate) from e
            except Exception as e:
                await conn.rollback()
                raise ActionException() from e
            finally:
                await cursor.close()
            await conn.commit()

    async def end_round(self):
        """
        Ends the current round.
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        if self.__status != 'started':
            raise ActionException(_GAME_IS_NOT_RUNNING)

        async with connection_pool.connection() as conn:
            try:
                cursor = conn.cursor()

                await cursor.execute("""
                           UPDATE public.\"lobby\"
                           SET round = %s, current_stones_cnt = %s, status = 'waiting'
                           WHERE public.\"lobby\".id = %s;
                           """ % (self.__round + 1, len(self.__stones_set[self.__move_number]), self.__lobby_id))

                for user in (await self.players()):
                    if user.chosen_stone is not None:
                        await user.leave_stone()

                self.__status = 'waiting'
            except DatabaseError as e:
                await conn.rollback()
                raise ActionException(e.sqlstate) from e
            except Exception as e:
                await conn.rollback()
                raise ActionException() from e
            finally:
                await cursor.close()
            await conn.commit()

    async def end_move(self):
        """
        Ends the current move.
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        if self.__status != 'started':
            raise ActionException(_GAME_IS_NOT_RUNNING)
        choices = await do_request("""
               SELECT stone_id FROM lobby_%s.\"logs\" where round_number = %s AND move_number = %s;""" % (
        self.__lobby_id, self.__round, self.__move_number))
        for stone_id in list(self.__stones_set[self.__move_number]):
            if len(list(filter(lambda x: x[0] == stone_id, choices))) == 2:
                self.__stones_set[self.__move_number].remove(stone_id)

        async with connection_pool.connection() as conn:
            try:
                cursor = conn.cursor()

                for player in await self.players():
                    await cursor.execute("""
                       INSERT INTO lobby_%s.\"logs\" (player_id, stone_id, round_number, move_number) VALUES (%s, NULL, %s, %s)""" % (
                        self.__lobby_id, player.id, self.__round, self.__move_number + 1))

                await cursor.execute("""
                           INSERT INTO lobby_%s.\"stones_list\" (round_num, move_num, stones) VALUES (
                           %s,
                           %s,
                           '%s')
                           """ % (
                    self.__lobby_id, self.__round, self.__move_number + 1,
                    ','.join(list(map(str, self.__stones_set[self.__move_number])))))

                self.__move_number += 1

                for user in (await self.players()):
                    if user.chosen_stone is not None:
                        await user.leave_stone()

                self.__stones_set[self.__move_number] = self.__stones_set[self.__move_number - 1].copy()
                self.__current_stones_cnt = len(self.__stones_set[self.__move_number])
            except DatabaseError as e:
                await conn.rollback()
                raise ActionException(e.sqlstate) from e
            except Exception as e:
                await conn.rollback()
                raise ActionException() from e
            finally:
                await cursor.close()
            await conn.commit()

    def number_of_players(self) -> int:
        """
        Returns a number of players in this lobby.
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        return self.__num_players

    def lobby_id(self) -> int:
        """
        Returns a lobby_id.
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        return self.__lobby_id

    def round(self) -> Optional[int]:
        """
        Returns the round number of this game.
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        return self.__round

    def move(self) -> Optional[int]:
        """
        Returns the move number of current round.
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        return self.__move_number

    def status(self) -> str:
        """
        Returns the status of this lobby.
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        return self.__status

    async def start_move_logs(self):
        for player in await self.players():
            await do_request("""
               INSERT INTO lobby_%s.\"logs\" (player_id, stone_id, round_number, move_number) VALUES (%s, %s, %s, %s)""" % (
                self.__lobby_id, player.id, 'NULL', self.__round, self.__move_number))

    def stones_left(self) -> int:
        """
        Returns the round number of this game.
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        return len(self.__stones_set[self.__move_number])

    async def player_naming(self) -> dict[int, str]:
        """
        Returns fake namings for players like user_id see them.
        :param user_id:
        :return:
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        result = await do_request("""
               SELECT * FROM lobby_%s.\"player_namings\"""" % (self.__lobby_id,))
        return {x[0]: x[1] for x in result}

    async def field_for_user(self, user) -> dict[int, tuple[bool, list[int]]]:
        """
        Returns the field for a user.
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        if user.id not in list(map(lambda x: x.id, await self.users())):
            raise ActionException(_NOT_IN_LOBBY)
        result = {await self.real_to_fake_stone_name(user.id, stone_id): (False, []) for stone_id in self.__stones_set[max(1, self.__move_number-1)]}
        choices = await do_request("""
                       SELECT stone_id, player_id FROM lobby_%s.\"logs\" where round_number = %s and move_number = %s;""" % (
            self.__lobby_id, self.__round, max(1, self.__move_number - 1),))
        fake_namings = await self.player_naming()
        if choices:
            for stone_id in self.__stones_set[max(1, self.__move_number - 1)]:
                stone_id_fake = await self.real_to_fake_stone_name(user.id, stone_id)
                result[stone_id_fake] = (
                    False, list(map(lambda x: fake_namings[x[1]], filter(lambda x: x[0] == stone_id and x[1] != user.id,
                                                                         choices))))
            result[0] = (
                False, list(map(lambda x: fake_namings[x[1]], filter(lambda x: (x[0] is None or x[0] not in self.__stones_set[max(1, self.__move_number - 1)]) and x[1] != user.id,
                                                                     choices))))
        user_log = list(filter(lambda x: x[1] == user.id, choices))
        if not user_log:
            raise ActionException()
        choice = user_log[0]
        if choice and choice[0] is not None and choice[0] in self.__stones_set[max(1, self.__move_number - 1)]:
            fake_choice = await self.real_to_fake_stone_name(user.id, choice[0])
            result[fake_choice] = (True, result[fake_choice][1])
        elif choice and (choice[0] is None or choice[0] not in self.__stones_set[max(1, self.__move_number - 1)]):
            result[0] = (True, result[0][1])
        return result

    async def get_logs(self) -> str:
        """
        Creates logs files .csv
        :return: filepath
        """
        path = os.path.join(f'{os.getenv('TEMP_DIR')}/logs_{self.__lobby_id}_{time.time()}.csv')
        result = await do_request("SELECT * FROM lobby_%s.\"logs\";" % (self.__lobby_id,))
        columns = await do_request("SELECT column_name FROM information_schema.columns WHERE table_name = 'logs' and table_schema = 'lobby_%s';" % (self.__lobby_id,))
        pd.DataFrame(result, columns=list(map(lambda x: x[0], columns))).sort_values(
            by=["round_number", "move_number"]).to_csv(path, index=False)
        return path

    async def last_round_started(self) -> datetime.datetime:
        result = await do_request("""
        select date_time from lobby_%s.logs where round_number = %s
        limit 1;
        """ % (self.__lobby_id, self.__round,))
        return result[0][0]

    async def delete(self):
        """
        Returns the round number of this game.
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        try:
            await do_request("""
            DROP SCHEMA lobby_%s CASCADE;

            DELETE from public.\"lobby\"
            WHERE id=%s;
            """ % (self.__lobby_id, self.__lobby_id,))
        except DatabaseError as e:
            raise ActionException(e.sqlstate) from e
        except Exception as e:
            raise ActionException() from e

        self.__deleted = True
        Lobby.__instances.pop(self.__lobby_id)

    def stones_set(self) -> set[int]:
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        return self.__stones_set[self.__move_number]

    def __str__(self):
        return f'Lobby {self.__lobby_id} with {self.__num_players} players and {self.__current_stones_cnt} stones and {self.__round} round and status {self.__status}'


class User:
    """
    Class-wrapper of SQL relation "User"
    """

    __instances: dict[int, 'User'] = {}

    def __init__(self, user_id: int, tg_id: int, status: str = 'player', current_lobby_id: int = None,
                 chosen_stone: int = None):
        self.__user_id = user_id
        self.__tg_id = tg_id
        self.__current_lobby_id = current_lobby_id
        self.__deleted = False
        self.__status = status
        self.chosen_stone = chosen_stone

    def __new__(cls, user_id: int, tg_id: int, status: str = 'player', current_lobby_id: int = None,
                chosen_stone: int = None):
        if user_id in cls.__instances:
            return cls.__instances[user_id]

        logging.debug(f"User {user_id} created")
        instance = super(User, cls).__new__(cls)
        cls.__instances[user_id] = instance
        return instance

    @classmethod
    async def add_or_get(cls, tg_id: int, status: str = 'player'):
        """
        Returns User object with given tg_id or creates it in database
        """
        result = await do_request("""
        SELECT * FROM public.\"user\"
        WHERE tg_id = %s;
        """ % (tg_id,))

        if len(result) == 0:
            result = await do_request("""
            INSERT INTO public.\"user\" (tg_id, status)
            VALUES (%s, %s) RETURNING *;""" % (tg_id, status))

        chosen_stone = await do_request("""
        SELECT stone_id FROM lobby_%s.\"logs\" where player_id = %s
        ORDER BY date_time DESC LIMIT 1;""" % (result[0][3], result[0][1])) if result[0][3] is not None else None

        if chosen_stone:
            chosen_stone = chosen_stone[0][0]
        else:
            chosen_stone = None

        result = result[0]

        self = cls(user_id=result[0], tg_id=result[1], status=result[2], current_lobby_id=result[3],
                   chosen_stone=chosen_stone)
        self.__database_consistent = True
        return self

    async def lobby(self) -> Optional[Lobby]:
        """
        Returns current lobby of user
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        if self.__current_lobby_id is None:
            return None
        return await Lobby.get_lobby(self.__current_lobby_id)

    def set_lobby(self, lobby: Lobby | None):
        if lobby is None:
            self.__current_lobby_id = None
            return
        self.__current_lobby_id = lobby.lobby_id()

    def is_admin(self):
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        return self.__status == 'admin'

    async def set_status(self, status: str):
        """
        Sets status of user
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        if status not in ['player', 'admin', 'agent']:
            raise ActionException(_NO_SUCH_ELEMENT)
        await do_request("""
        UPDATE public.\"user\"
        SET status = \'%s\'
        WHERE id = %s;
        """ % (status, self.__user_id))
        self.__status = status

    async def leave_stone(self):
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        if await self.lobby() is None:
            raise ActionException(_NOT_IN_LOBBY)
        if (await self.lobby()).status() != 'started':
            raise ActionException(_GAME_IS_NOT_RUNNING)
        self.chosen_stone = None
        await do_request("""
        UPDATE lobby_%s.\"logs\"
        SET stone_id = NULL
        WHERE player_id = %s AND round_number = %s AND move_number = %s;""" % (
            self.__current_lobby_id, self.__tg_id, (await self.lobby()).round(), (await self.lobby()).move()))

    async def choose_stone(self, stone_id: int):
        """
        Chooses stone with stone_id
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        if self.chosen_stone is not None:
            raise ActionException(_ALREADY_CHOSEN_STONE)
        if await self.lobby() is None:
            raise ActionException(_NOT_IN_LOBBY)
        if (await self.lobby()).status() != 'started':
            raise ActionException(_GAME_IS_NOT_RUNNING)

        stone_id = await (await self.lobby()).fake_to_real_stone_name(self.__tg_id, stone_id)
        logging.debug(f'real stone id: {stone_id}')
        if stone_id not in (await self.lobby()).stones_set():
            wtf = (await self.lobby()).stones_set()
            logging.debug(f'stones_set: {wtf}')
            raise ActionException(_NO_SUCH_STONE)
        self.chosen_stone = stone_id
        await do_request("""
        UPDATE lobby_%s.\"logs\"
        SET stone_id = %s
        WHERE player_id = %s AND round_number = %s AND move_number = %s;""" % (
            self.__current_lobby_id, stone_id, self.__tg_id, (await self.lobby()).round(), (await self.lobby()).move()))

    async def delete(self):
        """
        Returns the round number of this game.
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        try:
            await do_request("""
                DELETE from public.\"user\"
                WHERE id=%s;
                """ % (self.__user_id,))
        except DatabaseError as e:
            raise ActionException(e.sqlstate) from e
        except Exception as e:
            raise ActionException() from e

        self.__deleted = True
        User.__instances.pop(self.__user_id)

    def __str__(self):
        return f'User {self.__user_id} with tg_id {self.__tg_id} and status {self.__status}'

    @property
    def id(self):
        return self.__tg_id



