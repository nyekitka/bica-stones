"""
Module providing class that can be used to interact with database.
"""
from typing import Optional

import json
import psycopg2.extensions as ext
from psycopg2 import DatabaseError

__exceptions_file = open('data/exceptions.json', encoding='utf-8')
Errors = json.load(__exceptions_file)
__exceptions_file.close()

class ActionException(Exception):
    """
    Exceptions that may be thrown during some action.
    """
    def __init__(self, code):
        super().__init__()
        self.code = code

    def __str__(self):
        return Errors[self.code]


class Lobby:
    """
    Class-wrapper of SQL relation "Lobby"
    """
    def __init__(self, lobby_id: int, connection: ext.connection):
        self.conn = connection
        self.cursor = self.conn.cursor()
        self.id = lobby_id

    @classmethod
    def make_lobby(cls, num_players: int, connection: ext.connection):
        """
        Creates a new lobby in the database and returns Lobby object
        """
        cursor = connection.cursor()
        cursor.execute("""INSERT INTO Lobby (num_players)
                       VALUES (%s,) RETURNING *""", (num_players, ))
        lobby_id = cursor.fetchone()[0]
        connection.commit()
        return cls(lobby_id, connection)

    def join_user(self, user_id: int):
        """
        Tries to join a given user to the lobby.
        """
        try:
            self.cursor.execute("""CALL join_user(%s, %s)""", (user_id, self.id))
        except DatabaseError as ex:
            self.conn.rollback()
            raise ActionException(ex.pgcode) from ex
        self.conn.commit()

    def number_of_players(self) -> int:
        """
        Returns a maximum number of players in this lobby.
        """
        self.cursor.execute("""SELECT num_players FROM Lobby WHERE id = %s""", (self.id, ))
        return self.cursor.fetchone()[0]

    def round(self) -> Optional[int]:
        """
        Returns the round number of this game.
        """
        self.cursor.execute("""SELECT round FROM Lobby WHERE id = %s""", (self.id, ))
        return self.cursor.fetchone()[0]

class User:
    """
    Class-wrapper of SQL relation "User"
    """
    def __init__(self, tg_id: int, connection: ext.connection):
        self.conn = connection
        self.cursor = self.conn.cursor()
        self.id = tg_id

    @classmethod
    def make_user(cls, tg_id: int, connection: ext.connection):
        """
        Adds a new user to the database.
        """
