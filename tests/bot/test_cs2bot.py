from __future__ import annotations

from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from telegram import Update
from telegram.constants import ChatType
from telegram.error import BadRequest
from telegram.error import Forbidden

from cs2posts.bot.chats import Chat
from cs2posts.bot.cs2 import CounterStrike2UpdateBot
from cs2posts.post import Post


def create_update_post():
    return Post(gid="1337",
                title="Update Post",
                url="http://test.com",
                is_external_url=True,
                author="Test author",
                contents="Test body",
                feedlabel="Test label",
                feedname="Test feed",
                date=1234567890,
                feed_type=1,
                appid=730,
                tags=["patchnotes"],)


def create_news_post():
    return Post(gid="gid",
                title="title",
                url="url",
                is_external_url=True,
                author="author",
                contents="contents",
                feedlabel="feedlabel",
                feedname="feedname",
                date=1234567890,
                feed_type=1,
                appid=730)


@pytest.fixture
@patch('cs2posts.bot.spam.SpamProtector')
@patch('cs2posts.store.LocalChatStore')
@patch('cs2posts.store.LocalLatestPostStore')
@patch('cs2posts.crawler.CounterStrike2Crawler')
def bot(mocked_crawler, mocked_post_store, mocked_chat_store, mocked_spam_protector):
    mocked_spam_protector.check = AsyncMock()
    mocked_spam_protector.strike = AsyncMock()
    bot = CounterStrike2UpdateBot(
        token='test_token',
        local_chat_store=mocked_chat_store,
        local_post_store=mocked_post_store,
        crawler=mocked_crawler,
        spam_protector=mocked_spam_protector)
    bot.chats = Mock()
    return bot


def test_cs2_bot_init_no_files(bot):
    bot.local_chat_store.is_empty.return_value = True
    bot.local_chat_store.is_empty.assert_called()
    bot.local_chat_store.save.assert_called()

    bot.local_post_store.is_empty.return_value = True
    bot.local_post_store.is_empty.assert_called()
    bot.crawler.crawl.assert_called()
    bot.local_post_store.save.assert_called()
    bot.local_chat_store.save.assert_called()

    # TODO finish up setup


@pytest.mark.asyncio
async def test_cs2_bot_post_init(bot):
    mocked_app = AsyncMock()
    mocked_app.bot.username = "test_bot"
    await bot.post_init(mocked_app)
    assert bot.username == "test_bot"


@pytest.mark.asyncio
async def test_cs2_bot_post_shutdown(bot):
    mocked_context = AsyncMock()
    bot.latest_news_post = create_news_post()
    bot.latest_update_post = create_update_post()

    bot.local_post_store.save.reset_mock()
    bot.local_chat_store.save.reset_mock()
    await bot.post_shutdown(mocked_context)

    assert bot.local_post_store.save.call_count == 2
    assert bot.local_chat_store.save.call_count == 1


@pytest.mark.asyncio
async def test_cs2_bot_new_chat_member_bot_added(bot):
    mocked_context = AsyncMock()
    mocked_update = AsyncMock()

    bot.username = 'myBotName'
    mocked_member = AsyncMock()
    mocked_member.username = bot.username
    mocked_update.message.new_chat_members = [mocked_member]
    mocked_update.message.chat_id = 42
    mocked_update.message.from_user.id = 1337
    bot.chats.get.return_value = None

    chat = Chat(42)
    chat.chat_id_admin = None

    bot.chats.create_and_add.return_value = chat

    await bot.new_chat_member(mocked_update, mocked_context)

    bot.chats.get.assert_called_once_with(42)
    bot.chats.create_and_add.assert_called_once_with(chat_id=42)
    bot.local_chat_store.save.assert_called()

    assert chat.chat_id_admin == 1337


@pytest.mark.asyncio
async def test_cs2_bot_new_chat_member_not_bot_added(bot):
    mocked_context = AsyncMock()
    mocked_update = AsyncMock()

    bot.username = 'myBotName'
    mocked_member = AsyncMock()
    mocked_member.username = 'notTheBotsUsername'
    mocked_update.message.new_chat_members = [mocked_member]

    bot.local_chat_store.reset_mock()
    await bot.new_chat_member(mocked_update, mocked_context)

    bot.chats.get.assert_not_called()
    bot.chats.create_and_add.assert_not_called()
    bot.local_chat_store.save.assert_not_called()


