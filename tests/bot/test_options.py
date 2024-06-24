from __future__ import annotations

from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from cs2posts.bot.chats import Chat
from cs2posts.bot.options import ButtonData
from cs2posts.bot.options import Options


@pytest.fixture
def options():
    options = Options(Mock())
    options.set_chat_db(Mock())
    return options


@pytest.mark.asyncio
@patch('cs2posts.bot.options.OptionsMessageFactory')
async def test_options(mocked_options_factory, options):
    mocked_context = AsyncMock()
    mocked_update = AsyncMock()
    mocked_update.message.from_user.id = 42

    mocked_options_factory.create.return_value = ('text', 'reply_markup')

    chat = Chat(42)
    chat.chat_id_admin = 42
    options.chats_db.get.return_value = chat

    await options.options(mocked_update, mocked_context)

    mocked_update.message.reply_text.assert_awaited_once()
    mocked_update.message.reply_text.assert_called_once_with(
        text='text', reply_markup='reply_markup', parse_mode='HTML')


@pytest.mark.asyncio
@patch('cs2posts.bot.options.OptionsMessageFactory')
async def test_options_no_admin(mocked_options_factory, options):
    mocked_context = AsyncMock()
    mocked_update = AsyncMock()
    mocked_update.message.from_user.id = 42

    chat = Chat(42)
    chat.chat_id_admin = 1337
    options.chats_db.get.return_value = chat

    await options.options(mocked_update, mocked_context)

    mocked_options_factory.assert_not_called()
    mocked_update.message.reply_text.assert_not_awaited()
    mocked_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
@patch('cs2posts.bot.options.OptionsMessageFactory')
async def test_options_no_valid_chat(mocked_options_factory, options):
    mocked_context = AsyncMock()
    mocked_update = AsyncMock()
    mocked_update.message.from_user.id = 42

    options.chats_db.get.return_value = None

    await options.options(mocked_update, mocked_context)

    mocked_options_factory.assert_not_called()
    mocked_update.message.reply_text.assert_not_awaited()
    mocked_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_options_buttons_no_chat_no_admin(options):
    mocked_context = AsyncMock()
    mocked_update = AsyncMock()
    mocked_update.callback_query.from_user.id = 1337

    options.update = AsyncMock()
    options.chats_db.get.return_value = None

    await options.button(mocked_update, mocked_context)

    mocked_update.callback_query.answer.assert_called_once()

    chat = Chat(42)
    chat.chat_id_admin = 1
    options.chats_db.get.return_value = chat

    await options.button(mocked_update, mocked_context)

    mocked_update.callback_query.answer.assert_called()

    options.update.assert_not_awaited()
    options.update.assert_not_called()


@pytest.mark.asyncio
async def test_options_buttons_close(options):
    mocked_context = AsyncMock()
    mocked_update = AsyncMock()
    mocked_update.callback_query.from_user.id = 42
    mocked_update.callback_query.data = ButtonData.CLOSE

    chat = Chat(42)
    chat.chat_id_admin = 42
    options.chats_db.get.return_value = chat

    options.close = AsyncMock()
    await options.button(mocked_update, mocked_context)

    mocked_update.callback_query.answer.assert_called_once()
    options.close.assert_awaited_once()
    options.close.assert_called_once_with(mocked_update, mocked_context)


@pytest.mark.asyncio
async def test_options_buttons_update(options):
    mocked_context = AsyncMock()
    mocked_update = AsyncMock()
    mocked_update.callback_query.from_user.id = 42
    mocked_update.callback_query.data = ButtonData.UPDATE

    options.update = AsyncMock()

    chat = Chat(42)
    chat.chat_id_admin = 42
    chat.is_update_interested = True
    options.chats_db.get.return_value = chat

    await options.button(mocked_update, mocked_context)

    mocked_update.callback_query.answer.assert_called_once()
    options.chats_db.update.assert_called_once_with(chat)
    assert chat.is_update_interested is False
    options.update.assert_called_once_with(
        mocked_context, mocked_update.callback_query, chat)

    mocked_update.callback_query.answer.reset_mock()
    await options.button(mocked_update, mocked_context)

    mocked_update.callback_query.answer.assert_called_once()
    options.chats_db.update.assert_called_with(chat)
    assert chat.is_update_interested
    options.update.assert_called_with(
        mocked_context, mocked_update.callback_query, chat)


@pytest.mark.asyncio
async def test_options_buttons_news(options):
    mocked_context = AsyncMock()
    mocked_update = AsyncMock()
    mocked_update.callback_query.from_user.id = 42
    mocked_update.callback_query.data = ButtonData.NEWS

    options.update = AsyncMock()

    chat = Chat(42)
    chat.chat_id_admin = 42
    chat.is_news_interested = True
    options.chats_db.get.return_value = chat

    await options.button(mocked_update, mocked_context)

    mocked_update.callback_query.answer.assert_called_once()
    options.chats_db.update.assert_called_once_with(chat)
    assert chat.is_news_interested is False
    options.update.assert_called_once_with(
        mocked_context, mocked_update.callback_query, chat)

    mocked_update.callback_query.answer.reset_mock()
    await options.button(mocked_update, mocked_context)

    mocked_update.callback_query.answer.assert_called_once()
    options.chats_db.update.assert_called_with(chat)
    assert chat.is_news_interested
    options.update.assert_called_with(
        mocked_context, mocked_update.callback_query, chat)


@pytest.mark.asyncio
@patch('cs2posts.bot.options.OptionsMessageFactory')
async def test_options_update(mocked_msg_factory, options):
    mocked_msg_factory.create.return_value = ('text', 'reply_markup')
    mocked_context = AsyncMock()
    mocked_query = AsyncMock()
    mocked_query.message.message_id = 1337
    chat = Chat(42)

    await options.update(mocked_context, mocked_query, chat)

    mocked_context.bot.edit_message_text.assert_awaited_once()
    mocked_context.bot.edit_message_text.assert_called_once_with(
        text='text', chat_id=42, message_id=1337,
        reply_markup='reply_markup', parse_mode='HTML')


@pytest.mark.asyncio
async def test_options_close(options):
    mocked_context = AsyncMock()
    mocked_update = AsyncMock()
    mocked_update.callback_query.message.chat_id = 42
    mocked_update.callback_query.message.message_id = 1337

    await options.close(mocked_update, mocked_context)

    mocked_update.callback_query.answer.assert_called_once()
    mocked_context.bot.delete_message.assert_awaited_once()
    mocked_context.bot.delete_message.assert_called_once_with(
        chat_id=42, message_id=1337)
