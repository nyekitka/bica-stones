import asyncio
import logging
import os
from typing import Optional

import psycopg
import psycopg_pool
from dotenv import load_dotenv

load_dotenv()

dsn = "dbname=%s user=%s password=%s host=%s port=%s" % (
    os.getenv("POSTGRES_DB"),
    os.getenv("PG_USER"),
    os.getenv("POSTGRES_PASSWORD"),
    os.getenv("POSTGRES_HOST"),
    os.getenv("POSTGRES_PORT"),
)

connection_pool = psycopg_pool.AsyncConnectionPool(
        conninfo=dsn,
        min_size=os.cpu_count(),
        max_size=max(int(os.getenv("POSTGRES_MAX_CONNECTIONS")) - 10, os.cpu_count()),
        open=False,
    )


async def init_pool():
    await connection_pool.open()
    logging.info("Connection pool initialized")


async def do_request(request: str) -> Optional[list]:
    async with connection_pool.connection() as conn:
        cursor = conn.cursor()
        try:
            await cursor.execute(request)
            result = await cursor.fetchall()
        except psycopg.ProgrammingError as e:
            if str(e) == "the last operation didn't produce a result":
                return None
            logging.error(e)
            await conn.rollback()
            raise e
        except Exception as e:
            logging.error(e)
            await conn.rollback()
            raise e
        finally:
            await cursor.close()

        await conn.commit()
    return result




