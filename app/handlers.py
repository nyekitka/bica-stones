from aiogram import types, F, Router
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command, CommandStart, CommandObject

router = Router()

@router.message(CommandStart())
async def start(message: types.Message):
    await message.answer('Привет')