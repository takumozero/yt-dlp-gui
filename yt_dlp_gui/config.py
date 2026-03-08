from __future__ import annotations

import sys
from pathlib import Path


def get_app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def get_internal_root() -> Path:
    app_root = get_app_root()

    if getattr(sys, "frozen", False):
        internal_dir = app_root / "_internal"
        if internal_dir.exists():
            return internal_dir

    return app_root


def get_bin_dir() -> Path:
    if getattr(sys, "frozen", False):
        return get_internal_root() / "bin"
    return get_app_root() / "bin"


def get_logs_dir() -> Path:
    logs_dir = get_app_root() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_assets_dir() -> Path:
    if getattr(sys, "frozen", False):
        return get_internal_root() / "assets"
    return get_app_root() / "yt_dlp_gui" / "assets"


def get_yt_dlp_path() -> Path:
    return get_bin_dir() / "yt-dlp.exe"

def get_ffmpeg_bin_dir() -> Path:
    if getattr(sys, "frozen", False):
        return get_internal_root() / "ffmpeg" / "bin"
    return get_app_root() / "ffmpeg" / "bin"