@pytest.mark.asyncio
async def test_cs2_bot_left_chat_member_bot_left(bot):
    mocked_context = AsyncMock()
    mocked_update = AsyncMock()

    bot.username = 'myBotName'
    mocked_update.message.left_chat_member.username = bot.username
    mocked_update.message.chat_id = 42
    mocked_update.message.from_user.id = 1337
    bot.chats.get.return_value = None

    await bot.left_chat_member(mocked_update, mocked_context)
    bot.chats.get.assert_called_once_with(42)

    chat = Chat(42)
    bot.chats.get.return_value = chat

    bot.local_chat_store.reset_mock()
    await bot.left_chat_member(mocked_update, mocked_context)

    bot.chats.remove.assert_called_once_with(chat)
    bot.local_chat_store.save.assert_called_once()


@pytest.mark.asyncio
async def test_cs2_bot_left_chat_member_not_bot_left(bot):
    mocked_context = AsyncMock()
    mocked_update = AsyncMock()

    bot.username = 'myBotName'
    mocked_update.message.left_chat_member.username = "notTheBotsUsername"
    mocked_update.message.chat_id = 42
    mocked_update.message.from_user.id = 1337
    bot.chats.get.return_value = None

    await bot.left_chat_member(mocked_update, mocked_context)

    bot.chats.get.assert_not_called()
    bot.chats.remove.assert_not_called()


@pytest.mark.asyncio
async def test_cs2_bot_start_command_new_user(bot):
    mocked_context = AsyncMock()
    mocked_context.bot = AsyncMock()
    mocked_context.job_queue = Mock()
    mocked_update = AsyncMock()
    mocked_update.message.chat_id = 42
    mocked_update.message.from_user.id = 42

    chat = Chat(42)
    bot.is_running = False
    bot.chats.get.return_value = None
    bot.chats.create_and_add.return_value = chat

    bot.local_chat_store.reset_mock()
    await bot.start(mocked_update, mocked_context)

    bot.chats.create_and_add.assert_called_once_with(chat_id=chat.chat_id)
    bot.local_chat_store.save.call_count == 2
    bot.spam_protector.update_chat_activity.assert_called_once_with(chat)
    assert chat.chat_id_admin == mocked_update.message.from_user.id

    assert chat.is_running
    mocked_update.message.reply_text.assert_called_once()

    mocked_context.job_queue.run_repeating.assert_called_once()
    assert bot.is_running


@pytest.mark.asyncio
async def test_cs2_bot_start_command_existing_user(bot):
    mocked_context = AsyncMock()
    mocked_context.bot = AsyncMock()
    mocked_context.job_queue = Mock()
    mocked_update = AsyncMock()
    mocked_update.message.chat_id = 42
    mocked_update.message.from_user.id = 42

    chat = Chat(42)
    chat.is_running = True
    chat.is_removed_while_banned = True
    bot.is_running = True
    bot.chats.get.return_value = chat

    bot.local_chat_store.reset_mock()
    await bot.start(mocked_update, mocked_context)

    bot.chats.create_and_add.assert_not_called()
    bot.local_chat_store.save.assert_not_called()
    mocked_update.message.reply_text.assert_called_once()

    mocked_context.job_queue.run_repeating.assert_not_called()
    assert chat.is_removed_while_banned is False


@pytest.mark.asyncio
async def test_cs2_bot_stop_command_chat_none(bot):
    mocked_context = AsyncMock()
    mocked_update = AsyncMock()
    mocked_update.message.chat_id = 42

    bot.chats.get.return_value = None
    bot.local_chat_store.reset_mock()
    await bot.stop(mocked_update, mocked_context)

    bot.chats.get.assert_called_with(42)

    mocked_update.message.reply_text.assert_not_called()
    bot.chats.remove.assert_not_called()
    bot.local_chat_store.save.assert_not_called()


@pytest.mark.asyncio
async def test_cs2_bot_stop_command_chat_is_banned(bot):
    mocked_context = AsyncMock()
    mocked_update = AsyncMock()

    chat = Chat(42)
    chat.is_banned = True
    bot.chats.get.return_value = chat

    bot.local_chat_store.reset_mock()
    await bot.stop(mocked_update, mocked_context)

    mocked_update.message.reply_text.assert_not_called()
    bot.chats.remove.assert_not_called()
    bot.local_chat_store.save.assert_not_called()


@pytest.mark.asyncio
async def test_cs2_bot_stop_command_chat_is_group(bot):
    mocked_context = AsyncMock()
    mocked_update = AsyncMock()
    mocked_update.message.chat.type = ChatType.GROUP

    chat = Chat(42)
    bot.chats.get.return_value = chat

    bot.local_chat_store.reset_mock()
    await bot.stop(mocked_update, mocked_context)

    assert chat.is_running is False

    mocked_update.message.reply_text.assert_called_once()
    bot.chats.remove.assert_not_called()
    bot.local_chat_store.save.assert_not_called()


