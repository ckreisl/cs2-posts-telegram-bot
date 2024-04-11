from __future__ import annotations

import logging
from typing import Any

from cs2posts.post import EventType
from cs2posts.post import Post


logger = logging.getLogger(__name__)


class CounterStrikeNetPosts:

    INITIAL_EPOCH_TIME_CS2 = 1679503828

    def __init__(self, posts: dict[str, Any]) -> None:

        self.__posts = []

        if posts is None or posts == {}:
            return

        if 'events' not in posts:
            return

        for event in posts['events']:

            event_type = EventType(event['event_type'])
            if event_type == EventType.NOT_DEFINED:
                logger.warning(
                    f"Unknown event type: {event['event_type']}"
                    f" for post with gid: {event['gid']}"
                    f" with headline: {event['announcement_body']['headline']}")
                continue

            self.__posts.append(
                Post(event['gid'],
                     event['announcement_body']['posterid'],
                     event['announcement_body']['headline'],
                     event['announcement_body']['posttime'],
                     event['announcement_body']['updatetime'],
                     event['announcement_body']['body'],
                     event_type.value))

    @property
    def posts(self) -> list[Post]:
        return self.__posts

    @property
    def news_posts(self) -> list[Post]:
        return list(filter(lambda x: (x.posttime >= self.INITIAL_EPOCH_TIME_CS2) and x.is_news(),
                           self.__posts))

    @property
    def update_posts(self) -> list[Post]:
        return list(filter(lambda x: (x.posttime >= self.INITIAL_EPOCH_TIME_CS2) and x.is_update(),
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
    def oldest(self) -> Post | None:
        return self.__posts[-1] if self.__posts else None

    @property
    def oldest_news_post(self) -> Post | None:
        return self.news_posts[-1] if self.news_posts else None

    @property
    def oldest_update_post(self) -> Post | None:
        return self.update_posts[-1] if self.update_posts else None

    def is_latest_post_news(self) -> bool:
        if self.latest is None:
            return False
        return self.latest.is_news()

    def is_latest_post_update(self) -> bool:
        if self.latest is None:
            return False
        return self.latest.is_update()

    def is_empty(self) -> bool:
        return len(self.__posts) == 0

    def __len__(self) -> int:
        return len(self.__posts)
