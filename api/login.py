from flask import Flask, Response, jsonify, render_template, redirect

from util import spotify
from util.logging_utils import setup_logging

app = Flask(__name__)
setup_logging(app)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):

    login_url = f"https://accounts.spotify.com/authorize?client_id={spotify.SPOTIFY_CLIENT_ID}&response_type=code&scope=user-read-currently-playing,user-read-recently-played&redirect_uri={spotify.REDIRECT_URI}"

    return redirect(login_url)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
