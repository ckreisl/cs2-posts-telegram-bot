from __future__ import annotations

import abc
import logging

from bs4 import BeautifulSoup
from telegram.constants import ParseMode

from cs2posts.bot.constants import TELEGRAM_MAX_MESSAGE_LENGTH
from cs2posts.bot.content import ContentExtractor
from cs2posts.bot.content import Image
from cs2posts.bot.content import TextBlock
from cs2posts.bot.content import Video
from cs2posts.bot.content import Youtube
from cs2posts.bot.utils import Utils
from cs2posts.parser.steam2telegram_html import Steam2TelegramHTML
from cs2posts.parser.steam_list import SteamListParser
from cs2posts.parser.steam_update_heading import SteamUpdateHeadingParser
from cs2posts.post import Post


logger = logging.getLogger(__name__)


class TelegramMessage:

    def __init__(self, message: str) -> None:
        self.__message = message
        self.__messages = self.split(message)

    @property
    def message(self) -> str:
        return self.__message

    @property
    def messages(self) -> list[str]:
        return self.__messages

    def split(self, message: str) -> list[str]:

        if len(message) < TELEGRAM_MAX_MESSAGE_LENGTH:
            return [message]

        lines = message.split('\n')
        chunks = []
        chunk = ''

        for line in lines:
            if (len(chunk) + len(line)) < TELEGRAM_MAX_MESSAGE_LENGTH:
                chunk += line + "\n"
                continue

            chunks.append(chunk)
            chunk = line + "\n"

        chunks.append(chunk)

        return chunks

    @abc.abstractmethod
    async def send(self, bot, chat_id: int) -> None:
        raise NotImplementedError("Method not implemented")  # pragma: no cover


class CounterStrikeNewsMessage(TelegramMessage):

    def __init__(self, post: Post) -> None:
        self.post = post
        parser = Steam2TelegramHTML(post.contents)
        parser.add_parser(parser=SteamListParser, priority=1)

        self.content = ContentExtractor.extract_message_blocks(parser.parse())
        self.__add_footer()

    def __add_footer(self) -> None:
        url = Utils.get_redirected_url(self.post.url)
        footer = (
            f"\n\n(Author: {self.post.author})\n\n"
            f"Source: <a href='{url}'>Link</a>"
        )

        if isinstance(self.content[-1], TextBlock):
            self.content[-1].text += footer
        else:
            self.content.append(TextBlock(
                text_pos_start=self.content[-1].text_pos_end + 1,
                text_pos_end=len(footer),
                is_heading=False,
                text=footer))

    def get_header(self) -> str:
        return f"<b>{self.post.title}</b>\n({self.post.date_as_datetime})"

    async def send_message(self, bot, chat_id: int, message: TextBlock) -> None:
        if message.is_heading:
            message.text = self.get_header() + "\n\n" + message.text

        for text in self.split(message.text):
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True)

    async def send_image(self, bot, chat_id: int, image: Image) -> None:
        image_url = ContentExtractor.extract_url(image.url)

        if not Utils.is_valid_url(image_url):
            logger.error(
                f"Not sending image due to invalid image URL {image_url=}")
            return

        caption = self.get_header() if image.is_heading else None
        await bot.send_photo(
            chat_id=chat_id,
            photo=image_url,
            caption=caption,
            parse_mode=ParseMode.HTML)

    async def send_video(self, bot, chat_id: int, video: Video) -> None:
        video_url = ContentExtractor.extract_url(video.mp4)

        if not Utils.is_valid_url(video_url):
            logger.error(
                f"Not sending video due to invalid video URL {video_url=}")
            return

        thumbnail_url = ContentExtractor.extract_url(video.poster)
        caption = self.get_header() if video.is_heading else None
        await bot.send_video(
            chat_id=chat_id,
            video=video_url,
            thumbnail=thumbnail_url,
            caption=caption,
            supports_streaming=True,
            parse_mode=ParseMode.HTML)

    async def send_youtube_video(self, bot, chat_id: int, youtube: Youtube) -> None:
        text: str = ""
        if youtube.is_heading:
            text = self.get_header() + "\n\n"
        text += f"<a href='{youtube.get_url()}'>{youtube.get_url()}</a>"

        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False)

    async def send(self, bot, chat_id: int) -> None:
        for content in self.content:
            if isinstance(content, TextBlock):
                await self.send_message(bot, chat_id, content)
            elif isinstance(content, Image):
                await self.send_image(bot, chat_id, content)
            elif isinstance(content, Video):
                await self.send_video(bot, chat_id, content)
            elif isinstance(content, Youtube):
                await self.send_youtube_video(bot, chat_id, content)


class CounterStrikeUpdateMessage(TelegramMessage):

    def __init__(self, post: Post) -> None:
        post.url = Utils.get_redirected_url(post.url)

        parser = Steam2TelegramHTML(post.contents)
        parser.add_parser(parser=SteamListParser, priority=1)
        parser.add_parser(parser=SteamUpdateHeadingParser, priority=2)

        msg = f"<b>{post.title}</b>\n"
        msg += f"({post.date_as_datetime})\n"
        msg += "\n"
        msg += parser.parse()
        msg += f"(Author: {post.author})"
        msg += "\n\n"
        msg += f"Source: <a href='{post.url}'>Link</a>"

        super().__init__(msg)

    async def send(self, bot, chat_id: int) -> None:
        for msg in self.messages:
            await bot.send_message(
                chat_id=chat_id,
                text=msg,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True)


class CounterStrikeExternalMessage(TelegramMessage):

    def __init__(self, post: Post) -> None:
        post.url = Utils.get_redirected_url(post.url)
        self.post = post

        soup = BeautifulSoup(post.contents, "html.parser")

        for img in soup.find_all("img"):
            img.decompose()

        for br in soup.find_all("br"):
            br.decompose()

        read_more_all = soup.find_all("a")

        read_more = []
        for a in read_more_all:
            if "read more" in a.text.lower():
                read_more.append(a)
            if "read the rest of the story" in a.text.lower():
                read_more.append(a)

        if len(read_more) > 0:
            for a in read_more:
                a.extract()

        content = str(soup)
        content = content.replace("<p>", "").replace("</p>", "")
        content = content.replace("<br/>", "")
        content = content.lstrip().rstrip()

        msg = "🔗 <b>External News</b>\n\n"
        msg += f"<b>{post.title}</b>\n"
        msg += f"({post.date_as_datetime})\n"
        msg += "\n"
        msg += content
        msg += "\n\n"

        if len(read_more) > 0:
            post.url = read_more[0].get("href")

        msg += f"Source: <a href='{post.url}'>Link</a>"

        super().__init__(msg)

    async def send(self, bot, chat_id: int) -> None:
        for msg in self.messages:
            await bot.send_message(
                chat_id=chat_id,
                text=msg,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True)


class TelegramMessageFactory:

    @staticmethod
    def create(post: Post) -> TelegramMessage:
        if post.is_news():
            return CounterStrikeNewsMessage(post)
        if post.is_update():
            return CounterStrikeUpdateMessage(post)
        if post.is_external():
            return CounterStrikeExternalMessage(post)
        raise ValueError(f"Unknown post type {post.title=} {post.url=}")
