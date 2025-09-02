import base64
import time
from typing import Dict, Tuple

import requests

DEFAULT_TIMEOUT = (3, 3)
_TTL = 600  # 10 minutes
_MAX_ENTRIES = 256
_cache: Dict[str, Tuple[float, str]] = {}


def fetch_data_uri(url: str) -> str:
    """Fetch an image and return it as a data URI.

    Uses a tiny in-memory cache with TTL to avoid refetching frequently.
    Returns an empty string on failure.
    """

    if not url:
        return ""
    now = time.time()
    cached = _cache.get(url)
    if cached and cached[0] > now:
        return cached[1]

    for attempt in range(2):
        try:
            resp = requests.get(url, timeout=DEFAULT_TIMEOUT)
        except requests.RequestException:
            return ""
        if resp.status_code >= 500 and attempt == 0:
            continue
        if resp.status_code != 200:
            return ""
        data = resp.content
        ctype = resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
        if not ctype.startswith("image/"):
            ctype = "image/jpeg"
        data_uri = f"data:{ctype};base64,{base64.b64encode(data).decode()}"
        _cache[url] = (now + _TTL, data_uri)
        if len(_cache) > _MAX_ENTRIES:
            # Evict the oldest item
            oldest = min(_cache.items(), key=lambda kv: kv[1][0])[0]
            _cache.pop(oldest, None)
        return data_uri
    return ""
