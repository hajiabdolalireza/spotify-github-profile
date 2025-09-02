import os
import sys
import time

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.recently_played import app, parse_limit
from util import spotify


class FakeDoc:
    def __init__(self, data, uid):
        self._data = data
        self.id = uid
        self.exists = data is not None

    def to_dict(self):
        return self._data


class FakeDB:
    def __init__(self, docs):
        self.docs = docs

    def collection(self, name):
        assert name == "users"
        return self

    def document(self, uid):
        db = self

        class Ref:
            def get(self):
                data = db.docs.get(uid)
                return FakeDoc(data, uid)

            def set(self, info, merge=True):
                db.docs.setdefault(uid, {}).update(info)

        return Ref()

    def stream(self):
        for uid, data in self.docs.items():
            yield FakeDoc(data, uid)


@pytest.fixture
def client():
    app.config.update({"TESTING": True})
    return app.test_client()


def test_parse_limit_clamp():
    assert parse_limit(None) == 5
    assert parse_limit("0") == 1
    assert parse_limit("11") == 10
    assert parse_limit("3") == 3


def test_alias_redirects(client):
    r = client.get("/api/recently_played")
    assert r.status_code == 301
    assert r.headers["Location"].endswith("/api/recently-played")
    r = client.get("/api/recentlyplayed")
    assert r.status_code == 301
    assert r.headers["Location"].endswith("/api/recently-played")


def test_empty_list_returns_message(client, monkeypatch):
    db = FakeDB({"u1": {"access_token": "t", "refresh_token": "r", "token_expired_timestamp": int(time.time()) + 60}})
    monkeypatch.setattr("api.recently_played.get_firestore_db", lambda: db)
    monkeypatch.setattr("util.spotify.get_recently_play", lambda token, limit=10: {"items": []})
    resp = client.get("/api/recently-played?uid=u1")
    assert resp.status_code == 200
    assert b"No recent tracks" in resp.data


def test_error_rate_limit_returns_svg(client, monkeypatch):
    db = FakeDB({"u1": {"access_token": "t", "refresh_token": "r", "token_expired_timestamp": int(time.time()) + 60}})
    monkeypatch.setattr("api.recently_played.get_firestore_db", lambda: db)
    monkeypatch.setattr(
        "util.spotify.get_recently_play",
        lambda *a, **k: (_ for _ in ()).throw(spotify.RateLimitError("x")),
    )
    resp = client.get("/api/recently-played?uid=u1")
    assert resp.status_code == 200
    assert b"rate limit" in resp.data.lower()


def test_success_path(client, monkeypatch):
    items = [
        {
            "track": {
                "name": f"S{i}",
                "artists": [{"name": f"A{i}"}],
                "album": {"images": [{"url": f"https://img/{i}"}]},
            }
        }
        for i in range(5)
    ]
    db = FakeDB(
        {
            "u1": {
                "access_token": "t",
                "refresh_token": "r",
                "token_expired_timestamp": int(time.time()) + 60,
            }
        }
    )
    monkeypatch.setattr("api.recently_played.get_firestore_db", lambda: db)
    monkeypatch.setattr("util.spotify.get_recently_play", lambda token, limit=10: {"items": items})
    resp = client.get("/api/recently-played?uid=u1&limit=5")
    text = resp.data.decode()
    assert text.count("<image") == 5
    assert text.count("</text>") - 1 == 5  # minus header line
    assert resp.headers["Cache-Control"].startswith("public")


def test_token_refresh_flow(client, monkeypatch):
    items = {
        "items": [
            {
                "track": {
                    "name": "S",
                    "artists": [{"name": "A"}],
                    "album": {"images": [{"url": "https://img/1"}]},
                }
            }
        ]
    }
    db = FakeDB(
        {
            "u1": {
                "access_token": "old",
                "refresh_token": "r",
                "token_expired_timestamp": int(time.time()) + 60,
            }
        }
    )
    monkeypatch.setattr("api.recently_played.get_firestore_db", lambda: db)

    calls = {"refresh": 0, "play": 0}

    def fake_get(token, limit=10):
        calls["play"] += 1
        if calls["play"] == 1:
            raise spotify.InvalidTokenError("bad")
        return items

    def fake_refresh(refresh):
        calls["refresh"] += 1
        return {"access_token": "new", "expires_in": 3600}

    monkeypatch.setattr("util.spotify.get_recently_play", fake_get)
    monkeypatch.setattr("util.spotify.refresh_token", fake_refresh)

    resp = client.get("/api/recently-played?uid=u1")
    assert resp.status_code == 200
    assert calls["play"] == 2
    assert calls["refresh"] == 1
    assert db.docs["u1"]["access_token"] == "new"


def test_snapshot_svg(client, monkeypatch):
    items = [
        {
            "track": {
                "name": "T1",
                "artists": [{"name": "A1"}],
                "album": {"images": [{"url": "https://img/1"}]},
            }
        },
        {
            "track": {
                "name": "T2",
                "artists": [{"name": "A2"}],
                "album": {"images": [{"url": "https://img/2"}]},
            }
        },
    ]
    db = FakeDB(
        {
            "u1": {
                "access_token": "t",
                "refresh_token": "r",
                "token_expired_timestamp": int(time.time()) + 60,
            }
        }
    )
    monkeypatch.setattr("api.recently_played.get_firestore_db", lambda: db)
    monkeypatch.setattr("util.spotify.get_recently_play", lambda *a, **k: {"items": items})
    resp = client.get("/api/recently-played?uid=u1&limit=2")
    with open("tests/golden_recently_played.svg", "r", encoding="utf-8") as f:
        expected = f.read().strip()
    assert resp.data.decode().strip() == expected


def test_etag_support(client, monkeypatch):
    items = {
        "items": [
            {
                "track": {
                    "name": "S",
                    "artists": [{"name": "A"}],
                    "album": {"images": [{"url": "https://img/1"}]},
                }
            }
        ]
    }
    db = FakeDB({"u1": {"access_token": "t", "refresh_token": "r", "token_expired_timestamp": int(time.time()) + 60}})
    monkeypatch.setattr("api.recently_played.get_firestore_db", lambda: db)
    monkeypatch.setattr("util.spotify.get_recently_play", lambda *a, **k: items)
    first = client.get("/api/recently-played?uid=u1")
    etag = first.headers["ETag"]
    second = client.get("/api/recently-played?uid=u1", headers={"If-None-Match": etag})
    assert first.status_code == 200
    assert second.status_code == 304
    assert second.data == b""

