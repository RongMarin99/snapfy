"""
Snapfy Rotating Proxy Pool

Proxies come from two sources, merged together:
  1. The bundled proxies.txt (optional seed file, kept for backwards compat)
  2. The user-entered "custom_proxies" text saved in Settings

Accepts a mix of formats, one entry per line (also tolerates comma/semicolon
separated entries, and stray quotes from copy-pasted JSON-ish exports):
  - user:pass@host:port
  - host:port:user:pass
  - host:port@user:pass
  - host:port                (no auth)
  - scheme://<any of the above>

Hands out a different proxy on each call so repeated calls to a
rate-limited API look like they're coming from many different IPs
instead of one. Proxies that fail (auth rejected, connect error, blocked)
are put on a cooldown and skipped by get() until it expires.
"""

import re
import time
import threading
from app.utils.resources import resource_path
from app.core.logger import logger

DEAD_COOLDOWN_SECONDS = 300.0
SCHEME_RE = re.compile(r'^[A-Za-z][A-Za-z0-9+.\-]*://(.*)$')
TOKEN_SPLIT_RE = re.compile(r'[\s,;"\'\[\]]+')
IPV4_RE = re.compile(r'^\d{1,3}(?:\.\d{1,3}){3}$')
HOSTNAME_RE = re.compile(r'^[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?)+$')


def _mask(proxy: str) -> str:
    """user:pass@host:port -> user:***@host:port, for safe logging."""
    if "@" not in proxy:
        return proxy
    creds, hostport = proxy.split("@", 1)
    user = creds.split(":", 1)[0]
    return f"{user}:***@{hostport}"


def _is_host(s: str) -> bool:
    return bool(s) and (bool(IPV4_RE.match(s)) or bool(HOSTNAME_RE.match(s)) or s.lower() == "localhost")


def _looks_like_hostport(s: str) -> bool:
    host, sep, port = s.rpartition(":")
    return bool(sep) and _is_host(host) and port.isdigit()


def parse_proxy_token(token: str) -> str:
    """Normalizes one proxy entry, in whatever supported format, down to
    canonical 'host:port' or 'user:pass@host:port'. Returns None if the
    token isn't recognizable as a proxy."""
    token = token.strip().strip("'\",;")
    if not token:
        return None

    m = SCHEME_RE.match(token)
    if m:
        token = m.group(1)
    if not token:
        return None

    if "@" in token:
        left, right = token.split("@", 1)
        if _looks_like_hostport(right):
            creds, hostport = left, right
        elif _looks_like_hostport(left):
            creds, hostport = right, left
        else:
            return None
        if not creds or ":" not in creds:
            return None
        return f"{creds}@{hostport}"

    parts = token.split(":")
    if len(parts) == 2:
        return token if _looks_like_hostport(token) else None

    if len(parts) == 4:
        a, b, c, d = parts
        if _is_host(a) and b.isdigit():
            return f"{c}:{d}@{a}:{b}"
        if _is_host(c) and d.isdigit():
            return f"{a}:{b}@{c}:{d}"

    return None


def parse_proxy_text(content: str) -> list:
    """Extracts every recognizable proxy from free-form pasted text."""
    proxies = []
    seen = set()
    for token in TOKEN_SPLIT_RE.split(content or ""):
        proxy = parse_proxy_token(token)
        if proxy and proxy not in seen:
            seen.add(proxy)
            proxies.append(proxy)
    return proxies


class ProxyPool:
    def __init__(self):
        self._lock = threading.Lock()
        self._idx = 0
        self._proxies: list[str] = []
        self._dead_until: dict[str, float] = {}
        self.load()

    def load(self, extra_text: str = None):
        """Reloads the pool from proxies.txt plus either `extra_text` (if given)
        or the user's saved custom_proxies setting."""
        from app.core.settings import settings_manager

        parts = []
        try:
            with open(resource_path("proxies.txt"), "r", encoding="utf-8") as f:
                parts.append(f.read())
        except Exception:
            pass

        user_text = extra_text if extra_text is not None else settings_manager.get("custom_proxies", "")
        if user_text:
            parts.append(user_text)

        proxies = parse_proxy_text("\n".join(parts))

        with self._lock:
            self._proxies = proxies
            self._idx = 0
            self._dead_until = {}

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
