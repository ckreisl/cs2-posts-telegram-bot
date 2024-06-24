from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo


class PostType(Enum):
    NEWS = "news"
    UPDATE = "update"
    EXTERNAL = "external"

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return str(self.value)

    @classmethod
    def from_post(cls, post: Post) -> PostType:
        if post.is_news():
            return cls.NEWS
        if post.is_update():
            return cls.UPDATE
        if post.is_external():
            return cls.EXTERNAL


class FeedType(Enum):
    EXTERN = 0
    INTERN = 1
    NOT_DEFINED = -1

    @classmethod
    def _missing_(cls, value: object) -> Any:
        return cls.NOT_DEFINED


@dataclass
class Post:
    gid: str
    title: str
    url: str
    is_external_url: bool
    author: str
    contents: str
    feedlabel: str
    date: int
    feedname: str
    feed_type: int
    appid: int
    # can be empty from crawled data
    tags: list[str] = field(default_factory=list)

    @property
    def date_as_datetime(self, tz: ZoneInfo = ZoneInfo('UTC')) -> datetime:
        # Do not return a timezone-aware datetime object
        return datetime.fromtimestamp(self.date, tz=tz).replace(tzinfo=None)

    def to_dict(self) -> dict:
        return asdict(self)

    def is_update(self) -> bool:
        return "patchnotes" in self.tags or "Release Notes" in self.title

    def is_news(self) -> bool:
        return not self.is_update() and not self.is_external()

    def is_external(self) -> bool:
        return FeedType(self.feed_type) == FeedType.EXTERN

    def is_newer_than(self, other: Post) -> bool:
        if other is None:
            return False
        return self.date > other.date

    def is_older_eq_than(self, other: Post | None) -> bool:
        if other is None:
            return False
        return self.date <= other.date

    def get_feed_type(self) -> FeedType:
        return FeedType(self.feed_type)

    def get_type(self) -> PostType:
        return PostType.from_post(self)

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return self.to_dict() == other.to_dict()
        return False

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)
