from __future__ import annotations

import pytest

from cs2posts.bot.chats import Chat
from cs2posts.db import ChatDatabase
from cs2posts.db import PostDatabase
from cs2posts.post import Post


@pytest.fixture
def data_latest():
    return {
        "update": {
            "gid": "5762994032385146001",
            "title": "Release Notes for 4/16/2024",
            "url": "https://steamstore-a.akamaihd.net/news/externalpost/steam_community_announcements/5762994032385146001",
            "is_external_url": True,
            "author": "Vitaliy",
            "contents": "[ MISC ]\n[list]\n[*] Fixed a bug where bomb can sometimes disappear from the radar\n[*] Allow scraping or removing stickers by selecting the sticker icons under the weapon\n[*] Allow deleting empty storage units that have an assigned label\n[*] Fixed Workshop tools from crashing when compiling maps that contain instances\n[/list]",
            "feedlabel": "Community Announcements",
            "date": 1713310428,
            "feedname": "steam_community_announcements",
            "feed_type": 1,
            "appid": 730,
            "tags": [
                "patchnotes"
            ]
        },
        "news": {
            "gid": "5756237364302520223",
            "title": "Copenhagen Major Champions",
            "url": "https://steamstore-a.akamaihd.net/news/externalpost/steam_community_announcements/5756237364302520223",
            "is_external_url": True,
            "author": "Piggles ULTRAPRO",
            "contents": "[img]https://clan.akamai.steamstatic.com/images/3381077/75c3204fcb2874385f7c3e1dafeb00003b76502e.png[/img]\nCongratulations to Natus Vincere, the first CS2 Major Champions!\n\nPlaying in front of a sold-out arena and with over 1.8 million viewers watching around the world, NAVI and FaZe met in the Grand Final of one of the most hotly-contested Counter-Strike Majors of all time. Trading map wins in Ancient and Mirage, the teams moved to Inferno for the decider. There, b1t, jL, Aleksib, iM, and w0nderful put on a dominating performance to earn the trophy and title of Major Champions.\n\nTo celebrate their achievement, the Copenhagen 2024 Major Champions Capsule is now available for purchase. The capsule features autographs for each member of the winning team in paper, glitter, holo, and gold. 50% of the proceeds go to the players and organizations.\n\nAnd with that, the Copenhagen Major has come to a close. See you next time in Shanghai!",
            "feedlabel": "Community Announcements",
            "date": 1712103491,
            "feedname": "steam_community_announcements",
            "feed_type": 1,
            "appid": 730,
            "tags": []
        },
        "external": {
            "gid": "5759616966667952408",
            "title": "Lefties unite! Counter-Strike 2 now lets you swap hands",
            "url": "https://steamstore-a.akamaihd.net/news/externalpost/GamingOnLinux/5759616966667952408",
            "is_external_url": True,
            "author": "",
            "contents": "<p><p>All you Lefties out there can finally get properly represented, in Counter-Strike 2 that is, as there's now the ability to swap your weapons into the other hand.</p><p><img src=\"https://www.gamingonlinux.com/uploads/articles/tagline_images/350555862id24405gol.jpg\" alt /></p><p>Read the full article here: https://www.gamingonlinux.com/2024/04/lefties-unite-counter-strike-2-now-lets-you-swap-hands</p></p>",
            "feedlabel": "GamingOnLinux",
            "date": 1714131032,
            "feedname": "GamingOnLinux",
            "feed_type": 0,
            "appid": 730,
            "tags": []
        }
    }


@pytest.fixture
def post_database(tmp_path, data_latest):
    filepath = tmp_path / "test_posts.db"

    db = PostDatabase(filepath)
    db.save(Post(**data_latest["update"]))
    db.save(Post(**data_latest["news"]))
    db.save(Post(**data_latest["external"]))

    yield db


@pytest.fixture
def data_chats():
    return {"chats": [Chat(1337), Chat(42)]}


@pytest.fixture
def chats_empty_database(tmp_path):
    filepath = tmp_path / "test_chats.db"
    db = ChatDatabase(filepath)
    yield db


@pytest.fixture
def chats_database(chats_empty_database, data_chats):
    for chat in data_chats["chats"]:
        chats_empty_database.save(chat)

    yield chats_empty_database


def test_post_database_save(post_database, data_latest):
    expected_temp_update_title = data_latest["news"]["title"]

    data_latest["update"]["title"] = "New Update headline"
    data_latest["news"]["title"] = "New News headline"
    data_latest["external"]["title"] = "New External headline"

    actual_post_update = Post(**data_latest["update"])
    actual_post_news = Post(**data_latest["news"])
    actual_post_external = Post(**data_latest["external"])

    post_database.save(actual_post_update)
    latest_update_post = post_database.get_latest_update_post()
    latest_news_post = post_database.get_latest_news_post()

    # News headline should not be changed
    assert latest_news_post.title == expected_temp_update_title
    assert latest_update_post.title == "New Update headline"

    post_database.save(actual_post_news)

    latest_news_post = post_database.get_latest_news_post()
    assert latest_news_post.title == "New News headline"

    post_database.save(actual_post_external)
    assert post_database.get_latest_external_post().title == "New External headline"


def test_post_database_get_latest_news_post(post_database, data_latest):
    actual_post = post_database.get_latest_news_post()
    expected_post = Post(**data_latest["news"])
    assert actual_post == expected_post


def test_post_database_get_latest_update_post(post_database, data_latest):
    actual_post = post_database.get_latest_update_post()
    expected_post = Post(**data_latest["update"])
    assert actual_post == expected_post


def test_chats_database_load(chats_database):
    chats = chats_database.load()
    assert isinstance(chats, list)
    assert len(chats) == 2
    assert Chat(1337) in chats
    assert Chat(42) in chats


def test_chats_database_save(chats_empty_database):
    expected_chats = [Chat(41), Chat(1338)]
    for chat in expected_chats:
        chats_empty_database.save(chat=chat)
    actual_chats = chats_empty_database.load()

    assert len(expected_chats) == len(actual_chats)
    assert actual_chats == expected_chats
