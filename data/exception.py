import json
import os

Errors = {}
_UNKNOWN_ERROR = "_UNKNOWN_ERROR"
_NO_SUCH_STONE = "_NO_SUCH_STONE"
_NO_SUCH_ELEMENT = "_NO_SUCH_ELEMENT"
_NOT_IN_LOBBY = "_NOT_IN_LOBBY"
_ALREADY_CHOSEN_STONE = "_ALREADY_CHOSEN_STONE"
_GAME_IS_NOT_RUNNING = "_GAME_IS_NOT_RUNNING"
_DATA_DELETED = "_DATA_DELETED"
_ALREADY_IN_LOBBY = "_ALREADY_IN_LOBBY"
_NOT_SYNCHRONIZED_WITH_DATABASE = "_NOT_SYNCHRONIZED_WITH_DATABASE"
_GAME_IS_RUNNING = "_GAME_IS_RUNNING"
_MAX_POSSIBLE_PLAYERS = "_MAX_POSSIBLE_PLAYERS"


def init_exceptions():
    """
    Initializes exceptions.
    """
    global Errors
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "exceptions.json"), encoding='utf-8') as file:
        Errors = json.load(file)


class ActionException(Exception):
    """
    Exceptions that may be thrown during some action.
    """
    def __init__(self, code=_UNKNOWN_ERROR):
        super().__init__()
        self.code = code

    def __str__(self):
        if self.code in Errors:
            return Errors[self.code]
        return _UNKNOWN_ERROR
