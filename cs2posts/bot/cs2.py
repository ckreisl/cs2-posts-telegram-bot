from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ChatType
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.error import ChatMigrated
from telegram.error import Forbidden
from telegram.ext import Application
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import ContextTypes
from telegram.ext import filters
from telegram.ext import MessageHandler

import cs2posts.bot.constants as const
from cs2posts.bot import settings
from cs2posts.bot.chats import Chat
from cs2posts.bot.message import TelegramMessage
from cs2posts.bot.message import TelegramMessageFactory
from cs2posts.bot.options import Options
from cs2posts.bot.spam import SpamProtector
from cs2posts.crawler import CounterStrike2Crawler
from cs2posts.cs2 import CounterStrike2Posts
from cs2posts.db import ChatDatabase
from cs2posts.db import PostDatabase
from cs2posts.post import Post


logger = logging.getLogger(__name__)


def admin(func):
    async def wrapper(self, update: Update, context: CallbackContext):
        chat = self.chat_db.get(chat_id=update.message.chat_id)
        if chat is None:
            return
        if update.message.from_user.id != chat.chat_id_admin:
            logger.warning(
                f'Unauthorized access to {func.__name__} by {update.message.from_user.id}')
            return
        return await func(self, update, context)
    return wrapper


def spam_protected(func):
    async def wrapper(self, update: Update, context: CallbackContext):
        chat = self.chat_db.get(update.message.chat_id)
        await self.spam_protector.check(context.bot, chat)
        if chat is not None and chat.is_banned:
            return
        if chat is not None:
            self.chat_db.update(chat)
        return await func(self, update, context)
    return wrapper