@pytest.mark.asyncio
async def test_cs2_bot_stop_command_chat_is_private(bot):
    mocked_context = AsyncMock()
    mocked_update = AsyncMock()
    mocked_update.message.chat.type = ChatType.PRIVATE

    chat = Chat(42)
    bot.chats.get.return_value = chat

    bot.local_chat_store.reset_mock()
    await bot.stop(mocked_update, mocked_context)

    mocked_update.message.reply_text.assert_not_called()
    bot.chats.remove.assert_called_once_with(chat)
    bot.local_chat_store.save.assert_called_once()


@pytest.mark.asyncio
async def test_cs2_bot_help_command(bot):
    mocked_context = AsyncMock()
    mocked_update = AsyncMock()

    bot.chats.get.return_value = None

    await bot.help(mocked_update, mocked_context)

    mocked_update.message.reply_text.assert_not_called()
    bot.chats.get.return_value = Chat(42)

    await bot.help(mocked_update, mocked_context)

    mocked_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_cs2_bot_latest_command(bot):
    mocked_context = AsyncMock()
    mocked_update = AsyncMock()

    chat = Chat(42)
    bot.chats.get.return_value = chat
    bot.latest_post = Mock()

    with patch('cs2posts.bot.message.TelegramMessageFactory.create') as mocked_factory:
        mocked_msg = Mock()
        mocked_factory.return_value = mocked_msg
        bot.send_message = AsyncMock()
        await bot.latest(mocked_update, mocked_context)
        mocked_factory.assert_called_once_with(bot.latest_post)
        bot.send_message.assert_called_once_with(
            context=mocked_context, msg=mocked_msg, chat=chat)


@pytest.mark.asyncio
async def test_cs2_bot_news_command(bot):
    mocked_context = AsyncMock()
    mocked_update = AsyncMock()

    chat = Chat(42)
    bot.chats.get.return_value = chat
    bot.latest_news_post = Mock()

    with patch('cs2posts.bot.message.TelegramMessageFactory.create') as mocked_factory:
        mocked_msg = Mock()
        mocked_factory.return_value = mocked_msg
        bot.send_message = AsyncMock()
        await bot.news(mocked_update, mocked_context)
        mocked_factory.assert_called_once_with(bot.latest_news_post)
        bot.send_message.assert_called_once_with(
            context=mocked_context, msg=mocked_msg, chat=chat)


@pytest.mark.asyncio
async def test_cs2_bot_update_command(bot):
    mocked_context = AsyncMock()
    mocked_update = AsyncMock()

    chat = Chat(42)
    bot.chats.get.return_value = chat
    bot.latest_update_post = Mock()

    with patch('cs2posts.bot.message.TelegramMessageFactory.create') as mocked_factory:
        mocked_msg = Mock()
        mocked_factory.return_value = mocked_msg
        bot.send_message = AsyncMock()
        await bot.update(mocked_update, mocked_context)
        mocked_factory.assert_called_once_with(bot.latest_update_post)
        bot.send_message.assert_called_once_with(
            context=mocked_context, msg=mocked_msg, chat=chat)


@pytest.mark.asyncio
async def test_cs2_bot_post_checker_crawler_exception(bot):
    mocked_context = AsyncMock()
    bot.crawler.crawl.side_effect = Exception("Exception")

    bot._post_checker_news = AsyncMock()
    bot._post_checker_update = AsyncMock()
    await bot.post_checker(context=mocked_context)
    bot._post_checker_news.assert_not_awaited()
    bot._post_checker_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_cs2_bot_post_checker_posts_empty(bot):
    # TODO
    pass


@pytest.mark.asyncio
async def test_cs2_bot_post_checker_new_news_post(bot):
    # TODO
    pass


@pytest.mark.asyncio
async def test_cs2_bot_post_checker_new_update_post(bot):
    # TODO
    pass


@pytest.mark.asyncio
async def test_cs2_bot_post_checker_new_news_and_update_post(bot):
    # TODO
    pass


@pytest.mark.asyncio
async def test_cs2_bot_send_news_post_to_chats(bot):
    mocked_context = AsyncMock()
    mocked_post = Mock()
    mocked_post.is_news.return_value = True
    bot.chats.get_running_and_interested_in_news.return_value = [Chat(13)]
    bot.send_message = AsyncMock()

    with patch('cs2posts.bot.message.TelegramMessageFactory.create') as mocked_factory:
        mocked_msg = Mock()
        mocked_factory.return_value = mocked_msg
        await bot.send_post_to_chats(mocked_context, mocked_post)
        bot.chats.get_running_and_interested_in_news.assert_called_once()
        bot.chats.get_running_and_interested_in_updates.assert_not_called()
        mocked_factory.assert_called_once_with(post=mocked_post)
        bot.send_message.assert_called_with(
            context=mocked_context, msg=mocked_msg, chat=Chat(13))


