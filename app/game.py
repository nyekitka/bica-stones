"""
Module providing class that can be used to interact with database.
"""
from typing import Optional

import json

from database.query import init_pool


async def main():
    await init_pool()
    pass
