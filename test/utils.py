from aiogram.types import User, Chat, Message
from datetime import datetime

TEST_USER = User(
    id=12345678, 
    is_bot=False,
    first_name='Никита',
    last_name='Клинов',
    username='nyekitka',
    language_code='ru-RU',
    is_premium=False,
)

TEST_USER_CHAT = Chat(
    id=87654321,
    type='private',
    username=TEST_USER.username,
    first_name=TEST_USER.first_name,
    last_name=TEST_USER.last_name
)

TEST_MESSAGE = Message(
    message_id=218959185,
    date=datetime.now(),
    chat=TEST_USER_CHAT,
    from_user=TEST_USER
)