@pytest.mark.asyncio
async def test_cs2_bot_send_update_post_to_chats(bot):
    mocked_context = AsyncMock()
    mocked_post = Mock()
    mocked_post.is_news.return_value = False
    mocked_post.is_update.return_value = True
    bot.chats.get_running_and_interested_in_updates.return_value = [Chat(13)]
    bot.send_message = AsyncMock()

    with patch('cs2posts.bot.message.TelegramMessageFactory.create') as mocked_factory:
        mocked_msg = Mock()
        mocked_factory.return_value = mocked_msg
        await bot.send_post_to_chats(mocked_context, mocked_post)
        bot.chats.get_running_and_interested_in_updates.assert_called_once()
        bot.chats.get_running_and_interested_in_news.assert_not_called()
        mocked_factory.assert_called_once_with(post=mocked_post)
        bot.send_message.assert_called_with(
            context=mocked_context, msg=mocked_msg, chat=Chat(13))


@pytest.mark.asyncio
async def test_cs2_bot_send_unknown_post_to_chats(bot):
    mocked_context = AsyncMock()
    mocked_post = Mock()
    mocked_post.is_news.return_value = False
    mocked_post.is_update.return_value = False
    mocked_post.is_external.return_value = False
    bot.send_message = AsyncMock()

    with patch('cs2posts.bot.message.TelegramMessageFactory.create') as mocked_factory:
        await bot.send_post_to_chats(mocked_context, mocked_post)
        bot.chats.get_running_and_interested_in_updates.assert_not_called()
        bot.chats.get_running_and_interested_in_news.assert_not_called()
        mocked_factory.assert_not_called()
        bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_cs2_bot_send_message_chat_is_none(bot):
    mocked_context = AsyncMock()
    mocked_msg = AsyncMock()

    await bot.send_message(mocked_context, mocked_msg, None)
    mocked_msg.send.assert_not_called()


@pytest.mark.asyncio
async def test_cs2_bot_send_message(bot):
    mocked_context = AsyncMock()
    mocked_context.bot = AsyncMock()
    mocked_msg = AsyncMock()
    mocked_msg.send = AsyncMock()
    chat = Chat(42)

    await bot.send_message(mocked_context, mocked_msg, chat)
    mocked_msg.send.assert_called_once_with(
        mocked_context.bot, chat_id=chat.chat_id)
    mocked_msg.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_cs2_bot_send_message_raises_bad_request_chat_not_found(bot):
    mocked_context = AsyncMock()
    mocked_context.bot = AsyncMock()
    mocked_msg = AsyncMock()
    mocked_msg.send = AsyncMock()
    mocked_msg.send.side_effect = BadRequest("Chat not found")
    chat = Chat(42)

    await bot.send_message(mocked_context, mocked_msg, chat)
    mocked_msg.send.assert_called_once_with(
        mocked_context.bot, chat_id=chat.chat_id)
    bot.chats.remove.assert_called_once_with(chat)


@pytest.mark.asyncio
async def test_cs2_bot_send_message_raises_bad_request(bot):
    mocked_context = AsyncMock()
    mocked_context.bot = AsyncMock()
    mocked_msg = AsyncMock()
    mocked_msg.send = AsyncMock()
    mocked_msg.send.side_effect = BadRequest("something")
    chat = Chat(42)

    await bot.send_message(mocked_context, mocked_msg, chat)
    mocked_msg.send.assert_called_once_with(
        mocked_context.bot, chat_id=chat.chat_id)
    bot.chats.remove.assert_not_called()


@pytest.mark.asyncio
async def test_cs2_bot_send_message_raises_forbidden(bot):
    mocked_context = AsyncMock()
    mocked_context.bot = AsyncMock()
    mocked_msg = AsyncMock()
    mocked_msg.send = AsyncMock()
    mocked_msg.send.side_effect = Forbidden("Forbidden")
    chat = Chat(42)

    await bot.send_message(mocked_context, mocked_msg, chat)
    mocked_msg.send.assert_called_once_with(
        mocked_context.bot, chat_id=chat.chat_id)
    bot.chats.remove.assert_called_once_with(chat)


@pytest.mark.asyncio
async def test_cs2_bot_send_message_raises_exception(bot):
    mocked_context = AsyncMock()
    mocked_context.bot = AsyncMock()
    mocked_msg = AsyncMock()
    mocked_msg.send = AsyncMock()
    mocked_msg.send.side_effect = Exception("Exception")
    chat = Chat(42)

    await bot.send_message(mocked_context, mocked_msg, chat)
    mocked_msg.send.assert_called_once_with(
        mocked_context.bot, chat_id=chat.chat_id)
    bot.chats.remove.assert_not_called()


def test_cs2_bot_run(bot):
    bot.app = Mock()
    bot.run()
    bot.app.run_polling.assert_called_once_with(
        allowed_updates=Update.ALL_TYPES)
