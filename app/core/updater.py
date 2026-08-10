"""
Snapfy GitHub Release Update Checker
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import httpx

from app.core.version import APP_VERSION, GITHUB_REPO
from app.core.settings import settings_manager
from app.core.logger import logger

RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


@dataclass
class UpdateInfo:
    current_version: str
    latest_version: str
    release_notes: str
    release_url: str
    download_url: str
    is_installer: bool  # True if download_url points at a real Setup.exe asset (silent-installable)


def _parse_version(v: str) -> tuple:
    """Parses '1.3.32' or 'v1.3.32' into (1, 3, 32) for comparison."""
    cleaned = v.strip().lstrip("vV")
    parts = re.findall(r'\d+', cleaned)
    return tuple(int(p) for p in parts) if parts else (0,)


def is_newer(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


def check_for_update() -> Optional[UpdateInfo]:
    """
    Queries the GitHub Releases API for the latest release.
    Returns UpdateInfo if a newer version is available, else None.
    Raises on network/API failure so callers can distinguish "no update" from "check failed".
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Snapfy-Updater",
    }

    with httpx.Client(timeout=10.0, verify=settings_manager.get("ssl_verify", True)) as client:
        resp = client.get(RELEASES_API_URL, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    latest_version = str(data.get("tag_name", "")).strip()
    if not latest_version:
        raise ValueError("GitHub release response missing tag_name.")

    if not is_newer(latest_version, APP_VERSION):
        logger.info(f"Snapfy is up to date (current={APP_VERSION}, latest={latest_version}).")
        return None

    download_url = data.get("html_url", "")
    is_installer = False
    for asset in data.get("assets", []):
        name = asset.get("name", "")
        if name.lower().endswith(".exe"):
            download_url = asset.get("browser_download_url", download_url)
            is_installer = True
            break

    logger.info(f"Update available: {APP_VERSION} -> {latest_version}")
    return UpdateInfo(
        current_version=APP_VERSION,
        latest_version=latest_version,
        release_notes=str(data.get("body", "")).strip(),
        release_url=data.get("html_url", ""),
        download_url=download_url,
        is_installer=is_installer,
    )


def download_installer(
    url: str,
    dest_path: Path,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> None:
    """Streams the installer .exe to dest_path. Raises on failure."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    verify = settings_manager.get("ssl_verify", True)

    with httpx.Client(timeout=30.0, follow_redirects=True, verify=verify) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(dest_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total:
                        progress_callback(downloaded / total * 100.0)

    logger.info(f"Installer downloaded to {dest_path}")
