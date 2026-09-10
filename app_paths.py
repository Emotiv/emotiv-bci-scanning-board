"""
Where files live, both when running from source and inside a packaged build.

Two different answers are needed:

  resource_path()  read-only files shipped with the app. PyInstaller unpacks
                   those into sys._MEIPASS, and inside a macOS .app that
                   directory is not the working directory, so a relative path
                   like "./insight_backdrop.jpg" misses.

  user_data_dir()  files the app writes (config.json, phrases.json). An
                   installed build lives under Program Files or /Applications,
                   which the user cannot write to, and the bare relative paths
                   the scripts used before resolved against whatever directory
                   the app happened to be launched from -- so the caregiver's
                   phrases would vanish depending on how the app was started.

Running from a checkout keeps both next to the source, exactly as before, so
nobody's existing config.json moves out from under them.
"""

import os
import sys

APP_DIR_NAME = "EmotivScanningBoard"


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def resource_path(*parts: str) -> str:
    """Absolute path to a read-only file shipped alongside the code."""
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)


def user_data_dir() -> str:
    """Per-user directory for settings, created on first use."""
    if not is_frozen():
        # Running from a checkout: keep config next to the source, as before.
        return os.path.dirname(os.path.abspath(__file__))

    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    elif os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")

    path = os.path.join(base, APP_DIR_NAME)
    os.makedirs(path, exist_ok=True)
    return path


# Resolved once at import. The Cortex credentials and the caregiver's phrase
# list; both are written by the app, so both follow user_data_dir().
CONFIG_PATH = os.path.join(user_data_dir(), "config.json")
PHRASES_PATH = os.path.join(user_data_dir(), "phrases.json")


def window_icon_path():
    """The multi-size app icon, or None when it has not been generated.

    Qt reads every frame out of a .ico and picks the size it needs, so this one
    file serves the title bar, the alt-tab switcher and the taskbar alike.

    Built by packaging/make_icon.py, which the release build runs. A checkout
    that has never run it simply has no icon, which is not worth refusing to
    start over -- so callers must handle None.
    """
    candidates = [
        # Inside a bundle it sits at the root of the unpacked tree.
        resource_path("app_icon.ico"),
        # From a checkout it stays where make_icon.py wrote it.
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "packaging", "app_icon.ico"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None
