import time
import os

from flask import Flask, jsonify

from util.logging_utils import setup_logging


app = Flask(__name__)
setup_logging(app)


@app.route("/api/ping", methods=["GET"])
def ping():
    return jsonify(
        {
            "ok": True,
            "time": int(time.time()),
            "version": os.getenv("VERSION", "dev"),
        }
    )


