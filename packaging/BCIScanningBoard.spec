# PyInstaller spec for the EMOTIV Scanning Board.
#
# Build from the repository root:
#     pyinstaller packaging/BCIScanningBoard.spec --noconfirm
#
# Produces dist/EMOTIV Scanning Board/ on Windows and
# dist/EMOTIV Scanning Board.app on macOS. Both are unsigned.

import os
import sys

APP_NAME = "EMOTIV Scanning Board"
# SPECPATH is injected by PyInstaller and points at packaging/; the sources sit
# one level up. Deriving it this way keeps the build independent of the cwd.
ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))

# Built from assets/logo.png by packaging/make_icon.py, which the build
# workflow runs before PyInstaller. Neither file is checked in -- they are
# derived artwork, and a stale committed icon is worse than none -- so the
# build tolerates their absence rather than failing on a checkout where
# make_icon.py has not been run.
ICON_WIN = os.path.join(SPECPATH, "app_icon.ico")
ICON_MAC = os.path.join(SPECPATH, "app_icon.icns")

# The window icon is the one file read from disk at runtime: the exe's own icon
# covers the taskbar and Explorer, but Qt draws the title bar from
# setWindowIcon(), which reads this .ico and picks the frame it needs. Everything else is in code -- the phrase matrix falls back to
# DEFAULT_PHRASES_LIST, config.json is written into the user's data directory,
# and cortex.py connects with cert_reqs=CERT_NONE so no root CA travels with the
# app. insight_backdrop.jpg is a README image the application never loads, so it
# is deliberately not bundled.
datas = [(ICON_WIN, ".")] if os.path.exists(ICON_WIN) else []

# PyQt6 ships far more than this app touches. Dropping the heavy optional
# modules keeps the bundle small and avoids Qt WebEngine, which needs signing
# help on macOS.
excludes = [
    "PyQt6.QtWebEngineCore", "PyQt6.QtWebEngineWidgets", "PyQt6.QtWebEngineQuick",
    "PyQt6.Qt3DCore", "PyQt6.Qt3DRender", "PyQt6.QtQuick3D",
    "PyQt6.QtBluetooth", "PyQt6.QtNfc", "PyQt6.QtDesigner",
    "tkinter", "matplotlib", "numpy", "PIL", "PySide6", "PyQt5",
]

# pyttsx3 picks its speech backend by name at runtime -- driverName is a string
# it imports -- so static analysis never sees the platform driver. Without
# these the packaged app raises at the first spoken phrase, which is the whole
# point of the product.
tts_hidden = ["pyttsx3.drivers", "pyttsx3.drivers.dummy"]
if sys.platform == "darwin":
    tts_hidden += ["pyttsx3.drivers.nsss"]
else:
    # comtypes builds its SpeechLib wrapper on first use and caches it; the
    # generated package has to be reachable inside the bundle for that to work.
    tts_hidden += ["pyttsx3.drivers.sapi5", "comtypes", "comtypes.gen", "pythoncom"]

a = Analysis(
    [os.path.join(ROOT, "scanning_board_setupandconfig.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    # cortex.py is imported inside a method, and pydispatch is its dependency.
    hiddenimports=["cortex", "pydispatch", "websocket"] + tts_hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name=APP_NAME,
    icon=ICON_WIN if os.path.exists(ICON_WIN) else None,
    debug=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=APP_NAME,
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=ICON_MAC if os.path.exists(ICON_MAC) else None,
        bundle_identifier="com.emotiv.scanningboard",
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": "1.0.0",
            "LSMinimumSystemVersion": "11.0",
            # Cortex runs on localhost; recent macOS versions treat that as the
            # local network and block it silently without this key.
            "NSLocalNetworkUsageDescription":
                "Connects to the EMOTIV Cortex service running on this computer.",
        },
    )
