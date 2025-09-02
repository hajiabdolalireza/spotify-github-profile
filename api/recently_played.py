import time
import hashlib
import html
from typing import Any, Dict

from flask import Flask, Response, request, redirect, render_template

from util.firestore import get_firestore_db
from util import spotify
from util.logging_utils import setup_logging


app = Flask(__name__)
setup_logging(app)

CACHE_CONTROL = "public, max-age=60, stale-while-revalidate=30"


def parse_limit(value: Any) -> int:
    try:
        num = int(value)
    except (TypeError, ValueError):
        return 5
    return max(1, min(num, 10))


def render_svg(items) -> str:
    width, row_h, pad, img = 400, 40, 16, 32
    if items:
        height = max(2 * pad + 32 + (len(items) - 1) * row_h, 80)
    else:
        height = 80
    return render_template(
        "recently-played.svg.j2",
        items=items,
        width=width,
        height=height,
        pad=pad,
        row_h=row_h,
        img=img,
    )


def render_error(msg: str) -> str:
    esc = html.escape(msg or "")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="60">'
        "<style>text { font-family: -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,sans-serif;"
        " fill: #e6edf3; }svg { background: #0d1117; }</style>"
        f'<text x="10" y="35" font-size="14">{esc}</text></svg>'
    )


def _svg_response(svg: str) -> Response:
    etag = hashlib.md5(svg.encode("utf-8")).hexdigest()
    if request.headers.get("If-None-Match") == etag:
        resp = Response(status=304)
    else:
        resp = Response(svg, mimetype="image/svg+xml")
    resp.headers["Cache-Control"] = CACHE_CONTROL
    resp.headers["ETag"] = etag
    return resp


def _get_user_id(db) -> str:
    uid = request.args.get("uid") or request.args.get("user")
    if uid:
        # allow only alphanumeric user ids
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
                "token_expired_timestamp": now + int(refreshed.get("expires_in", 3600)) - 30,
            }
        )
        db.collection("users").document(uid).set(info, merge=True)
    return info["access_token"]


@app.route("/api/recently_played", methods=["GET"])
@app.route("/api/recentlyplayed", methods=["GET"])
def recently_played_redirect():
    return redirect("/api/recently-played", code=301)


@app.route("/api/recently-played", methods=["GET"])
def recently_played_view():
    limit = parse_limit(request.args.get("limit"))
    db = get_firestore_db()
    uid = _get_user_id(db)
    app.logger.info("recently-played uid=%s limit=%s", uid or "", limit)
    if not uid:
        svg = render_error("Please provide ?uid=<spotify id>")
        return _svg_response(svg)
    try:
        info = _get_tokens(db, uid)
        token = _ensure_access_token(db, uid, info)
        try:
            data = spotify.get_recently_play(token, limit=10)
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
            data = spotify.get_recently_play(info["access_token"], limit=10)
        items = data.get("items", [])[:limit]
        svg = render_svg(items)
        return _svg_response(svg)
    except spotify.RateLimitError:
        return _svg_response(render_error("Spotify rate limit"))
    except Exception as e:  # noqa: BLE001
        return _svg_response(render_error(str(e)))


