"""
Snapfy Rotating Proxy Pool

Loads proxies.txt (one user:pass@host:port credential per entry, tolerant of
stray quotes/commas from copy-pasted JSON-ish exports) and hands out a
different proxy on each call so repeated calls to a rate-limited API look
like they're coming from many different IPs instead of one.

Proxies that fail (auth rejected, connect error, blocked) are put on a
cooldown and skipped by get() until it expires, so a handful of dead
entries in proxies.txt don't keep burning retry attempts.
"""

import re
import time
import threading
from app.utils.resources import resource_path
from app.core.logger import logger

PROXY_RE = re.compile(r'([A-Za-z0-9._-]+:[A-Za-z0-9._-]+@\d{1,3}(?:\.\d{1,3}){3}:\d+)')
DEAD_COOLDOWN_SECONDS = 300.0


def _mask(proxy: str) -> str:
    """user:pass@host:port -> user:***@host:port, for safe logging."""
    if "@" not in proxy:
        return proxy
    creds, hostport = proxy.split("@", 1)
    user = creds.split(":", 1)[0]
    return f"{user}:***@{hostport}"


class ProxyPool:
    def __init__(self, file_path: str = None):
        self._lock = threading.Lock()
        self._idx = 0
        self._proxies: list[str] = []
        self._dead_until: dict[str, float] = {}
        self.load(file_path)

    def load(self, file_path: str = None):
        path = file_path or resource_path("proxies.txt")
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            with self._lock:
                self._proxies = PROXY_RE.findall(content)
                self._idx = 0
                self._dead_until = {}
        except Exception as e:
            logger.warning(f"ProxyPool: could not load {path}: {e}")
            with self._lock:
                self._proxies = []

        if self._proxies:
            logger.info(f"ProxyPool: loaded {len(self._proxies)} proxies")

    def is_available(self) -> bool:
        return bool(self._proxies)

    def report_failure(self, proxy_url: str, cooldown: float = DEAD_COOLDOWN_SECONDS):
        """Marks a proxy (as returned by get(), e.g. 'http://user:pass@host:port')
        as dead for `cooldown` seconds so get() stops handing it out."""
        if not proxy_url:
            return
        raw = proxy_url.split("://", 1)[-1]
        with self._lock:
            if raw not in self._proxies:
                return
            self._dead_until[raw] = time.monotonic() + cooldown
        logger.warning(f"ProxyPool: proxy failed, cooling down {cooldown:.0f}s -> {_mask(raw)}")

    def get(self) -> str:
        """Round-robin the next live proxy as an http:// URL. Skips proxies
        currently on cooldown. Returns None if the pool is empty or every
        proxy is currently on cooldown (caller should fall back to a direct
        connection in that case)."""
        with self._lock:
            n = len(self._proxies)
            if n == 0:
                return None
            now = time.monotonic()
            for _ in range(n):
                proxy = self._proxies[self._idx % n]
                self._idx += 1
                if self._dead_until.get(proxy, 0.0) <= now:
                    return f"http://{proxy}"

        logger.warning("ProxyPool: all proxies are on cooldown, falling back to direct connection")
        return None


proxy_pool = ProxyPool()
