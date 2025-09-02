import os
from datetime import datetime

from flask import Flask, jsonify

from util.logging_utils import setup_logging

app = Flask(__name__)
setup_logging(app)


@app.route("/api/ping", methods=["GET"])
def ping():
    now = datetime.utcnow().isoformat() + "Z"
    return jsonify(
        {
            "ok": True,
            "time": now,
            "version": os.getenv("VERSION", "dev"),
        }
    )
