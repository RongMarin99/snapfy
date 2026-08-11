"""
Snapfy Rotating Proxy Pool

Loads proxies.txt (one user:pass@host:port credential per entry, tolerant of
stray quotes/commas from copy-pasted JSON-ish exports) and hands out a
different proxy on each call so repeated calls to a rate-limited API look
like they're coming from many different IPs instead of one.
"""

import re
import threading
from app.utils.resources import resource_path
from app.core.logger import logger

PROXY_RE = re.compile(r'([A-Za-z0-9._-]+:[A-Za-z0-9._-]+@\d{1,3}(?:\.\d{1,3}){3}:\d+)')


class ProxyPool:
    def __init__(self, file_path: str = None):
        self._lock = threading.Lock()
        self._idx = 0
        self._proxies: list[str] = []
        self.load(file_path)

    def load(self, file_path: str = None):
        path = file_path or resource_path("proxies.txt")
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self._proxies = PROXY_RE.findall(content)
        except Exception as e:
            logger.warning(f"ProxyPool: could not load {path}: {e}")
            self._proxies = []

        if self._proxies:
            logger.info(f"ProxyPool: loaded {len(self._proxies)} proxies")

    def is_available(self) -> bool:
        return bool(self._proxies)

    def get(self) -> str:
        """Round-robin the next proxy as an http:// URL, or None if the pool is empty."""
        if not self._proxies:
            return None
        with self._lock:
            proxy = self._proxies[self._idx % len(self._proxies)]
            self._idx += 1
        return f"http://{proxy}"


proxy_pool = ProxyPool()
