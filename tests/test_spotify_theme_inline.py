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


def test_spotify_theme_inlines_images(client, monkeypatch):
    items = [
        {
            "track": {
                "name": f"T{i}",
                "artists": [{"name": f"A{i}"}],
                "album": {"images": [{"url": f"https://img/{i}"}]},
            },
            "played_at": "2024-01-04T23:59:00Z",
        }
        for i in range(3)
    ]
    db = _base_db()
    monkeypatch.setattr("api.recently_played.get_firestore_db", lambda: db)
    monkeypatch.setattr(
        "util.spotify.get_recently_played", lambda token, limit=3: {"items": items}
    )
    tiny_png = (
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )
    monkeypatch.setattr("util.images.fetch_data_uri", lambda url: tiny_png)
    monkeypatch.setattr("api.recently_played.fetch_data_uri", lambda url: tiny_png)

    from datetime import datetime, timezone

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2024, 1, 5, tzinfo=timezone.utc)

    monkeypatch.setattr("api.recently_played.datetime", FixedDatetime)

    resp = client.get("/api/recently-played?uid=u1&theme=spotify&limit=3")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "image/svg+xml; charset=utf-8"
    svg = resp.data.decode()
    assert 'href="http' not in svg
    assert "data:image/" in svg
    assert "Spotify" in svg and "Recently Played" in svg
    with open("tests/golden_spotify_theme.svg", "r", encoding="utf-8") as f:
        expected = f.read().strip()
    assert svg.strip() == expected
    etag = resp.headers["ETag"]
    second = client.get(
        "/api/recently-played?uid=u1&theme=spotify&limit=3",
        headers={"If-None-Match": etag},
    )
    assert second.status_code == 304
    assert second.data == b""
