from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CS2_UPDATE_CHECK_INTERVAL = int(os.getenv('CS2_UPDATE_CHECK_INTERVAL', 900))

# Database filepaths (default: sqlite.db for both)
CHAT_DB_FILEPATH = os.getenv('CHAT_DB_FILEPATH', None)
POST_DB_FILEPATH = os.getenv('POST_DB_FILEPATH', None)

CHAT_SPAM_INTERVAL_MS = int(os.getenv('CHAT_SPAM_INTERVAL_MS', 750))
CHAT_BAN_TIMEOUT_SECONDS = int(os.getenv('CHAT_BAN_TIMEOUT_SECONDS', 600))
CHAT_MAX_STRIKES = int(os.getenv('CHAT_MAX_STRIKES', 3))
