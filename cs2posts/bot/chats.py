from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Chat:
    chat_id: int
    chat_id_admin: int = 0
    strikes: int = 0
    is_running: bool = False
    is_banned: bool = False
    is_removed_while_banned: bool = False
    is_news_interested: bool = True
    is_update_interested: bool = True
    is_external_news_interested: bool = True
    last_activity: datetime = datetime(1970, 1, 1)

    @classmethod
    def from_json(cls, data: dict[str, str]) -> Chat:
        last_activity = datetime.fromisoformat(data.pop('last_activity'))
        return cls(**data, last_activity=last_activity)
