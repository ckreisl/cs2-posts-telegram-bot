from __future__ import annotations

import pytest

from cs2posts.post import FeedType
from cs2posts.post import Post


@pytest.fixture
def post_fixture():
    return Post(gid="1",
                title="Test",
                url="http://test.com",
                is_external_url=True,
                author="Test author",
                contents="Test body",
                date=1234567890,
                feedlabel="Test label",
                feedname="Test feed",
                feed_type=0,
                appid=730,
                tags=["patchnotes"])


@pytest.fixture
def post_fixture2():
    return Post(gid="2",
                title="Test2",
                url="http://test2.com",
                is_external_url=True,
                author="Test author2",
                contents="Test body2",
                date=1234567891,
                feedlabel="Test label",
                feedname="Test feed",
                feed_type=1,
                appid=730)


def test_feed_type():
    assert FeedType(12) == FeedType.NOT_DEFINED
    assert FeedType(-1) == FeedType.NOT_DEFINED
    assert FeedType(0) == FeedType.EXTERN
    assert FeedType(1) == FeedType.INTERN


def test_post_is_update(post_fixture):
    assert post_fixture.is_update()


def test_post_is_news(post_fixture2):
    assert post_fixture2.is_news()


def test_get_feed_type(post_fixture, post_fixture2):
    assert post_fixture.get_feed_type() == FeedType.EXTERN
    assert post_fixture2.get_feed_type() == FeedType.INTERN


def test_post_to_dict(post_fixture):
    expected = {
        "gid": post_fixture.gid,
        "title": post_fixture.title,
        "url": post_fixture.url,
        "is_external_url": post_fixture.is_external_url,
        "author": post_fixture.author,
        "contents": post_fixture.contents,
        "date": post_fixture.date,
        "feedlabel": post_fixture.feedlabel,
        "feedname": post_fixture.feedname,
        "feed_type": post_fixture.feed_type,
        "appid": post_fixture.appid,
        "tags": post_fixture.tags
    }
    assert post_fixture.to_dict() == expected


def test_post_get_item(post_fixture):
    assert post_fixture["gid"] == post_fixture.gid
    assert post_fixture["title"] == post_fixture.title
    assert post_fixture["url"] == post_fixture.url
    assert post_fixture["is_external_url"] == post_fixture.is_external_url
    assert post_fixture["author"] == post_fixture.author
    assert post_fixture["contents"] == post_fixture.contents
    assert post_fixture["date"] == post_fixture.date
    assert post_fixture["feedlabel"] == post_fixture.feedlabel
    assert post_fixture["feedname"] == post_fixture.feedname
    assert post_fixture["feed_type"] == post_fixture.feed_type
    assert post_fixture["appid"] == post_fixture.appid
    assert post_fixture["tags"] == post_fixture.tags


def test_post_equals(post_fixture):
    assert post_fixture == post_fixture
    assert post_fixture != {}


def test_post_not_equals(post_fixture, post_fixture2):
    assert post_fixture != post_fixture2


def test_post_is_newer_than(post_fixture, post_fixture2):
    assert not post_fixture.is_newer_than(None)
    assert not post_fixture.is_newer_than(post_fixture2)
    post_fixture2.date = 123456789
    assert post_fixture.is_newer_than(post_fixture2)


def test_post_is_older_eq_than(post_fixture, post_fixture2):
    assert not post_fixture.is_older_eq_than(None)
    assert post_fixture.is_older_eq_than(post_fixture2)
