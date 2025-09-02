import os
import sys
import time

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.recently_played import app
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


def _base_db():
    return FakeDB(
        {
            "u1": {
                "access_token": "t",
                "refresh_token": "r",
                "token_expired_timestamp": int(time.time()) + 60,
            }
        }
    )


@pytest.fixture
def client():
    app.config.update({"TESTING": True})
    return app.test_client()


def test_spotify_theme_snapshot(client, monkeypatch):
    items = [
        {
            "track": {
                "name": f"T{i}",
                "artists": [{"name": f"A{i}"}],
                "album": {"images": [{"url": f"https://img/{i}"}]},
            },
            "played_at": f"2024-01-0{i}",
        }
        for i in range(1, 4)
    ]
    db = _base_db()
    monkeypatch.setattr("api.recently_played.get_firestore_db", lambda: db)
    monkeypatch.setattr(
        "util.spotify.get_recently_played", lambda token, limit=3: {"items": items}
    )
    resp = client.get("/api/recently-played?uid=u1&theme=spotify&limit=3")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "image/svg+xml; charset=utf-8"
    text = resp.data.decode()
    assert "Spotify" in text and "Recently Played" in text
    assert 'href="https://img/1"' in text
    with open("tests/golden_spotify_theme.svg", "r", encoding="utf-8") as f:
        expected = f.read().strip()
    assert text.strip() == expected
    etag = resp.headers["ETag"]
    second = client.get(
        "/api/recently-played?uid=u1&theme=spotify&limit=3",
        headers={"If-None-Match": etag},
    )
    assert second.status_code == 304
    assert second.data == b""
