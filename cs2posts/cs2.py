from __future__ import annotations

import logging
from typing import Any

from cs2posts.post import FeedType
from cs2posts.post import Post


logger = logging.getLogger(__name__)


class CounterStrike2Posts:

    INITIAL_EPOCH_TIME_CS2 = 1679503828

    def __init__(self, posts: dict[str, Any]) -> None:

        self.__posts = []

        if posts is None or posts == {}:
            return

        if 'appnews' not in posts:
            return

        posts = posts['appnews']

        if 'newsitems' not in posts:
            return

        posts = posts['newsitems']

        for post in posts:
            feed_type = FeedType(post['feed_type'])
            if feed_type not in [FeedType.INTERN, FeedType.EXTERN]:
                logger.info(
                    f"Ignoring feed: {post['gid']}"
                    f" with headline: {post['title']}"
                    f" and url: {post['url']}"
                    f" {feed_type=}")
                continue

            self.__posts.append(Post(**post))

        self.__posts.sort(key=lambda x: x.date, reverse=True)

    @classmethod
    def create(cls, posts: dict[str, Any]) -> CounterStrike2Posts:
        return cls(posts)

    @property
    def posts(self) -> list[Post]:
        return self.__posts

    @property
    def news_posts(self) -> list[Post]:
        return list(filter(lambda x: (x.date >= self.INITIAL_EPOCH_TIME_CS2) and x.is_news(),
                           self.__posts))

    @property
    def update_posts(self) -> list[Post]:
        return list(filter(lambda x: (x.date >= self.INITIAL_EPOCH_TIME_CS2) and x.is_update(),
                           self.__posts))

    @property
    def external_posts(self) -> list[Post]:
        return list(filter(lambda x: (x.date >= self.INITIAL_EPOCH_TIME_CS2) and x.is_external(),
                           self.__posts))

    @property
    def posts_json(self) -> list[dict]:
        return list(map(lambda x: x.to_dict(), self.__posts))

    @property
    def latest(self) -> Post | None:
        return self.__posts[0] if self.__posts else None

    @property
    def latest_news_post(self) -> Post | None:
        return self.news_posts[0] if self.news_posts else None

    @property
    def latest_update_post(self) -> Post | None:
        return self.update_posts[0] if self.update_posts else None

    @property
    def latest_external_post(self) -> Post | None:
        return self.external_posts[0] if self.external_posts else None

    @property
    def oldest(self) -> Post | None:
        return self.__posts[-1] if self.__posts else None

    @property
    def oldest_news_post(self) -> Post | None:
        return self.news_posts[-1] if self.news_posts else None

    @property
    def oldest_update_post(self) -> Post | None:
        return self.update_posts[-1] if self.update_posts else None

    @property
    def oldest_external_post(self) -> Post | None:
        return self.external_posts[-1] if self.external_posts else None

    def is_latest_post_news(self) -> bool:
        if self.latest is None:
            return False
        return self.latest.is_news()

    def is_latest_post_update(self) -> bool:
        if self.latest is None:
            return False
        return self.latest.is_update()

    def is_latest_post_external(self) -> bool:
        if self.latest is None:
            return False
        return self.latest.is_external()

    def is_empty(self) -> bool:
        return len(self.__posts) == 0

    def __len__(self) -> int:
        return len(self.__posts)
