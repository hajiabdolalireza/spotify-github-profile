# api/recently_played.py
import os, json, base64, time, requests
from flask import Flask, request, Response
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
app.url_map.strict_slashes = False  

def _init_firestore():
    b64 = os.environ.get("FIREBASE")
    cred = json.loads(base64.b64decode(b64))
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(cred))
    return firestore.client()

def _get_tokens(db, uid):
    doc = db.collection("users").document(uid).get()
    if not doc.exists:
        raise RuntimeError("Firestore document not found")
    return doc.to_dict()

def _refresh_access_token(refresh_token):
    r = requests.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        auth=(os.environ["SPOTIFY_CLIENT_ID"], os.environ["SPOTIFY_SECRET_ID"]),
        timeout=10,
    )
    r.raise_for_status()
    return r.json()

def _ensure_access_token(db, uid, info):
    now = int(time.time())
    if info.get("token_expired_timestamp", 0) <= now:
        new_info = _refresh_access_token(info["refresh_token"])
        info.update({
            "access_token": new_info["access_token"],
            "token_expired_timestamp": now + int(new_info.get("expires_in", 3600)) - 30
        })
        db.collection("users").document(uid).set(info, merge=True)
    return info["access_token"]

def _escape(s): return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def _render_svg(items, title="Recently played"):
    width, line_h, pad = 700, 22, 16
    lines = [f'<text x="0" y="{pad}" font-size="18" font-weight="bold">{_escape(title)}</text>']
    y = pad + 26
    for i, it in enumerate(items[:10], 1):
        track = (it or {}).get("track", {})
        name = track.get("name","")
        artists = ", ".join(a.get("name","") for a in track.get("artists",[]))
        lines.append(f'<text x="0" y="{y}" font-size="14">{i}. {_escape(name)} — {_escape(artists)}</text>')
        y += line_h
    height = max(y + pad, 80)
    body = "\n".join(lines) if items else '<text x="0" y="30" font-size="14">No recent tracks</text>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
<style>text {{ font-family: -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,sans-serif; fill: #e6edf3; }}
svg {{ background: #0d1117; }}</style>
        <g transform="translate(16,8)">{body}</g></svg>'''


@app.route("/api/recently_played", methods=["GET"])
@app.route("/api/recently_played/", methods=["GET"])
@app.route("/api/recently-played", methods=["GET"])
@app.route("/api/recently-played/", methods=["GET"])
@app.route("/api/recently-played.svg", methods=["GET"])
def recently_played_svg():
    uid = request.args.get("uid")
    limit = int(request.args.get("count", 10))
    if not uid:
        return Response("uid is required", status=400)
    db = _init_firestore()
    info = _get_tokens(db, uid)
    token = _ensure_access_token(db, uid, info)
    r = requests.get(
        "https://api.spotify.com/v1/me/player/recently-played",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": limit},
        timeout=10,
    )
    r.raise_for_status()
    svg = _render_svg(r.json().get("items", []))
    return Response(svg, mimetype="image/svg+xml")

@app.route("/api/recently_played/ping", methods=["GET"])
def ping():
    return Response("ok", mimetype="text/plain")