class CounterStrike2UpdateBot:

    def __init__(self, *args, **kwargs) -> None:
        self.app = (Application.builder()
                    .post_init(self.post_init)
                    .post_shutdown(self.post_shutdown)
                    .token(kwargs['token'])
                    .build())

        self.crawler: CounterStrike2Crawler = kwargs['crawler']
        self.spam_protector: SpamProtector = kwargs['spam_protector']
        self.post_db: PostDatabase = kwargs['post_db']
        self.chat_db: ChatDatabase = kwargs['chat_db']

        self.options = Options(app=self.app)

        self.app.add_handlers([
            CommandHandler('start', self.start),
            CommandHandler('stop', self.stop),
            CommandHandler('help', self.help),
            CommandHandler('news', self.news),
            CommandHandler('update', self.update),
            CommandHandler('external', self.external),
            CommandHandler('latest', self.latest),
            MessageHandler(
                filters.StatusUpdate.NEW_CHAT_MEMBERS, self.new_chat_member),
            MessageHandler(
                filters.StatusUpdate.LEFT_CHAT_MEMBER, self.left_chat_member),
            MessageHandler(
                filters.StatusUpdate.MIGRATE, self.migrate_chat),
        ])

        # self.app.add_error_handler(self.error)
        self.is_running = False
        self.__init_data()

    def __init_data(self) -> None:

        if self.post_db.is_empty():
            # TODO: Maybe ensure that there is a latest update and news post
            # As of now we just fetch 100 items.
            logger.info('No post data found. Fetching latest posts...')
            # TODO: What happens here if crawler fails?
            data = self.crawler.crawl()
            posts = CounterStrike2Posts(data)
            self.post_db.save(posts.latest_update_post)
            self.post_db.save(posts.latest_news_post)
            self.post_db.save(posts.latest_external_post)

        self.latest_post: Post = self.post_db.get_latest_post()
        self.latest_news_post: Post = self.post_db.get_latest_news_post()
        self.latest_update_post: Post = self.post_db.get_latest_update_post()
        self.latest_external_post: Post = self.post_db.get_latest_external_post()
        self.options.set_chat_db(self.chat_db)

    async def post_init(self, application: Application) -> None:
        logger.info('Post init bot...')
        # Bot username is only available after initialization
        self.username = application.bot.username
        logger.info(f'Bot username: {self.username}. Bot is ready.')

    async def post_shutdown(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info('Shutting down bot...')
        # saving chats or posts not requires anymore
        # since we directly operatoe on the database
        # Keep function for future use

    async def new_chat_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info(f'New chat member {update.message.new_chat_members} ...')
        logger.info(f"Username: {update.message.from_user.username}")

        for member in update.message.new_chat_members:
            if member.username != self.username:
                continue

            logger.info(f'Bot joined chat {update.message.chat_id} ...')

            chat = self.chat_db.get(update.message.chat_id)
            if chat is None:
                logger.info('Chat not found. Creating new chat...')
                chat = Chat(update.message.chat_id)

            chat.chat_id_admin = update.message.from_user.id
            self.chat_db.add(chat)

    async def left_chat_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info(f'Left chat member {update.message.left_chat_member} ...')

        if update.message.left_chat_member.username != self.username:
            return

        logger.info(f'Bot left chat {update.message.chat_id} ...')

        chat = self.chat_db.get(update.message.chat_id)
        if chat is None:
            return

        logger.info('Removing chat from chat list...')
        self.chat_db.remove(chat)

    async def migrate_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message.migrate_from_chat_id is None:
            # Someone two events are fired for the same chat migration
            # ignore the second event where migrate_from_chat_id is None
            return

        logger.info(
            f'Migrating chat from {update.message.migrate_from_chat_id} to {update.message.chat_id} ...')

        chat = self.chat_db.get(update.message.migrate_from_chat_id)
        if chat is None:
            if self.chat_db.get(update.message.chat_id) is not None:
                logger.info('Chat already migrated. Nothing to do.')
                return
            return

        logger.info(f'Chat migrated to {update.message.chat_id} ...')
        self.chat_db.migrate(chat, update.message.chat_id)
        logger.info("Chat migrated successfully.")

    @spam_protected
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info(f'Starting bot for chat_id={update.message.chat_id} ...')

        chat_id = update.message.chat_id
        chat = self.chat_db.get(chat_id=chat_id)

        if chat is None:
            chat = Chat(chat_id)
            chat.chat_id_admin = update.message.from_user.id
            self.spam_protector.update_chat_activity(chat)
            self.chat_db.add(chat)

        if not chat.is_running:
            chat.is_running = True
            await update.message.reply_text(
                text=const.WELCOME_MESSAGE_ENGLISH,
                parse_mode=ParseMode.HTML)
            self.chat_db.update(chat)
        else:
            await update.message.reply_text(
                'Bot is already running for your chat!')

        if chat.is_removed_while_banned:
            chat.is_removed_while_banned = False
            self.chat_db.update(chat)

        if self.is_running:
            return

        # Check for posts every X seconds
        context.job_queue.run_repeating(
            callback=self.post_checker,
            interval=settings.CS2_UPDATE_CHECK_INTERVAL)

        self.is_running = True

    @spam_protected
    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info(f'Stopping bot for chat_id={update.message.chat_id} ...')

        chat = self.chat_db.get(update.message.chat_id)
        if chat is None:
            logger.info('Chat not found. Nothing to do.')
            return

        chat_type = update.message.chat.type
        if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:
            chat.is_running = False
            self.chat_db.update(chat)
            await update.message.reply_text(
                'Bot is stopped for this chat. You can start it again with /start')
            # We do not remove the chat here, because we want to keep the chat
            # and only remove it if the bot is removed from the group chat.
            return

        if chat_type == ChatType.PRIVATE:
            self.chat_db.remove(chat)
            return

    @spam_protected
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info(
            f'Sending help message to chat_id={update.message.chat_id} ...')

        chat = self.chat_db.get(update.message.chat_id)
        if chat is None:
            logger.error('Chat not found. Not sending help message.')
            return

        msg = ("/start - Starts the bot\n"
               "/stop - Stops the bot for this chat\n"
               "/latest - Sends the latest post\n"
               "/news - Sends the latest news post\n"
               "/update - Sends the latest update post\n"
               "/external - Sends the latest external post\n"
               "/help - Prints this help message\n"
               "/options - Configure Options <b>(only admins)</b>")

        await update.message.reply_text(text=msg, parse_mode=ParseMode.HTML)

    @spam_protected
    async def latest(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info('Sending latest saved post to chat ...')
        chat = self.chat_db.get(update.message.chat_id)
        msg = TelegramMessageFactory.create(self.latest_post)
        await self.send_message(context=context, msg=msg, chat=chat)

    @spam_protected
    async def news(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info('Sending latest news post to chat ...')
        chat = self.chat_db.get(update.message.chat_id)
        msg = TelegramMessageFactory.create(self.latest_news_post)
        await self.send_message(context=context, msg=msg, chat=chat)

    @spam_protected
    async def update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info('Sending latest update post to chats ...')
        chat = self.chat_db.get(update.message.chat_id)
        msg = TelegramMessageFactory.create(self.latest_update_post)
        await self.send_message(context=context, msg=msg, chat=chat)

    @spam_protected
    async def external(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info('Sending latest external post to chat ...')
        chat = self.chat_db.get(update.message.chat_id)
        msg = TelegramMessageFactory.create(self.latest_external_post)
        await self.send_message(context=context, msg=msg, chat=chat)

    async def _post_checker_news(self, context: CallbackContext, post: Post) -> None:
        if post is None:
            return

        if not post.is_newer_than(self.latest_news_post):
            logger.info(
                f'No new news post found latest_news_post=[{post.title}]')
            return

        logger.info(
            f'New news post found latest_news_post=[{post.title}]')

        self.latest_news_post = post
        await self.send_post_to_chats(context, post=post)

    async def _post_checker_update(self, context: CallbackContext, post: Post) -> None:
        if post is None:
            return

        if not post.is_newer_than(self.latest_update_post):
            logger.info(
                f'No new update post found latest_update_post=[{post.title}]')
            return

        logger.info(
            f'New update post found latest_update_post=[{post.title}]')

        self.latest_update_post = post
        await self.send_post_to_chats(context, post=post)

    async def _post_checker_external(self, context: CallbackContext, post: Post) -> None:
        if post is None:
            logger.info(
                f'No external {post=} found latest_external_post=[{self.latest_external_post.title}]')
            return

        if not post.is_newer_than(self.latest_external_post):
            logger.info(
                f'No new external post found latest_external_post=[{post.title}]')
            return

        logger.info(
            f'New external post found latest_external_post=[{post.title}]')

        self.latest_external_post = post
        await self.send_post_to_chats(context, post=post)

    async def post_checker(self, context: CallbackContext) -> None:
        logger.info('Crawling latest posts ...')
        try:
            data = self.crawler.crawl(count=10)
        except Exception as e:
            logger.error(f'Could not fetch latest posts: {e}')
            return

        posts = CounterStrike2Posts.create(data)

        if posts.is_empty():
            logger.info(f'No post(s) found in latest crawl: {posts}')
            return

        latest_news_post = posts.latest_news_post
        latest_update_post = posts.latest_update_post
        latest_external_post = posts.latest_external_post

        await self._post_checker_news(context, latest_news_post)
        await self._post_checker_update(context, latest_update_post)
        await self._post_checker_external(context, latest_external_post)

        self.latest_post = self.latest_post if self.latest_post.is_older_eq_than(
            posts.latest) else posts.latest

    async def send_post_to_chats(self, context: CallbackContext, post: Post) -> None:
        logger.info('Sending post to chats ...')

        # Send to all chats that are interested in the post type
        if post.is_news():
            chats = self.chat_db.get_running_and_interested_in_news_chats()
        elif post.is_update():
            chats = self.chat_db.get_running_and_interested_in_updates_chats()
        elif post.is_external():
            chats = self.chat_db.get_running_and_interested_in_external_news_chats()
        else:
            logger.error(
                f'Unknown post type {post.to_dict()}. Not sending any message.')
            return

        msg = TelegramMessageFactory.create(post=post)

        for chat in chats:
            await self.send_message(context=context, msg=msg, chat=chat)

    async def send_message(self, context: CallbackContext, msg: TelegramMessage, chat: Chat) -> None:

        if chat is None:
            logger.error('Chat is None. Not sending any message.')
            return

        try:
            await msg.send(context.bot, chat_id=chat.chat_id)
        except BadRequest as e:
            logger.error(f'Bad request for {chat.chat_id=}')
            if e.message == 'Chat not found':
                logger.error(
                    f'Chat not found we delete the chat {chat.chat_id=}')
                self.chat_db.remove(chat)
            logger.error(f"Reason: {e}")
        except Forbidden as e:
            logger.error(
                f'Bot is blocked by user we delete the chat {chat.chat_id=}')
            logger.error(f"Reason: {e}")
            self.chat_db.remove(chat)
        except ChatMigrated as e:
            logger.error(
                f'Chat migrated we update the chat {chat.chat_id=}')
            logger.error(f"Reason: {e}")
            chat = self.chat_db.migrate(chat, e.new_chat_id)
            await self.send_message(context, msg, chat)
        except Exception as e:
            logger.exception(f'Could not send message to chat {chat.chat_id=}')
            logger.exception(f"Reason: {e}")

    async def error(self, update: Update, context: CallbackContext) -> None:
        logger.error(f'Update {update} caused error {context.error}')
        # TODO: Implement clean error handling

    def run(self) -> None:
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)
