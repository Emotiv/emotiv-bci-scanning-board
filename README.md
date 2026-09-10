# EMOTIV BCI Assistive Communication System

An interactive, dual-stream Brain-Computer Interface (BCI) communication board designed for nonverbal individuals and individuals with motor impairments. Powered by PyQt6 and the EMOTIV Cortex API, this application converts real-time EEG brain patterns (Mental Commands) and facial EMG expressions into matrix-scanning keyboard selections and text-to-speech outputs.

---

## 📥 Install and set up

Everything below is for someone installing the app, not building it. If you are
working on the code, skip to
[Running from source](#🛠-running-from-source).

### 1. What you need first

| | |
| :--- | :--- |
| **An EMOTIV headset** | Insight, EPOC, EPOC+ or EPOC X. The board reads mental commands and facial expressions, so any of them works. |
| **An EMOTIV account** | Free, at [emotiv.com](https://www.emotiv.com/). The Launcher and your API credentials both hang off it. |
| **EMOTIV Launcher** | The desktop program that talks to the headset and runs the Cortex service the app connects to. Download it from your account, install it, and **sign in**. |
| **A computer** | Windows 10/11, or a Mac with Apple Silicon. There is no phone version — the Launcher is a desktop program. |

The Launcher has to be **running and signed in** whenever you use the board. The
app connects to it over `wss://localhost:6868`; nothing about your brain data
leaves your machine.

### 2. Create your own API credentials

The board talks to Cortex as an *application*, and every person needs their own
application key. They are free and take a minute to make.

1. Sign in at [emotiv.com](https://www.emotiv.com/) and open
   **[My Account → Cortex Apps](https://www.emotiv.com/my-account/cortex-apps/)**.
2. Create a new application. Any name will do — it is only a label for your own
   key.
3. Copy the **Client ID** and the **Client Secret**.

**The secret is shown once.** Copy it somewhere safe before you close the page;
if you lose it, create a new application rather than hunting for it.

You will paste both into the app in step 4. They are stored on your own machine
only — see [Where your settings are kept](#where-your-settings-are-kept).

### 3. Install the app

Download the file for your system from the
[latest release](https://github.com/Emotiv/BCIScanningBoard/releases/latest):

| Platform | File |
| :--- | :--- |
| Windows 10/11 (x64) | `EMOTIV-Scanning-Board-windows-x64-setup.exe` |
| macOS 11+ (Apple Silicon) | `EMOTIV-Scanning-Board-macos-arm64.dmg` |

Intel Macs are not covered — the build is Apple Silicon only, and Rosetta does
not help with an arm64 binary.

These builds are **not code-signed**, so both operating systems will object the
first time. Nothing is wrong with the download; there is simply no certificate
on it yet.

**Windows.** Run the installer. It installs for your user only, so it needs no
admin rights and raises no UAC prompt. SmartScreen shows *"Windows protected
your PC"* — click **More info**, then **Run anyway**.

**macOS.** Open the `.dmg` and drag the app to **Applications**. Do not run it
from the mounted disk image: that volume is read-only and flagged, so Gatekeeper
blocks it there and the flag cannot even be cleared.

macOS marks anything downloaded from the internet with a quarantine flag, which
for an unsigned app usually surfaces as *"EMOTIV Scanning Board is damaged and
can't be opened"*. It is not damaged. Clear the flag once, in Terminal:

```bash
xattr -dr com.apple.quarantine "/Applications/EMOTIV Scanning Board.app"
```

Then open it normally. (On older macOS versions right-click → **Open** also
works; on macOS 15 and later it does not, which is why the command above is the
one to use.)

macOS will also ask for **local network** permission on first launch — allow it,
or the app cannot reach Cortex.

### 4. First run

1. Start **EMOTIV Launcher** and sign in. Connect your headset and check it is
   reporting good contact quality.
2. Open the scanning board. Because there are no saved credentials yet, it opens
   the **⚙️ API Settings** dialog straight away.
3. Paste your **Client ID** and **Client Secret**, and type the name of the
   trained **profile** you want to use.
4. Choose which inputs you want under **Include Mental Commands** and **Include
   Facial Expressions**, and which action each one triggers.
5. Press OK. The board connects and the preflight screen shows live contact and
   EEG quality.

**About the profile.** Mental commands need a profile that has been trained,
in EMOTIV's own software, on the *same headset model* you are using — a profile
trained on an EPOC X will not load on an Insight. Facial expressions need no
training, so if you have no profile yet you can start with **Include Facial
Expressions** alone and add mental commands later.

To change any of this afterwards, the **⚙️ API Settings** button is on the
preflight screen.

## Repository Scripts

This repository contains three evolutionary versions of the communication board:

| File Script | Description | Status |
| :--- | :--- | :--- |
| `scanningboard.py` | **Original Core Board:** The foundational 2-stage matrix scanner interface without the preflight diagnostic wizard or credential dialogs. | Legacy |
| `scanningboard_setupscreen.py` | **Diagnostics & Visual Update:** Introduces the preflight Contact Quality (CQ) and EEG Quality (EQ) sensor maps with EMOTIV brand styling (`#d9145a` hot-pink). | Intermediate |
| `scanningboard_setupandconfig.py` | **Production Master:** The complete, feature-rich version including in-app API credential setup, caregiver phrase management, live battery/signal diagnostics, TTS synthesis, dynamic sensitivity sliders, and clean exit thread handling. | **Recommended (Latest)** |

---

## Key Features (`scanningboard_setupandconfig.py`)

### Dual-Stream Telemetry Engine
* **Mental Commands (`com`):** Maps `Push` (Select) and `Pull` (Change Speed) intent streams directly to matrix targeting.
* **Facial EMG Expressions (`fac`):** Dual-mapped backup input processing using `Teeth Clench` (Select) and `Brow Furrow / Frown` (Speed Change).
* **Independent Stream Toggles:** Easily enable or disable mental commands or facial expressions independently via bottom checkboxes.

### Real-time Hardware Tuning Bay
* **Thought Sensitivity Slider:** Adjustable trigger activation threshold (0.05 to 0.95, default `0.35`).
* **Facial EMG Sensitivity Slider:** Adjustable trigger activation threshold (0.05 to 0.95, default `0.70`).
* **Cooldown Duration Slider:** Dynamic post-selection pause timer (0.5s to 5.0s, default `2.5s`).

### Caregiver Custom Phrase Manager
* Open the **`📝 Phrases`** dialog on the preflight screen to add, edit, or remove custom words, daily care requests, or family names.
* Automatically saves to `phrases.json` and updates the phrase matrix dynamically.

### ⚙️ In-App API & Profile Configuration
* Open the **`⚙️ API Settings`** modal to input your EMOTIV Developer **Client ID**, **Client Secret**, and trained **Profile Name**.
* Saves credentials to `config.json` and prompts automatically on initial startup if configuration files are missing.

### 🔊 Speech & Editing Controls
* **Offline Text-to-Speech (TTS):** Integrated `pyttsx3` voice engine with an asynchronous worker thread so audio playback never freezes matrix scanning.
* **Single-Character Backspace:** Edit messages tile-by-tile via the `⌫ BACKSPACE` button without clearing the entire sentence.
* **Scanner Pause/Resume:** Freeze matrix cycling at any time using the `⏸️ PAUSE` button or the `P` key on your keyboard.

### Live Device & Cooldown Diagnostics
* **Battery & Signal Status:** Live real-time telemetry displaying headset battery percentage (`🔋`) and signal quality strength (`📶`).
* **Telemetry Cooldown Banner:** Prominent live visual countdown (`⏳ BCI PAUSE — RESUMING IN 2.1s`) rendered directly in the top state tracker during selection locks.

---

## 🛠️ Running from source

### 1. Hardware & Software Requirements
* An **EMOTIV Insight** or **EPOC/EPOC+** headset.
* **EMOTIV Launcher** installed and running in the background (enables the local Cortex WebSocket service at `wss://localhost:6868`).
* Python installed on your system.

### 2. Install Required Python Libraries

Run the following command in your terminal:

```bash
pip install PyQt6 pyttsx3
websocket-client python-dispatch
```

Or, equivalently, from the pinned list in this repository:

```bash
pip install -r requirements.txt
```

### 3. Run it

```bash
python scanning_board_setupandconfig.py
```

The EMOTIV Launcher must be running first — it is what serves Cortex on
`wss://localhost:6868`. On the first launch the app asks for your EMOTIV
Developer Client ID, Client Secret and trained profile name; those are saved
for next time.

### Where your settings are kept

Running from a checkout, `config.json` and
`phrases.json` sit next to the source, as they always have. In an installed
build they move to a directory you can actually write to:

| | Location |
| :--- | :--- |
| Windows | `%APPDATA%\EmotivScanningBoard\` |
| macOS | `~/Library/Application Support/EmotivScanningBoard/` |

Uninstalling leaves both behind on purpose — reinstalling should not wipe a
phrase list somebody spent an afternoon building.

---

---

## 📦 Releasing

Builds come from [`.github/workflows/build.yml`](.github/workflows/build.yml),
which runs on `macos-14` and `windows-latest` and produces the two files above.

**To cut a release:**

```bash
git tag v1.0.0
git push origin v1.0.0
```

The tag triggers the workflow, which builds both platforms, creates the GitHub
release, and attaches the `.dmg` and the `-setup.exe` to it. The tag name minus
its leading `v` becomes the version stamped into the Windows installer.

**To test a build without releasing**, run the workflow manually from the
**Actions** tab. It builds exactly the same way but attaches the results as
workflow artifacts instead of publishing a release, and versions them `0.0.0`.

**What the build checks.** After packaging, each runner launches the bundle and
fails if it exits within 25 seconds. That catches the failure these builds are
actually prone to — a module that PyInstaller did not notice and therefore did
not include. It does not prove the UI rendered, and it does not exercise speech:
`pyttsx3` is imported lazily at the first spoken phrase, so a missing speech
driver would survive the check. Speak one phrase by hand before announcing a
release.

**To build locally:**

```bash
pip install -r requirements.txt pyinstaller pillow
python packaging/make_icon.py
pyinstaller packaging/BCIScanningBoard.spec --noconfirm
iscc packaging/BCIScanningBoard.iss          # Windows installer, needs Inno Setup 6
```

**Icons.** They are generated, not committed: `packaging/make_icon.py` builds
the Windows `.ico` and the macOS `.icns` from `assets/logo.png`, and the
workflow runs it before PyInstaller. Change the logo and every icon follows on
the next build. To refresh them locally:

```bash
pip install pillow
python packaging/make_icon.py
```

The wordmark is dropped below 256px and the speech board below 128px, where
neither is legible any more and both only cost the head its size; at 16px the
ink is thickened before the downscale, or the outline washes out to grey.
