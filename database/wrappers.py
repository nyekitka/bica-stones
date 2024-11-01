import asyncio
import pandas as pd
import logging
import os
import time
from typing import Optional

from dotenv import load_dotenv
from psycopg import DatabaseError

from data.exception import ActionException, _NO_SUCH_ELEMENT, _DATA_DELETED, _NOT_SYNCHRONIZED_WITH_DATABASE, \
    _GAME_IS_RUNNING, _ALREADY_IN_LOBBY, _NOT_IN_LOBBY, _GAME_IS_NOT_RUNNING, _ALREADY_CHOSEN_STONE, init_exceptions
from database.query import connection_pool, do_request, init_pool

from itertools import permutations


def gen_rnd_matrix(lines: int, columns: int = None) -> tuple[tuple[int, ...], ...]:
    """
    Generates matrix of ids for players in lobby.
    """
    if columns is None:
        columns = lines
    permutation_generator = permutations(range(1, columns + 1), lines)
    ids_matrix = tuple(
        (
            next(permutation_generator)
            for _ in range(lines)
        )
    )
    return ids_matrix


class Lobby:
    # TODO: номер раунда в логах, все остальные функции

    """
    Class-wrapper of SQL relation "lobby"
    """
    __instances: dict[int, 'Lobby'] = {}

    def __init__(self, lobby_id: int, stones_set: dict[int, set] = None, stones: int = 1, num_players: int = 0, status: str = 'waiting',
                 round_num: int = 0):
        self.__lobby_id = lobby_id
        self.__num_players = num_players
        self.__status = status
        self.__round = round_num
        self.__deleted = False
        self.__stones_cnt = stones
        self.__stones_set = stones_set if stones_set is not None else {0: set(range(1, stones + 1))}

    def __new__(cls, lobby_id: int, stones_set: set = None, stones: int = 1, num_players: int = 0, status: str = 'waiting',
                round_num: int = 0):
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
            f"SELECT stones_cnt, num_players, status, round FROM public.\"lobby\" WHERE id = {lobby_id}")
        if db_lobby:
            stones_set = await do_request("""
                                            SELECT round_num, stones from lobby_%s.\"stones_list\";
                                        """ % (lobby_id,))
            stones_set = {round_stones[0]: set(list(map(int, round_stones[1].split(',')))) for round_stones in stones_set}
            instance = cls(lobby_id, stones_set, *db_lobby[0])
            instance.__database_consistent = True
            return instance
        raise ActionException(_NO_SUCH_ELEMENT)

    @classmethod
    async def make_lobby(cls, stones: int):
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
                    """INSERT INTO public.\"lobby\" (id, num_players, status, round, stones_cnt) VALUES (%s, %s, \'%s\', %s, %s) RETURNING *;""" %
                    (next_id, 0, 'waiting', 0, stones))
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
                        round_number int not null
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
                        stones varchar(512) not null
                    );""" %
                    (result[0][0]))
                await cursor.execute(
                    """INSERT INTO lobby_%s.\"stones_list\" (round_num, stones) VALUES
                    (
                        %s,
                        '%s'
                    );""" %
                    (result[0][0], 0, ','.join(list(map(str, range(1, stones + 1))))))
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
        self = cls(lobby_id, stones=stones)
        self.__database_consistent = True
        return self

    @staticmethod
    async def lobby_ids():
        """
        Returns list of ids of all lobbies in the database
        """
        db_lobbies = await do_request(f"SELECT id FROM public.\"lobby\"")
        return [lobbies[0] for lobbies in db_lobbies]

    async def join_user(self, user):
        """
        Tries to join a given user to the lobby.
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        async with connection_pool.connection() as conn:
            try:
                cursor = conn.cursor()

                if len(await do_request("""SELECT * FROM lobby_%s.\"player_list\" where player_id = %s;""" % (
                self.__lobby_id, user.id))) != 0:
                    raise ActionException(_ALREADY_IN_LOBBY)

                await cursor.execute("""
                                UPDATE public.\"user\"
                                SET current_lobby_id = %s
                                WHERE public.\"user\".tg_id = %s;
                                """ % (self.__lobby_id, user.id))

                await cursor.execute("""
                                UPDATE public.\"lobby\"
                                SET num_players = num_players + 1
                                WHERE public.\"lobby\".id = %s;
                                
                                """ % (self.__lobby_id,))

                await cursor.execute("""
                                INSERT INTO lobby_%s.\"player_list\" (player_id)
                                VALUES(%s);
                                """ % (self.__lobby_id, user.id,))
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
        return [await User.add_or_get(user[0]) for user in result]

    async def kick_user(self, user):
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        if not user.is_admin() and self.__status != 'waiting':
            raise ActionException(_GAME_IS_RUNNING)
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
                                UPDATE public.\"lobby\"
                                SET num_players = num_players - 1
                                WHERE public.\"lobby\".id = %s;

                                """ % (self.__lobby_id,))

                await cursor.execute("""
                                DELETE from lobby_%s.\"player_list\"
                                WHERE player_id=%s;
                                """ % (self.__lobby_id, user.id,))
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

    async def start_game(self):
        """
        Tries to start a game
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

                ids_matrix = gen_rnd_matrix(self.__num_players)
                user_list = await self.users()
                columns_players = ',\n'.join([f"\"{str(user.id)}\" int not null" for user in user_list])

                #stones_matrix = gen_rnd_matrix(self.__num_players, self.__stones_cnt)
                #columns_stones = ',\n'.join(
                #    [f"\"{str(stone_num)}\" int not null" for stone_num in range(1, self.__stones_cnt + 1)])

                await cursor.execute(
                    """CREATE TABLE lobby_%s.\"player_namings\"
                    (
                       player_id bigint not null,
                        %s
                    );""" %
                    (self.__lobby_id, columns_players))

                for i, player_namings in enumerate(ids_matrix):
                    await cursor.execute(
                        """INSERT INTO lobby_%s.\"player_namings\"
                        VALUES (%s, %s);""" %
                        (self.__lobby_id, user_list[i].id, ', '.join(list(map(str, player_namings)))))

                await cursor.execute("""
                                UPDATE public.\"lobby\"
                                SET status = 'started'
                                WHERE public.\"lobby\".id = %s;
                                """ % (self.__lobby_id,))
                await self.start_round_logs()
                self.__status = 'started'
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
        if self.__status != 'started':
            raise ActionException(_GAME_IS_NOT_RUNNING)
        async with connection_pool.connection() as conn:
            try:
                cursor = conn.cursor()

                await cursor.execute("""
                                UPDATE public.\"lobby\"
                                SET status = 'finished'
                                WHERE public.\"lobby\".id = %s;
                                """ % (self.__lobby_id,))
                self.__status = 'finished'
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

    def status(self) -> str:
        """
        Returns the status of this lobby.
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        return self.__status

    async def start_round_logs(self):
        for player in await self.users():
            await do_request("""
               INSERT INTO lobby_%s.\"logs\" (player_id, stone_id, round_number) VALUES (%s, %s, %s)""" % (
            self.__lobby_id, player.id, 'NULL', self.round()))

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
        choices = await do_request("""
               SELECT stone_id FROM lobby_%s.\"logs\" where round_number = %s;""" % (self.__lobby_id, self.__round,))
        new_set_stone = self.__stones_set[self.__round].copy()
        for stone_id in list(new_set_stone):
            if len(list(filter(lambda x: x[0] == stone_id, choices))) == 2:
                new_set_stone.remove(stone_id)

        async with connection_pool.connection() as conn:
            try:
                cursor = conn.cursor()

                for player in await self.users():
                    await cursor.execute("""
                          SELECT stone_id FROM lobby_%s.\"logs\" where player_id = %s and round_number = %s;""" % (
                    self.__lobby_id, player.id, self.__round))
                    result = await cursor.fetchone()
                    result = result[0]
                    if result not in new_set_stone:
                        result = "NULL"
                    await cursor.execute("""
                       INSERT INTO lobby_%s.\"logs\" (player_id, stone_id, round_number) VALUES (%s, %s, %s)""" % (
                        self.__lobby_id, player.id, result, self.__round + 1))

                await cursor.execute("""
                           UPDATE public.\"lobby\"
                           SET round = %s, stones_cnt = %s
                           WHERE public.\"lobby\".id = %s;
                           """ % (self.__round + 1, len(new_set_stone), self.__lobby_id))

                await cursor.execute("""
                           INSERT INTO lobby_%s.\"stones_list\" (round_num, stones) VALUES (
                           %s,
                           '%s')
                           """ % (self.__lobby_id, self.__round + 1, ','.join(list(map(str, new_set_stone)))))

                self.__round += 1
                self.__stones_cnt = len(new_set_stone)
                self.__stones_set[self.__round] = new_set_stone
            except DatabaseError as e:
                await conn.rollback()
                raise ActionException(e.sqlstate) from e
            except Exception as e:
                await conn.rollback()
                raise ActionException() from e
            finally:
                await cursor.close()
            await conn.commit()

    def stones_left(self) -> int:
        """
        Returns the round number of this game.
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        return len(self.__stones_set[self.__round])

    async def fake_namings(self, user_id: int) -> dict[int, int]:
        """
        Returns fake namings for players like user_id see them.
        :param user_id:
        :return:
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        if user_id not in list(map(lambda x: x.id, await self.users())):
            raise ActionException(_NO_SUCH_ELEMENT)
        result = await do_request("""
               SELECT * FROM lobby_%s.\"player_namings\" where player_id = %s;""" % (self.__lobby_id, user_id,))
        user_list = await self.users()
        return {user.id: result[0][i + 1] for i, user in enumerate(user_list)}

    async def field_for_user(self, user) -> dict[int, tuple[bool, list[int]]]:
        """
        Returns the field for a user.
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        if user.id not in list(map(lambda x: x.id, await self.users())):
            raise ActionException(_NO_SUCH_ELEMENT)
        result = {stone_id + 1: (False, []) for stone_id in range(self.__stones_cnt)}
        choices = await do_request("""
                       SELECT stone_id, player_id FROM lobby_%s.\"logs\" where round_number = %s;""" % (
            self.__lobby_id, max(self.__round - 1, 0)))
        fake_namings = await self.fake_namings(user.id)
        if choices:
            for stone_id in self.__stones_set[self.__round - 1]:
                result[stone_id] = (False, list(map(lambda x: fake_namings[x[1]], filter(lambda x: x[0] == stone_id and x[1] != user.id,
                                                                                         choices))))
        user_log = list(filter(lambda x: x[1] == user.id, choices))
        if not user_log:
            raise ActionException()
        choice = user_log[0]
        if choice and choice[0] is not None:
            result[choice[0]] = (True, result[choice[0]][1])
        return result

    async def get_logs(self) -> str:
        """
        Creates logs files .csv
        :return: filepath
        """
        path = os.path.join(f'{os.getenv('TEMP_DIR')}/logs_{self.__lobby_id}_{time.time()}.csv')
        result = await do_request("SELECT * FROM lobby_%s.\"logs\";" % (self.__lobby_id,))
        pd.DataFrame(result, columns=["date_time", "player_id", "stone_id", "round_number"]).to_csv(path)
        return path

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
        return self.__stones_set[self.__round]

    def __str__(self):
        return f'Lobby {self.__lobby_id} with {self.__num_players} players and {self.__stones_cnt} stones and {self.__round} round and status {self.__status}'


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
            logging.debug(f"User with id {user_id} already exists")
            return cls.__instances[user_id]

        logging.debug(f"User {user_id} created")
        instance = super(User, cls).__new__(cls)
        cls.__instances[user_id] = instance
        return instance

    @classmethod
    async def add_or_get(cls, tg_id: int):
        """
        Returns User object with given tg_id or creates it in database
        """
        result = await do_request("""
        SELECT * FROM public.\"user\"
        WHERE tg_id = %s;
        """ % (tg_id,))

        if len(result) == 0:
            result = await do_request("""
            INSERT INTO public.\"user\" (tg_id)
            VALUES (%s) RETURNING *;""" % (tg_id,))

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

    def set_lobby(self, lobby: Lobby):
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
        if status not in ['player', 'admin']:
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
        WHERE player_id = %s;""" % (self.__current_lobby_id, self.__tg_id))

    async def choose_stone(self, stone_id: int):
        """
        Chooses stone with stone_id
        """
        if hasattr(self, '__database_consistent'):
            raise ActionException(_NOT_SYNCHRONIZED_WITH_DATABASE)
        if self.__deleted:
            raise ActionException(_DATA_DELETED)
        if await self.lobby() is None:
            raise ActionException(_NOT_IN_LOBBY)
        if self.chosen_stone is not None:
            raise ActionException(_ALREADY_CHOSEN_STONE)
        if (await self.lobby()).status() != 'started':
            raise ActionException(_GAME_IS_NOT_RUNNING)
        if stone_id not in (await self.lobby()).stones_set():
            raise ActionException(_NO_SUCH_ELEMENT)
        self.chosen_stone = stone_id
        await do_request("""
        UPDATE lobby_%s.\"logs\"
        SET stone_id = %s
        WHERE player_id = %s;""" % (self.__current_lobby_id, stone_id, self.__tg_id))

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


async def main():
    await init_pool()
    init_exceptions()
    lobby = await Lobby.get_lobby(6)
    print(lobby)
    print(lobby.stones_set())
    print(lobby.stones_left())
    # lobby = await Lobby.make_lobby(5)
    # user = await User.add_or_get(123)
    # user4 = await User.add_or_get(12356)
    # await user4.set_status('admin')
    # user2 = await User.add_or_get(1234)
    # user3 = await User.add_or_get(12345)
    #
    # await lobby.join_user(user)
    # await lobby.join_user(user4)
    # await lobby.join_user(user2)
    # await lobby.join_user(user3)
    #
    # await lobby.start_game()
    #
    # await user.leave_stone()
    # await user.choose_stone(4)
    # await user2.leave_stone()
    # await user2.choose_stone(2)
    # await user3.choose_stone(4)
    # await user3.leave_stone()
    # await user3.choose_stone(2)
    # #
    # await lobby.end_round()
    # print(await lobby.field_for_user(user))
    # print(await lobby.field_for_user(user2))
    # print(await lobby.field_for_user(user3))
    #
    # await lobby.end_round()
    # print(await lobby.field_for_user(user))
    # print(await lobby.field_for_user(user2))
    # print(await lobby.field_for_user(user3))
    # #print(await lobby.field_for_user(user4))
    # print(lobby)

    #await lobby.end_game()
    #print(lobby)

    return


load_dotenv()
if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
    print("Done")
