import html
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from flask import Flask, Response, redirect, render_template, request

from util.firestore import get_firestore_db
from util import spotify
from util.logging_utils import setup_logging

app = Flask(__name__)
setup_logging(app)

CACHE_CONTROL = "public, max-age=60, stale-while-revalidate=30"


def humanize_ago(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    diff = max(0, int((now - dt).total_seconds()))
    if diff < 90:
        return "1 min. ago"
    mins = diff // 60
    if mins < 60:
        return f"{mins} min. ago"
    hours = mins // 60
    if hours < 24:
        return f"{hours} hr. ago"
    days = hours // 24
    return f"{days} d. ago"


def parse_iso_z(s: str) -> datetime:
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return datetime.now(timezone.utc)


def parse_limit(value: Any) -> int:
    """Parse ?limit ensuring 1 <= limit <= 10."""
    try:
        num = int(value)
    except (TypeError, ValueError):
        return 5
    return max(1, min(num, 10))


def _svg_response(svg: str) -> Response:
    etag = f'W/"{hash(svg)}"'
    headers = {
        "Content-Type": "image/svg+xml; charset=utf-8",
        "ETag": etag,
        "Cache-Control": CACHE_CONTROL,
    }
    if request.headers.get("If-None-Match") == etag:
        return Response(status=304, headers=headers)
    return Response(svg, headers=headers)


def _get_user_id(db) -> str:
    uid = request.args.get("uid") or request.args.get("user")
    if uid:
        return "".join(ch for ch in uid if ch.isalnum())
    users = list(db.collection("users").stream())
    if len(users) == 1:
        return users[0].id
    return ""


def _get_tokens(db, uid: str) -> Dict[str, Any]:
    doc = db.collection("users").document(uid).get()
    if not doc.exists:
        raise RuntimeError("user not found")
    return doc.to_dict()


def _ensure_access_token(db, uid: str, info: Dict[str, Any]) -> str:
    now = int(time.time())
    if info.get("token_expired_timestamp", 0) <= now:
        refreshed = spotify.refresh_token(info["refresh_token"])
        info.update(
            {
                "access_token": refreshed["access_token"],
                "token_expired_timestamp": now
                + int(refreshed.get("expires_in", 3600))
                - 30,
            }
        )
        db.collection("users").document(uid).set(info, merge=True)
    return info["access_token"]


def _render_recent(items: List[Dict[str, Any]]) -> str:
    width, row_h, pad, img = 400, 40, 16, 32
    height = max(80, pad * 2 + (len(items) or 1) * row_h)
    return render_template(
        "recently_played.svg.j2",
        items=items,
        width=width,
        height=height,
        pad=pad,
        row_h=row_h,
        img=img,
    )


def _render_error(msg: str) -> str:
    return render_template("error.svg.j2", message=html.escape(msg or ""))


@app.route("/api/recently_played", methods=["GET"])
@app.route("/api/recentlyplayed", methods=["GET"])
def recently_played_redirect():
    return redirect("/api/recently-played", code=301)


@app.route("/api/recently-played", methods=["GET"])
def recently_played_view():
    theme = (request.args.get("theme") or "default").lower()

    def clamp(v, lo, hi):
        return max(lo, min(hi, v))

    try:
        limit = clamp(int(request.args.get("limit", 5)), 1, 10)
    except Exception:
        limit = 5

    try:
        width = int(request.args.get("width")) if request.args.get("width") else None
    except Exception:
        width = None
    db = get_firestore_db()
    uid = _get_user_id(db)
    if not uid:
        return _svg_response(_render_error("Please provide ?uid=<spotify id>"))
    try:
        info = _get_tokens(db, uid)
        token = _ensure_access_token(db, uid, info)
        try:
            data = spotify.get_recently_played(token, limit=limit)
        except spotify.InvalidTokenError:
            refreshed = spotify.refresh_token(info["refresh_token"])
            info.update(
                {
                    "access_token": refreshed["access_token"],
                    "token_expired_timestamp": int(time.time())
                    + int(refreshed.get("expires_in", 3600))
                    - 30,
                }
            )
            db.collection("users").document(uid).set(info, merge=True)
            data = spotify.get_recently_played(info["access_token"], limit=limit)

        raw_items = data.get("items", []) if data else []

        tracks: List[Dict[str, Any]] = []
        for item in raw_items:
            track = item.get("track", {})
            artists = [a.get("name", "") for a in track.get("artists", []) or []]
            images = track.get("album", {}).get("images", []) or []
            cover = images[0].get("url", "") if images else ""
            tracks.append(
                {
                    "name": track.get("name", ""),
                    "artists": artists,
                    "cover": cover,
                    "played_at": item.get("played_at", ""),
                }
            )

        items: List[Dict[str, Any]] = []
        for t in tracks[:limit]:
            played_at = t.get("played_at")
            when = humanize_ago(parse_iso_z(played_at)) if played_at else ""
            items.append(
                {
                    "title": t.get("name", ""),
                    "artist": ", ".join(t.get("artists", [])),
                    "cover": t.get("cover"),
                    "when": when,
                }
            )

        if theme in ("spotify", "sp"):
            template = "recently_played_spotify.svg.j2"
            svg = render_template(template, items=items, W=(width or 920))
        else:
            svg = _render_recent(raw_items)
        return _svg_response(svg)
    except spotify.RateLimitError:
        return _svg_response(_render_error("Spotify rate limit"))
    except spotify.SpotifyTimeoutError:
        return _svg_response(_render_error("Spotify timeout"))
    except Exception as exc:  # noqa: BLE001
        return _svg_response(_render_error(str(exc)))
