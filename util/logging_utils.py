import json
import logging
import time
import uuid

from flask import request, g


def setup_logging(app):
    """Configure basic structured logging for a Flask app."""
    logger = logging.getLogger("spotify-profile")
    if not logger.handlers:
        handler = logging.StreamHandler()
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    @app.before_request
    def _start_timer():
        g._start_time = time.time()
        g.request_id = str(uuid.uuid4())

    @app.after_request
    def _log_request(response):
        duration = int((time.time() - g.get("_start_time", time.time())) * 1000)
        payload = {
            "request_id": g.get("request_id"),
            "path": request.path,
            "query": request.query_string.decode("utf-8"),
            "user_id": request.args.get("uid") or request.args.get("user"),
            "status": response.status_code,
            "duration_ms": duration,
        }
        logger.info(json.dumps(payload))
        response.headers["X-Request-ID"] = g.get("request_id")
        return response

    @app.teardown_request
    def _log_error(exc):
        if exc is not None:
            logger.exception("request failed", exc_info=exc)

