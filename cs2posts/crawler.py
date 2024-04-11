from __future__ import annotations

import json
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class CounterStrike2NetCrawler:

    def __init__(self) -> None:
        self.url = "https://store.steampowered.com/" \
            "events/ajaxgetpartnereventspageable/" \
            "?clan_accountid=0" \
            "&appid=730" \
            "&offset=0" \
            "&count=%s" \
            "&l=english" \
            "&origin=https://www.counter-strike.net"

    def _validate_args(self, **kwargs: dict[str, Any]) -> None:
        if "count" in kwargs and kwargs["count"] < 0:
            raise ValueError('Count must be greater than 0!')

    def crawl(self, *, count: int | None = None) -> dict[str, Any]:
        if count is None:
            count = 100

        self._validate_args(count=count)

        try:
            response = requests.get(self.url % count)
        except Exception as e:
            logger.error(f'Could not fetch data due to {e}')
            raise

        if not response.ok:
            raise Exception(
                f'Could not fetch data received response code={response.status_code}')

        return json.loads(response.text)
