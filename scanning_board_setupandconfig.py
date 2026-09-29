### ---------------------------------------------------------------------------------- ###
# EMOTIV BCI Assistive Communication System
# Original author: Jordan Labio
#
# A row/column scanning communication board driven by mental commands and
# facial EMG, with text-to-speech output.
#
#               Version History:
#               2026-07-23
                # - Added CortexCredentialsDialog class, which acts as a configurable settings file dialog for entering EMOTIV Cortex API credentials and Profile Name.
                # - Added a settings menu to include custom phrases. --> saved in phrases.json file.
                # - Added realtime battery and signal monitoring to the device screen.
#               2026-07-27
                # - Added Action Mapping Dropdowns in API screen: Choose from standard EMOTIV mental commands and facial EMG expressions for both SELECT and CHANGE SPEED actions.
                # - route_bci_command and route_facial_command now evaluate incoming WebSocket triggers against your custom assigned mappings instead of hardcoded strings.
#               2026-07-29
                # - Removed the strict warning requiring Client ID and Client Secret to be filled in. Users can leave these blank if your application relies on cloud licensing, auto-discovery, or first-party pre-approved credentials.
                # - Added the "Include Mental Commands" and "Include Facial Expressions" checkboxes directly into the ⚙️ API Settings dialog.
#               2026-09-28
                # - Headset picker: the app no longer connects to whichever headset answered first. Screen 1 lists every headset Cortex reports and the caregiver chooses.
                # - Any EMOTIV headset: the sensor map is built from the channel names Cortex returns, so Insight (5), EPOC X (14) and MN8 (2) all draw correctly.
                # - MN8 has no facial expression stream, so facial input is disabled and explained rather than silently never firing.
                # - Contact and EEG quality are now monitored during a session, not only before it, and shown on the board itself.
                # - Chinese translation (interface and the phrase board), switchable at any time.
                # - Stream parsing moved onto Cortex's own events instead of guessing array offsets out of raw WebSocket frames.
### ---------------------------------------------------------------------------------- ###


import sys
import json
import os
import time
import threading
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout,
                             QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
                             QStackedWidget, QCheckBox, QSlider, QDialog,
                             QLineEdit, QFormLayout, QMessageBox, QListWidget,
                             QInputDialog, QComboBox, QScrollArea, QFrame)
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QIcon

# Settings are written by the app, so they cannot live next to an installed
# executable. app_paths resolves them to the user's own data directory in a
# packaged build, and next to the source when running from a checkout.
from app_paths import CONFIG_PATH, PHRASES_PATH, window_icon_path

import devices
import i18n
from i18n import t

# --- DEFAULT MATRIX PHRASES ---
# These are TOKENS, not labels. What appears on the button is i18n.cell(token),
# which is how the same board speaks English or Chinese without the scanning
# logic knowing anything about language.
DEFAULT_PHRASES_LIST = [
    "I HAVE TO TELL YOU SOMETHING", "I LOVE YOU", "YES", "NO", "THANK YOU", "YOU'RE WELCOME", "HELLO",
    "I AM", "HAPPY", "SAD", "TIRED", "HOT", "COLD", "EXCITED",
    "I HAVE A PROBLEM", "PAIN", "CRAMP", "ITCH", "STOP", "SICK", "UNCOMFORTABLE",
    "I NEED", "SUCTION", "MEDICINE", "BATHE", "BATHROOM", "BED", "BREATHING MACHINE",
    "MASSAGE", "LEG", "ARM", "HIPS", "HEAD", "LEFT", "RIGHT",
    "I WANT", "FOOD", "DRINK", "TV", "PHONE", "COMPUTER", "HELP",
    "TO GO", "TO CALL", "A HUG", "A KISS", "COMPANY", "FLIP OVER", "SOMETHING ELSE"
]

MENTAL_COMMAND_OPTIONS = ["push", "pull", "lift", "drop", "left", "right", "rotateClockwise", "rotateCounterClockwise", "disappear", "None"]
FACIAL_EXPRESSION_OPTIONS = ["clench", "furrow", "smile", "surprise", "smirkLeft", "smirkRight", "laugh", "None"]

# Labels Cortex includes with the electrodes that are not electrodes.
NON_SENSOR_LABELS = {"OVERALL", "CMS", "DRL", "BATTERY", "SIGNAL"}

ACTION_TOKENS = {"FLIP OVER", "SPEAK", "BACKSPACE", "PAUSE SCANNER",
                 "CLEAR MESSAGE", "SPACE"}


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if isinstance(cfg, dict):
                    return cfg
        except Exception as e:
            print(f"[config] could not read {CONFIG_PATH}: {e}")
    return {}


def save_config(patch: dict):
    """Merge into config.json, so one screen's setting never wipes another's."""
    cfg = load_config()
    cfg.update(patch)
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[config] could not write {CONFIG_PATH}: {e}")


def load_phrases_from_file():
    if os.path.exists(PHRASES_PATH):
        try:
            with open(PHRASES_PATH, "r", encoding="utf-8") as f:
                phrases = json.load(f)
                if isinstance(phrases, list) and len(phrases) > 0:
                    return phrases
        except Exception as e:
            print(f"[Phrases] Error loading phrases.json: {e}")
    return DEFAULT_PHRASES_LIST[:]

def build_phrase_matrix(phrases_list):
    items = phrases_list[:]
    if "FLIP OVER" not in items:
        items.append("FLIP OVER")

    matrix = []
    col_count = 7
    for i in range(0, len(items), col_count):
        row = items[i:i+col_count]
        while len(row) < col_count:
            row.append("")
        matrix.append(row)
    return matrix

BOARD_1_PHRASES = build_phrase_matrix(load_phrases_from_file())

BOARD_2_ALPHA = [
    ["A", "B", "C", "D", "YES", "NO"],
    ["E", "F", "G", "H", "MAYBE", "I DON'T KNOW"],
    ["I", "J", "K", "L", "M", "N"],
    ["O", "P", "QU", "R", "S", "T"],
    ["U", "V", "W", "X", "Y", "Z"],
    ["1", "2", "3", "4", "5", "6"],
    ["7", "8", "9", "0", "THANK YOU", "SOMETHING ELSE"],
    ["BACKSPACE", "SPEAK", "SPACE", "PAUSE SCANNER", "CLEAR MESSAGE", "FLIP OVER"]
]


class PhraseManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("phrases.title"))
        self.setFixedSize(520, 420)

        self.setStyleSheet("""
            QDialog { background-color: #ffffff; font-family: 'Segoe UI'; }
            QLabel { color: #1e293b; font-size: 11px; font-weight: bold; }
            QListWidget {
                color: #0f172a; background-color: #f8fafc;
                border: 1px solid #cbd5e1; border-radius: 6px;
                padding: 6px; font-size: 11px; font-weight: bold;
            }
            QListWidget::item:selected {
                background-color: #d9145a; color: #ffffff; border-radius: 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        header_lbl = QLabel(t("phrases.header"))
        header_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header_lbl.setStyleSheet("color: #d9145a; margin-bottom: 5px;")
        layout.addWidget(header_lbl)

        sub_lbl = QLabel(t("phrases.subtitle"))
        sub_lbl.setFont(QFont("Segoe UI", 9))
        sub_lbl.setStyleSheet("color: #64748b; margin-bottom: 10px;")
        sub_lbl.setWordWrap(True)
        layout.addWidget(sub_lbl)

        body_layout = QHBoxLayout()
        self.phrase_list_widget = QListWidget()
        body_layout.addWidget(self.phrase_list_widget, stretch=1)

        btn_column = QVBoxLayout()
        btn_column.setSpacing(8)

        add_btn = QPushButton("+ " + t("phrases.add"))
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("QPushButton { padding: 8px; background-color: #2ecc71; color: white; border-radius: 4px; font-weight: bold; } QPushButton:hover { background-color: #27ae60; }")
        add_btn.clicked.connect(self.add_phrase)
        btn_column.addWidget(add_btn)

        edit_btn = QPushButton("✏️")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setStyleSheet("QPushButton { padding: 8px; background-color: #4f5d75; color: white; border-radius: 4px; font-weight: bold; } QPushButton:hover { background-color: #3b4758; }")
        edit_btn.clicked.connect(self.edit_phrase)
        btn_column.addWidget(edit_btn)

        delete_btn = QPushButton("🗑️ " + t("phrases.remove"))
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setStyleSheet("QPushButton { padding: 8px; background-color: #e74c3c; color: white; border-radius: 4px; font-weight: bold; } QPushButton:hover { background-color: #c0392b; }")
        delete_btn.clicked.connect(self.delete_phrase)
        btn_column.addWidget(delete_btn)

        btn_column.addStretch()
        body_layout.addLayout(btn_column)
        layout.addLayout(body_layout)

        layout.addSpacing(10)
        footer_btn_layout = QHBoxLayout()
        footer_btn_layout.addStretch()

        cancel_btn = QPushButton(t("phrases.cancel"))
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("QPushButton { padding: 8px 16px; border: 1px solid #cbd5e1; border-radius: 4px; background: #f1f5f9; color: #334155; font-weight: bold; }")
        cancel_btn.clicked.connect(self.reject)
        footer_btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton(t("phrases.save"))
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet("QPushButton { padding: 8px 20px; background-color: #d9145a; color: white; border-radius: 4px; font-weight: bold; } QPushButton:hover { background-color: #b00f46; }")
        save_btn.clicked.connect(self.save_phrases)
        footer_btn_layout.addWidget(save_btn)

        layout.addLayout(footer_btn_layout)

        self.populate_phrase_list()

    def populate_phrase_list(self):
        self.phrase_list_widget.clear()
        phrases = load_phrases_from_file()
        for p in phrases:
            if p != "FLIP OVER":
                # Shown translated where we have a translation, so a Chinese
                # caregiver reads the board's own vocabulary in Chinese.
                item_text = i18n.cell(p)
                self.phrase_list_widget.addItem(item_text)
                self.phrase_list_widget.item(
                    self.phrase_list_widget.count() - 1).setData(
                        Qt.ItemDataRole.UserRole, p)

    def _tokens(self):
        tokens = []
        for i in range(self.phrase_list_widget.count()):
            item = self.phrase_list_widget.item(i)
            token = item.data(Qt.ItemDataRole.UserRole) or item.text()
            tokens.append(token)
        return tokens

    def add_phrase(self):
        text, ok = QInputDialog.getText(self, t("phrases.prompt_title"),
                                        t("phrases.prompt_body"))
        if ok and text.strip():
            clean_text = text.strip().upper()
            self.phrase_list_widget.addItem(clean_text)
            self.phrase_list_widget.item(
                self.phrase_list_widget.count() - 1).setData(
                    Qt.ItemDataRole.UserRole, clean_text)

    def edit_phrase(self):
        current_item = self.phrase_list_widget.currentItem()
        if not current_item:
            return
        text, ok = QInputDialog.getText(self, t("phrases.prompt_title"),
                                        t("phrases.prompt_body"),
                                        QLineEdit.EchoMode.Normal,
                                        current_item.text())
        if ok and text.strip():
            current_item.setText(text.strip().upper())
            current_item.setData(Qt.ItemDataRole.UserRole, text.strip().upper())

    def delete_phrase(self):
        row = self.phrase_list_widget.currentRow()
        if row >= 0:
            self.phrase_list_widget.takeItem(row)

    def save_phrases(self):
        phrases = self._tokens()
        if "FLIP OVER" not in phrases:
            phrases.append("FLIP OVER")
        try:
            with open(PHRASES_PATH, "w", encoding="utf-8") as f:
                json.dump(phrases, f, indent=4, ensure_ascii=False)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save phrases.json:\n{e}")


class CortexCredentialsDialog(QDialog):
    def __init__(self, parent=None, facial_supported=True):
        super().__init__(parent)
        self.facial_supported = facial_supported
        self.setWindowTitle(t("creds.title"))
        self.setFixedSize(540, 520)

        self.setStyleSheet("""
            QDialog { background-color: #ffffff; font-family: 'Segoe UI'; }
            QLabel { color: #1e293b; font-size: 11px; font-weight: bold; }
            QLineEdit, QComboBox {
                color: #0f172a; background-color: #f8fafc; padding: 5px;
                border: 1px solid #cbd5e1; border-radius: 4px; font-size: 11px;
            }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #d9145a; background-color: #ffffff; }
            QCheckBox { color: #334155; font-size: 11px; font-weight: bold; spacing: 6px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)

        header_lbl = QLabel(t("creds.title"))
        header_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header_lbl.setStyleSheet("color: #d9145a; margin-bottom: 2px;")
        layout.addWidget(header_lbl)

        sub_lbl = QLabel(t("creds.help"))
        sub_lbl.setFont(QFont("Segoe UI", 9))
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet("color: #64748b; margin-bottom: 10px;")
        layout.addWidget(sub_lbl)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.client_id_input = QLineEdit()
        form_layout.addRow(t("creds.client_id") + ":", self.client_id_input)

        self.client_secret_input = QLineEdit()
        self.client_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow(t("creds.client_secret") + ":", self.client_secret_input)

        self.profile_name_input = QLineEdit()
        self.profile_name_input.setPlaceholderText("e.g. John_Insight")
        form_layout.addRow(t("creds.profile") + ":", self.profile_name_input)

        sep_label1 = QLabel("───────────")
        sep_label1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sep_label1.setStyleSheet("color: #94a3b8; font-size: 10px; margin-top: 6px; margin-bottom: 2px;")
        form_layout.addRow(sep_label1)

        self.include_mental_cb = QCheckBox(t("creds.include_mental"))
        self.include_mental_cb.setChecked(True)
        form_layout.addRow("", self.include_mental_cb)

        self.include_facial_cb = QCheckBox(t("creds.include_facial"))
        self.include_facial_cb.setChecked(True)
        form_layout.addRow("", self.include_facial_cb)

        sep_label2 = QLabel("───────────")
        sep_label2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sep_label2.setStyleSheet("color: #94a3b8; font-size: 10px; margin-top: 6px; margin-bottom: 2px;")
        form_layout.addRow(sep_label2)

        self.select_thought_combo = QComboBox()
        self.select_thought_combo.addItems(MENTAL_COMMAND_OPTIONS)
        form_layout.addRow(t("creds.select_thought") + ":", self.select_thought_combo)

        self.select_facial_combo = QComboBox()
        self.select_facial_combo.addItems(FACIAL_EXPRESSION_OPTIONS)
        self.select_facial_row = form_layout.rowCount()
        form_layout.addRow(t("creds.select_facial") + ":", self.select_facial_combo)

        self.speed_thought_combo = QComboBox()
        self.speed_thought_combo.addItems(MENTAL_COMMAND_OPTIONS)
        form_layout.addRow(t("creds.speed_thought") + ":", self.speed_thought_combo)

        self.speed_facial_combo = QComboBox()
        self.speed_facial_combo.addItems(FACIAL_EXPRESSION_OPTIONS)
        form_layout.addRow(t("creds.speed_facial") + ":", self.speed_facial_combo)

        if not facial_supported:
            # Offering a facial trigger on a headset that has no facial stream
            # would be a setting that silently never fires.
            note = QLabel(t("board.facial_unsupported"))
            note.setWordWrap(True)
            note.setStyleSheet("color: #d9145a; font-weight: bold; font-size: 10px;")
            form_layout.addRow("", note)
            for widget in (self.include_facial_cb, self.select_facial_combo,
                           self.speed_facial_combo):
                widget.setEnabled(False)
            self.include_facial_cb.setChecked(False)

        layout.addLayout(form_layout)
        layout.addSpacing(15)

        self.load_existing_config()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton(t("creds.cancel"))
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("QPushButton { padding: 8px 16px; border: 1px solid #cbd5e1; border-radius: 4px; background: #f1f5f9; color: #334155; font-weight: bold; }")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton(t("creds.save"))
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        save_btn.setStyleSheet("QPushButton { padding: 8px 20px; background-color: #d9145a; color: white; border-radius: 4px; font-weight: bold; } QPushButton:hover { background-color: #b00f46; }")
        save_btn.clicked.connect(self.save_config)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def load_existing_config(self):
        cfg = load_config()
        if not cfg:
            return
        self.client_id_input.setText(cfg.get("cortex_client_id", cfg.get("client_id", "")))
        self.client_secret_input.setText(cfg.get("cortex_client_secret", cfg.get("client_secret", "")))
        self.profile_name_input.setText(cfg.get("profile_name", ""))

        self.include_mental_cb.setChecked(cfg.get("include_mental_commands", True))
        if self.facial_supported:
            self.include_facial_cb.setChecked(cfg.get("include_facial_expressions", True))

        sel_th = cfg.get("select_thought", "push")
        sel_fc = cfg.get("select_facial", "clench")
        spd_th = cfg.get("speed_thought", "pull")
        spd_fc = cfg.get("speed_facial", "furrow")

        if sel_th in MENTAL_COMMAND_OPTIONS: self.select_thought_combo.setCurrentText(sel_th)
        if sel_fc in FACIAL_EXPRESSION_OPTIONS: self.select_facial_combo.setCurrentText(sel_fc)
        if spd_th in MENTAL_COMMAND_OPTIONS: self.speed_thought_combo.setCurrentText(spd_th)
        if spd_fc in FACIAL_EXPRESSION_OPTIONS: self.speed_facial_combo.setCurrentText(spd_fc)

    def save_config(self):
        save_config({
            "cortex_client_id": self.client_id_input.text().strip(),
            "cortex_client_secret": self.client_secret_input.text().strip(),
            "profile_name": self.profile_name_input.text().strip(),
            "include_mental_commands": self.include_mental_cb.isChecked(),
            "include_facial_expressions": self.include_facial_cb.isChecked(),
            "select_thought": self.select_thought_combo.currentText(),
            "select_facial": self.select_facial_combo.currentText(),
            "speed_thought": self.speed_thought_combo.currentText(),
            "speed_facial": self.speed_facial_combo.currentText(),
        })
        self.accept()


class TTSThread(QThread):
    def __init__(self, text, language="en"):
        super().__init__()
        self.text = text
        self.language = language

    def run(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            self._select_voice(engine)
            engine.say(self.text)
            engine.runAndWait()
        except Exception as e:
            print(f"[TTS Exception] {e}")

    def _select_voice(self, engine):
        """Pick a voice that can actually pronounce the text.

        The board speaks whatever language its labels are in, and the default
        system voice will read Chinese characters as silence. If no Chinese
        voice is installed we say so in the log rather than failing quietly —
        installing one is a Windows/macOS setting, not something the app can do.
        """
        if self.language != "zh":
            return
        try:
            wanted = ("chinese", "zh_", "zh-", "huihui", "yaoyao", "tingting",
                      "mandarin", "中文")
            for voice in engine.getProperty("voices"):
                haystack = f"{voice.id} {getattr(voice, 'name', '')}".lower()
                if any(token in haystack for token in wanted):
                    engine.setProperty("voice", voice.id)
                    return
            print("[TTS] No Chinese voice is installed; speech will be wrong or "
                  "silent. Add one in the operating system's speech settings.")
        except Exception as e:
            print(f"[TTS] Could not inspect voices: {e}")


class EmotivCortexWorker(QThread):
    """Owns the Cortex connection and translates its events into Qt signals.

    Everything here used to be read out of raw WebSocket frames by guessing
    array offsets, which is what tied the app to one five-sensor headset. It now
    listens to Cortex's own events and takes the channel names from the
    subscription result, so the number and names of sensors come from the
    hardware rather than from a constant.
    """

    headsets_signal = pyqtSignal(list)
    connected_signal = pyqtSignal(str)
    contact_quality_signal = pyqtSignal(dict)
    eeg_quality_signal = pyqtSignal(dict)
    device_diagnostics_signal = pyqtSignal(int, int)
    mental_command_signal = pyqtSignal(str, float)
    facial_expression_signal = pyqtSignal(str, float, str, float)
    status_signal = pyqtSignal(str, dict)
    stream_failed_signal = pyqtSignal(str, str)
    # "credentials" | "pending" | "granted" | "rejected" | "failed", plus detail
    access_state_signal = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.cortex = None
        self._lock = threading.Lock()
        self._labels = {}
        self._wanted_headset = ""
        self._want_facial = True
        self._profile_name = ""

    # ── called from the UI thread ────────────────────────────────────────
    def connect_to(self, headset_id: str, want_facial: bool = True):
        """Choose the headset and let the connection sequence continue."""
        self._wanted_headset = headset_id
        self._want_facial = want_facial
        with self._lock:
            if self.cortex:
                self.cortex.set_wanted_headset(headset_id)
                try:
                    self.cortex.query_headset()
                except Exception as e:
                    self.status_signal.emit("status.failed", {"detail": str(e)})

    def refresh_headsets(self):
        with self._lock:
            if self.cortex:
                try:
                    self.cortex.query_headset()
                except Exception as e:
                    self.status_signal.emit("status.failed", {"detail": str(e)})

    def retry_access(self):
        """Ask Cortex again whether the user has approved us in the Launcher."""
        with self._lock:
            if self.cortex:
                try:
                    self.cortex.retry_access()
                except Exception as e:
                    self.status_signal.emit("status.failed", {"detail": str(e)})

    # ── the thread itself ────────────────────────────────────────────────
    def run(self):
        self.status_signal.emit("status.connecting", {})

        cfg = load_config()
        client_id = cfg.get("cortex_client_id", cfg.get("client_id", "")).strip()
        client_secret = cfg.get("cortex_client_secret", cfg.get("client_secret", "")).strip()
        profile_name = cfg.get("profile_name", "")

        # Without keys there is nothing to authorize with, and Cortex would
        # answer with an error the user cannot act on. Ask first instead.
        if not client_id or not client_secret:
            self.access_state_signal.emit("credentials", "")
            return

        try:
            from cortex import Cortex
        except ImportError:
            self.status_signal.emit("status.no_cortex_file", {})
            return

        try:
            cortex = Cortex(client_id, client_secret)
            with self._lock:
                self.cortex = cortex

            # Every listener has to be a bound method, never a lambda or a
            # local function: python-dispatch keeps listeners WEAKLY, so a
            # lambda passed straight into bind() is collected before the event
            # can ever reach it. That is what made the app authorize, connect,
            # and then sit there forever with no data: the session was created
            # and nothing subscribed.
            self._profile_name = profile_name
            cortex.bind(headset_list_done=self._on_headset_list)
            cortex.bind(create_session_done=self._on_session)
            cortex.bind(new_data_labels=self._on_labels)
            cortex.bind(new_dev_data=self._on_dev)
            cortex.bind(new_eq_data=self._on_eq)
            cortex.bind(new_com_data=self._on_com)
            cortex.bind(new_fe_data=self._on_fac)
            cortex.bind(sub_failure=self._on_sub_failure)
            cortex.bind(inform_error=self._on_error)
            cortex.bind(access_pending=self._on_access_pending)
            cortex.bind(access_granted=self._on_access_granted)
            cortex.bind(access_rejected=self._on_access_rejected)

            self.status_signal.emit("status.linked", {})
            cortex.open()
        except Exception as e:
            self.status_signal.emit("status.failed", {"detail": str(e)})

    # ── Cortex events ────────────────────────────────────────────────────
    def _on_headset_list(self, *args, **kwargs):
        data = kwargs.get("data", args[0] if args else [])
        headsets = []
        for entry in data or []:
            if not isinstance(entry, dict):
                continue
            headsets.append({
                "id": entry.get("id", ""),
                "status": entry.get("status", ""),
                "connectedBy": entry.get("connectedBy", ""),
                "firmware": entry.get("firmware", ""),
                "settings": entry.get("settings", {}) or {},
            })
        self.headsets_signal.emit(headsets)

    def _on_session(self, *args, **kwargs):
        profile_name = self._profile_name
        headset_id = ""
        with self._lock:
            if self.cortex:
                headset_id = getattr(self.cortex, "headset_id", "") or ""
        self.connected_signal.emit(headset_id)

        if profile_name:
            self.status_signal.emit("status.loading_profile", {"profile": profile_name})
            with self._lock:
                if self.cortex and hasattr(self.cortex, "setup_profile"):
                    try:
                        self.cortex.setup_profile(profile_name, "load")
                    except Exception as e:
                        print(f"[cortex] could not load profile: {e}")

        streams = devices.streams_for(headset_id, self._want_facial)
        with self._lock:
            if self.cortex:
                self.cortex.sub_request(streams)

    def _on_labels(self, *args, **kwargs):
        data = kwargs.get("data", args[0] if args else {})
        if not isinstance(data, dict):
            return
        stream = data.get("streamName", "")
        labels = [str(x) for x in (data.get("labels") or [])]
        self._labels[stream] = labels

    def _quality_map(self, stream, values):
        """Pair the grades with their channel names, dropping the non-electrodes."""
        labels = self._labels.get(stream, [])
        pairs = zip(labels, values) if labels else []
        return {name: int(value) for name, value in pairs
                if str(name).upper() not in NON_SENSOR_LABELS
                and isinstance(value, (int, float))}

    def _on_dev(self, *args, **kwargs):
        data = kwargs.get("data", args[0] if args else {})
        if not isinstance(data, dict):
            return
        battery = data.get("batteryPercent")
        signal = data.get("signal")
        if isinstance(battery, (int, float)) and isinstance(signal, (int, float)):
            # `signal` is 0-2 from Cortex (0 bad, 1 good, 2 excellent-ish).
            self.device_diagnostics_signal.emit(
                int(battery), int(min(100, max(0, signal * 50))))

        mapping = self._quality_map("dev", data.get("dev") or [])
        if mapping:
            self.contact_quality_signal.emit(mapping)
            self.status_signal.emit("status.live", {})

    def _on_eq(self, *args, **kwargs):
        data = kwargs.get("data", args[0] if args else {})
        if not isinstance(data, dict):
            return
        mapping = self._quality_map("eq", data.get("eq") or [])
        if mapping:
            self.eeg_quality_signal.emit(mapping)

    def _on_com(self, *args, **kwargs):
        data = kwargs.get("data", args[0] if args else {})
        if isinstance(data, dict) and "action" in data and "power" in data:
            self.mental_command_signal.emit(str(data["action"]), float(data["power"]))

    def _on_fac(self, *args, **kwargs):
        data = kwargs.get("data", args[0] if args else {})
        if not isinstance(data, dict):
            return
        self.facial_expression_signal.emit(
            str(data.get("uAct", "")), float(data.get("uPow", 0.0) or 0.0),
            str(data.get("lAct", "")), float(data.get("lPow", 0.0) or 0.0))

    def _on_sub_failure(self, *args, **kwargs):
        stream = kwargs.get("stream", "")
        message = kwargs.get("message", "")
        self.stream_failed_signal.emit(str(stream), str(message))

    def _on_access_pending(self, *args, **kwargs):
        self.access_state_signal.emit("pending", str(kwargs.get("data", "")))
        self.status_signal.emit("status.awaiting_approval", {})

    def _on_access_granted(self, *args, **kwargs):
        self.access_state_signal.emit("granted", "")
        self.status_signal.emit("status.access_granted", {})

    def _on_access_rejected(self, *args, **kwargs):
        self.access_state_signal.emit("rejected", str(kwargs.get("data", "")))
        self.status_signal.emit("status.access_rejected", {})

    def _on_error(self, *args, **kwargs):
        error = kwargs.get("error_data", {})
        detail = error.get("message", str(error)) if isinstance(error, dict) else str(error)
        request_id = kwargs.get("request_id")

        # 3 is requestAccess and 4 is authorize; either failing means the keys
        # themselves are the problem, which is a different thing to fix than a
        # headset or a stream going wrong.
        if request_id in (3, 4):
            self.access_state_signal.emit("failed", detail)
        self.status_signal.emit("status.failed", {"detail": detail})


class HeadsetMapWidget(QWidget):
    """The head seen from above, with whatever sensors this headset has.

    The positions come from devices.layout_for(), so five, fourteen or two
    electrodes all draw correctly and an unfamiliar headset still shows every
    channel it reports.
    """

    def __init__(self):
        super().__init__()
        self.setFixedSize(360, 360)
        self.channels = []
        self.cq_status = {}
        self.eq_status = {}
        self.display_mode = "CQ"

    def set_channels(self, channels):
        self.channels = [c for c in (channels or [])
                         if str(c).upper() not in NON_SENSOR_LABELS]
        self.cq_status = {c: self.cq_status.get(c, 0) for c in self.channels}
        self.eq_status = {c: self.eq_status.get(c, 0) for c in self.channels}
        self.update()

    def update_quality(self, mode, mapping):
        target = self.cq_status if mode == "CQ" else self.eq_status
        target.update(mapping)
        if not self.channels:
            self.set_channels(list(mapping.keys()))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setBrush(QColor("#eef2f7"))
        painter.setPen(QPen(QColor("#cbd5e1"), 2))
        painter.drawEllipse(40, 40, 280, 280)

        # The nose, so left and right are never ambiguous.
        painter.setBrush(QColor("#cbd5e1"))
        painter.drawPolygon([QPoint(165, 40), QPoint(195, 40), QPoint(180, 15)])

        active = self.cq_status if self.display_mode == "CQ" else self.eq_status
        placed = devices.layout_for(self.channels)
        radius = 14 if len(placed) > 8 else 16
        font_size = 7 if len(placed) > 8 else 8

        for name, nx, ny in placed:
            x = 180 + int(nx * 140)
            y = 180 + int(ny * 140)
            val = active.get(name, 0)

            if val >= 3:
                node_color, border_color = QColor("#2ecc71"), QColor("#27ae60")
            elif val > 0:
                node_color, border_color = QColor("#f39c12"), QColor("#d35400")
            else:
                node_color, border_color = QColor("#1e1e24"), QColor("#334155")

            painter.setBrush(node_color)
            painter.setPen(QPen(border_color, 2))
            painter.drawEllipse(x - radius, y - radius, radius * 2, radius * 2)

            painter.setPen(QPen(QColor("#ffffff") if val == 0 else QColor("#111111")))
            painter.setFont(QFont("Segoe UI", font_size, QFont.Weight.Bold))
            painter.drawText(x - radius + 1, y + 4, name)


class QualityPill(QWidget):
    """Contact, EEG and battery at a glance, live, on the board screen.

    The pre-flight screen answers "is the headset on properly" once. This
    answers "is it still on properly" for the rest of the session, which is the
    question that actually matters when a selection stops working.
    """

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(12)

        self.device_lbl = QLabel("—")
        self.device_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.device_lbl.setStyleSheet("color: #1e293b; border: none;")
        layout.addWidget(self.device_lbl)

        self.contact_lbl = QLabel()
        self.contact_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(self.contact_lbl)

        self.eeg_lbl = QLabel()
        self.eeg_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(self.eeg_lbl)

        self.battery_lbl = QLabel()
        self.battery_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(self.battery_lbl)

        self.setStyleSheet("QWidget { background-color: #ffffff; border: 1px solid #e2e8f0;"
                           "border-radius: 6px; }")
        self.set_device("")
        self.set_contact(None)
        self.set_eeg(None)
        self.set_battery(None)

    @staticmethod
    def _colour(percent):
        if percent is None:
            return "#94a3b8"
        if percent >= 80:
            return "#27ae60"
        if percent >= 50:
            return "#f39c12"
        return "#d9145a"

    def set_device(self, headset_id):
        self.device_lbl.setText(headset_id or t("pill.no_data"))

    def set_contact(self, percent):
        text = t("pill.contact", percent=percent if percent is not None else t("pill.no_data"))
        self.contact_lbl.setText(text)
        self.contact_lbl.setStyleSheet(f"color: {self._colour(percent)}; border: none;")

    def set_eeg(self, percent):
        text = t("pill.eeg", percent=percent if percent is not None else t("pill.no_data"))
        self.eeg_lbl.setText(text)
        self.eeg_lbl.setStyleSheet(f"color: {self._colour(percent)}; border: none;")

    def set_battery(self, percent):
        text = t("pill.battery", percent=percent if percent is not None else t("pill.no_data"))
        self.battery_lbl.setText(text)
        self.battery_lbl.setStyleSheet(f"color: {self._colour(percent)}; border: none;")


PAGE_DEVICES = 0
PAGE_PREFLIGHT = 1
PAGE_BOARD = 2


class BCICommunicationBoard(QMainWindow):
    def __init__(self):
        super().__init__()

        cfg = load_config()
        i18n.set_language(cfg.get("language", "en"))
        self.setWindowTitle(t("app.title"))

        self.page_container = QStackedWidget()
        self.setCentralWidget(self.page_container)

        self.current_setup_tab = "CQ"
        self.headsets = []
        self.selected_headset = ""
        self.device_facial_supported = True
        self.contact_percent = None
        self.eeg_percent = None
        self.battery_percent = None

        self.load_bci_action_mappings()
        self.build_device_screen()
        self.build_preflight_screen()
        self.build_keyboard_screen()

        self.page_container.addWidget(self.device_page)
        self.page_container.addWidget(self.setup_page)
        self.page_container.addWidget(self.keyboard_page)
        self.page_container.setCurrentIndex(PAGE_DEVICES)

        self.cortex_thread = None
        self.start_cortex_worker()

        QTimer.singleShot(500, self.check_credentials_on_launch)

    # ── configuration ────────────────────────────────────────────────────
    def load_bci_action_mappings(self):
        cfg = load_config()
        self.select_thought = cfg.get("select_thought", "push")
        self.select_facial = cfg.get("select_facial", "clench")
        self.speed_thought = cfg.get("speed_thought", "pull")
        self.speed_facial = cfg.get("speed_facial", "furrow")
        self.init_include_mental = cfg.get("include_mental_commands", True)
        self.init_include_facial = cfg.get("include_facial_expressions", True)

    def closeEvent(self, event):
        print("[SYSTEM] Shutting down application...")
        for timer_name in ("timer", "cooldown_ticker"):
            timer = getattr(self, timer_name, None)
            if timer:
                timer.stop()

        event.accept()
        QApplication.quit()

        import os
        os._exit(0)

    def start_cortex_worker(self):
        if self.cortex_thread and self.cortex_thread.isRunning():
            self.cortex_thread.quit()
            self.cortex_thread.wait(500)

        self.cortex_thread = EmotivCortexWorker()
        self.cortex_thread.headsets_signal.connect(self.on_headsets)
        self.cortex_thread.connected_signal.connect(self.on_headset_connected)
        self.cortex_thread.status_signal.connect(self.display_network_logs)
        self.cortex_thread.device_diagnostics_signal.connect(self.update_device_diagnostics)
        self.cortex_thread.contact_quality_signal.connect(self.process_contact_quality)
        self.cortex_thread.eeg_quality_signal.connect(self.process_eeg_quality)
        self.cortex_thread.mental_command_signal.connect(self.route_bci_command)
        self.cortex_thread.facial_expression_signal.connect(self.route_facial_command)
        self.cortex_thread.stream_failed_signal.connect(self.on_stream_failed)
        self.cortex_thread.access_state_signal.connect(self.on_access_state)
        self.cortex_thread.start()

    def check_credentials_on_launch(self):
        """Ask for the application keys the first time this screen is opened.

        A saved file is not the test — an empty Client ID in an existing file
        cannot authorize either, and the user should be asked rather than shown
        a Cortex error about it.
        """
        cfg = load_config()
        has_keys = (cfg.get("cortex_client_id", cfg.get("client_id", "")).strip()
                    and cfg.get("cortex_client_secret", cfg.get("client_secret", "")).strip())
        if not has_keys:
            self.on_access_state("credentials", "")
            self.open_credentials_dialog()

    def open_credentials_dialog(self):
        dlg = CortexCredentialsDialog(self, facial_supported=self.device_facial_supported)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # New keys mean the whole connection sequence starts again, from
            # asking Cortex whether this application is allowed to run.
            self.access_banner.setVisible(False)
            self.access_retry_timer.stop()
            self.load_bci_action_mappings()
            self.mental_selector.setChecked(self.init_include_mental)
            self.facial_selector.setChecked(
                self.init_include_facial and self.device_facial_supported)
            self.handle_stream_selectors_toggled()
            self.start_cortex_worker()

    def open_phrase_manager_dialog(self):
        dlg = PhraseManagerDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            global BOARD_1_PHRASES
            BOARD_1_PHRASES = build_phrase_matrix(load_phrases_from_file())
            self.boards["PHRASES"] = BOARD_1_PHRASES
            if self.current_board_name == "PHRASES":
                self.current_matrix = BOARD_1_PHRASES
                self.build_board_grid()

    # ── language ─────────────────────────────────────────────────────────
    def build_language_toggle(self):
        row = QHBoxLayout()
        row.setSpacing(4)
        self.language_buttons = {}
        for code, label in (("en", "EN"), ("zh", "中文")):
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(28)
            btn.setFixedWidth(52)
            btn.clicked.connect(lambda _checked, c=code: self.set_language(c))
            row.addWidget(btn)
            self.language_buttons.setdefault(code, []).append(btn)
        self.paint_language_toggle()
        return row

    def paint_language_toggle(self):
        for code, buttons in getattr(self, "language_buttons", {}).items():
            active = (code == i18n.language())
            for btn in buttons:
                btn.setStyleSheet(
                    "QPushButton { background-color: %s; color: %s; border: 1px solid "
                    "#cbd5e1; border-radius: 4px; font-weight: bold; }" % (
                        "#d9145a" if active else "#f1f5f9",
                        "#ffffff" if active else "#334155"))

    def set_language(self, code):
        if code == i18n.language():
            return
        i18n.set_language(code)
        save_config({"language": code})
        self.setWindowTitle(t("app.title"))
        self.paint_language_toggle()
        self.retranslate()

    def retranslate(self):
        """Redraw everything that is not a plain bound label."""
        self.render_headset_list()
        if self.access_state and self.access_banner.isVisible():
            self.on_access_state(self.access_state, self.access_detail)
        self.switch_setup_tab(self.current_setup_tab)
        self.build_board_grid()
        self.update_ui_highlights()
        self.update_status_bar()
        self.handle_stream_selectors_toggled()
        self.update_telemetry_box("neutral")
        # Re-say the current status in the new language rather than leaving the
        # last sentence behind.
        key, params = self.board_status
        colour = self.keyboard_network_status_label.styleSheet()
        colour = colour.split("color:")[-1].split(";")[0].strip() or "#2ecc71"
        self.set_board_status(key, colour, **params)
        self.refresh_quality_pill()
        self.display_box.setText(t("board.composed", text=self.composed_text))
        self.mental_slider_lbl.setText(
            t("board.mental_sens", value=f"{self.MENTAL_THRESHOLD:.2f}"))
        self.facial_slider_lbl.setText(
            t("board.facial_sens", value=f"{self.FACIAL_THRESHOLD:.2f}"))
        self.cooldown_slider_lbl.setText(
            t("board.cooldown", value=f"{self.SELECTION_COOLDOWN_MS/1000:.1f}"))
        self.update_preflight_metrics()

    # ── screen 1: which headset ──────────────────────────────────────────
    def build_device_screen(self):
        self.device_page = QWidget()
        self.device_page.setStyleSheet("background-color: #ffffff;")
        layout = QVBoxLayout(self.device_page)
        layout.setContentsMargins(40, 30, 40, 30)

        header = QHBoxLayout()
        title = i18n.bind(QLabel(), "device.title")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #1a1a1a;")
        header.addWidget(title)
        header.addStretch()
        header.addLayout(self.build_language_toggle())

        self.device_config_btn = i18n.bind(QPushButton(), "nav.api_settings")
        self.device_config_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.device_config_btn.setStyleSheet(
            "QPushButton { background-color: #f1f5f9; color: #334155; border: 1px solid "
            "#cbd5e1; padding: 6px 12px; border-radius: 4px; margin-left: 8px; } "
            "QPushButton:hover { background-color: #e2e8f0; }")
        self.device_config_btn.clicked.connect(self.open_credentials_dialog)
        header.addWidget(self.device_config_btn)
        layout.addLayout(header)

        subtitle = i18n.bind(QLabel(), "device.subtitle")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #64748b; margin-bottom: 12px;")
        layout.addWidget(subtitle)

        # Everything that stands between the user and a connection appears
        # here: missing keys, an approval waiting in EMOTIV Launcher, a refusal.
        self.access_banner = QWidget()
        self.access_banner.setStyleSheet(
            "QWidget { background-color: #fff1f2; border: 1px solid #f9a8c4;"
            "border-radius: 8px; }")
        banner_row = QHBoxLayout(self.access_banner)
        banner_row.setContentsMargins(16, 12, 16, 12)

        banner_text = QVBoxLayout()
        banner_text.setSpacing(2)
        self.access_title_lbl = QLabel()
        self.access_title_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.access_title_lbl.setStyleSheet("color: #9f1239; border: none;")
        banner_text.addWidget(self.access_title_lbl)

        self.access_body_lbl = QLabel()
        self.access_body_lbl.setFont(QFont("Segoe UI", 10))
        self.access_body_lbl.setWordWrap(True)
        self.access_body_lbl.setStyleSheet("color: #4f5d75; border: none;")
        banner_text.addWidget(self.access_body_lbl)
        banner_row.addLayout(banner_text, stretch=1)

        self.access_action_btn = QPushButton()
        self.access_action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.access_action_btn.setFixedSize(150, 42)
        self.access_action_btn.setStyleSheet(
            "QPushButton { background-color: #d9145a; color: white; border-radius: 4px;"
            "font-weight: bold; } QPushButton:hover { background-color: #b00f46; }")
        self.access_action_btn.clicked.connect(self.on_access_action)
        banner_row.addWidget(self.access_action_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.access_banner.setVisible(False)
        self.access_detail = ""
        layout.addWidget(self.access_banner)

        # While approval is outstanding, ask Cortex again on a timer as well as
        # on the button: the user approves in another window and should not have
        # to come back here and press anything.
        self.access_retry_timer = QTimer(self)
        self.access_retry_timer.setInterval(3000)
        self.access_retry_timer.timeout.connect(self.retry_access)
        self.access_state = ""

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.device_list_host = QWidget()
        self.device_list_layout = QVBoxLayout(self.device_list_host)
        self.device_list_layout.setContentsMargins(0, 0, 0, 0)
        self.device_list_layout.setSpacing(10)
        self.device_list_layout.addStretch()
        scroll.setWidget(self.device_list_host)
        layout.addWidget(scroll, stretch=1)

        footer = QHBoxLayout()
        self.device_status_lbl = i18n.bind(QLabel(), "device.searching")
        self.device_status_lbl.setFont(QFont("Segoe UI", 10))
        self.device_status_lbl.setStyleSheet("color: #64748b;")
        footer.addWidget(self.device_status_lbl)
        footer.addStretch()

        self.device_refresh_btn = i18n.bind(QPushButton(), "device.refresh")
        self.device_refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.device_refresh_btn.setFixedHeight(40)
        self.device_refresh_btn.setStyleSheet(
            "QPushButton { background-color: #f1f5f9; color: #334155; border: 1px solid "
            "#cbd5e1; padding: 8px 18px; border-radius: 4px; font-weight: bold; } "
            "QPushButton:hover { background-color: #e2e8f0; }")
        self.device_refresh_btn.clicked.connect(self.refresh_headsets)
        footer.addWidget(self.device_refresh_btn)
        layout.addLayout(footer)

        self.render_headset_list()

    def on_access_state(self, state, detail):
        """What the user has to do before a headset can be reached."""
        self.access_state = state
        self.access_detail = detail

        if state == "granted":
            self.access_banner.setVisible(False)
            self.access_retry_timer.stop()
            return

        if state == "credentials":
            self.access_title_lbl.setText(t("access.credentials_title"))
            self.access_body_lbl.setText(t("access.credentials_body"))
            self.access_action_btn.setText(t("access.enter_credentials"))
            self.access_retry_timer.stop()
        elif state == "pending":
            self.access_title_lbl.setText(t("access.pending_title"))
            self.access_body_lbl.setText(t("access.pending_body"))
            self.access_action_btn.setText(t("access.check_again"))
            self.access_retry_timer.start()
        elif state == "rejected":
            self.access_title_lbl.setText(t("access.rejected_title"))
            self.access_body_lbl.setText(t("access.rejected_body"))
            self.access_action_btn.setText(t("access.ask_again"))
            # Keep asking: the usual reason for a refusal is the wrong button in
            # the Launcher, and the user's next move is to approve it properly.
            self.access_retry_timer.start()
        elif state == "failed":
            self.access_title_lbl.setText(t("access.failed_title"))
            self.access_body_lbl.setText(t("access.failed_body", detail=detail))
            self.access_action_btn.setText(t("access.enter_credentials"))
            self.access_retry_timer.stop()

        self.access_banner.setVisible(True)
        self.page_container.setCurrentIndex(PAGE_DEVICES)

    def on_access_action(self):
        if self.access_state in ("credentials", "failed"):
            self.open_credentials_dialog()
        else:
            self.retry_access()

    def retry_access(self):
        if self.cortex_thread:
            self.cortex_thread.retry_access()

    def refresh_headsets(self):
        i18n.bind(self.device_status_lbl, "device.searching")
        if self.cortex_thread:
            self.cortex_thread.refresh_headsets()

    def on_headsets(self, headsets):
        self.headsets = headsets
        self.render_headset_list()

    def render_headset_list(self):
        while self.device_list_layout.count():
            item = self.device_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                # deleteLater() alone leaves the widget parented and painting
                # until the event loop gets round to it, which shows the
                # previous list underneath the new one.
                widget.setParent(None)
                widget.deleteLater()

        if not self.headsets:
            empty = QWidget()
            empty_layout = QVBoxLayout(empty)
            title = QLabel(t("device.none_title"))
            title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            title.setStyleSheet("color: #1e293b;")
            body = QLabel(t("device.none_body"))
            body.setWordWrap(True)
            body.setStyleSheet("color: #64748b;")
            empty_layout.addWidget(title)
            empty_layout.addWidget(body)
            empty.setStyleSheet("background-color: #f8fafc; border: 1px dashed #cbd5e1;"
                                "border-radius: 8px;")
            self.device_list_layout.addWidget(empty)
            self.device_list_layout.addStretch()
            return

        for headset in self.headsets:
            self.device_list_layout.addWidget(self.build_headset_card(headset))
        self.device_list_layout.addStretch()

    def build_headset_card(self, headset):
        headset_id = headset.get("id", "")
        info = devices.describe(headset_id)

        card = QWidget()
        card.setStyleSheet("QWidget { background-color: #f8fafc; border: 1px solid "
                           "#e2e8f0; border-radius: 8px; }")
        row = QHBoxLayout(card)
        row.setContentsMargins(16, 12, 16, 12)

        text_column = QVBoxLayout()
        text_column.setSpacing(2)

        name = QLabel(info["name"] or headset_id)
        name.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        name.setStyleSheet("color: #1e293b; border: none;")
        text_column.addWidget(name)

        ident = QLabel(headset_id)
        ident.setFont(QFont("Segoe UI", 9))
        ident.setStyleSheet("color: #94a3b8; border: none;")
        text_column.addWidget(ident)

        status_key = {
            "connected": "device.status.connected",
            "discovered": "device.status.discovered",
            "connecting": "device.status.connecting",
        }.get(headset.get("status", ""), "device.status.unknown")
        by_key = {
            "dongle": "device.by.dongle",
            "bluetooth": "device.by.bluetooth",
            "usb cable": "device.by.usb",
            "usb": "device.by.usb",
        }.get(str(headset.get("connectedBy", "")).lower())

        line = t(status_key)
        if by_key:
            line += " · " + t(by_key)
        detail = QLabel(line)
        detail.setFont(QFont("Segoe UI", 10))
        detail.setStyleSheet("color: #4f5d75; border: none;")
        text_column.addWidget(detail)

        if info["channels"]:
            channels = QLabel(t("device.channels", count=len(info["channels"]),
                                names=", ".join(info["channels"])))
        elif info["known"]:
            channels = QLabel(t("device.unknown_model"))
        else:
            channels = QLabel(t("device.unknown_model"))
        channels.setFont(QFont("Segoe UI", 9))
        channels.setWordWrap(True)
        channels.setStyleSheet("color: #94a3b8; border: none;")
        text_column.addWidget(channels)

        # The one capability difference a caregiver has to know about before
        # they start: MN8 cannot see a clench or a furrow.
        facial = QLabel(t("device.facial_yes") if info["has_facial"]
                        else t("device.facial_no"))
        facial.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        facial.setWordWrap(True)
        facial.setStyleSheet("color: %s; border: none;" %
                             ("#27ae60" if info["has_facial"] else "#d9145a"))
        text_column.addWidget(facial)

        row.addLayout(text_column, stretch=1)

        connect_btn = QPushButton(t("device.connect"))
        connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        connect_btn.setFixedSize(130, 42)
        connect_btn.setStyleSheet(
            "QPushButton { background-color: #d9145a; color: white; border-radius: 4px;"
            "font-weight: bold; } QPushButton:hover { background-color: #b00f46; }")
        connect_btn.clicked.connect(lambda _c=False, h=headset_id: self.choose_headset(h))
        row.addWidget(connect_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        return card

    def choose_headset(self, headset_id):
        self.selected_headset = headset_id
        info = devices.describe(headset_id)
        self.device_facial_supported = info["has_facial"]

        i18n.unbind(self.device_status_lbl)
        self.device_status_lbl.setText(t("device.connecting", headset=headset_id))

        # Draw the head map for this headset immediately. Cortex will confirm
        # the real channel names on subscribe and they replace these.
        self.head_map.set_channels(info["channels"])
        # The setup advice differs per headset family, so it is re-rendered for
        # the one that was just chosen.
        self.switch_setup_tab(self.current_setup_tab)
        self.apply_device_capabilities()
        self.update_hardware_banner(headset_id)
        self.quality_pill.set_device(headset_id)

        if self.cortex_thread:
            self.cortex_thread.connect_to(
                headset_id, want_facial=self.facial_selector.isChecked())

        self.page_container.setCurrentIndex(PAGE_PREFLIGHT)
        self.update_preflight_metrics()

    def apply_device_capabilities(self):
        """Reflect what this headset can do, in the places it matters."""
        supported = self.device_facial_supported
        self.facial_selector.setEnabled(supported)
        if not supported:
            self.facial_selector.setChecked(False)
            self.facial_selector.setToolTip(t("board.facial_unsupported"))
            self.facial_slider.setEnabled(False)
            self.facial_slider_lbl.setStyleSheet("color: #94a3b8; border: none;")
        else:
            self.facial_selector.setChecked(self.init_include_facial)
            self.facial_selector.setToolTip("")
            self.facial_slider.setEnabled(True)
            self.facial_slider_lbl.setStyleSheet("color: #4f5d75; border: none;")
        self.facial_note_lbl.setVisible(not supported)
        self.handle_stream_selectors_toggled()

    def on_headset_connected(self, headset_id):
        if headset_id:
            self.selected_headset = headset_id
            self.update_hardware_banner(headset_id)
            self.quality_pill.set_device(headset_id)

    def on_stream_failed(self, stream, message):
        self.display_network_logs("status.stream_refused",
                                  {"stream": stream, "detail": message})
        if stream == "fac":
            # Cortex refusing `fac` is the authoritative answer, whatever the
            # device table said.
            self.device_facial_supported = False
            self.apply_device_capabilities()

    # ── screen 2: pre-flight ─────────────────────────────────────────────
    def build_preflight_screen(self):
        self.setup_page = QWidget()
        self.setup_page.setStyleSheet("background-color: #ffffff;")
        layout = QVBoxLayout(self.setup_page)
        layout.setContentsMargins(40, 30, 40, 30)

        nav_header = QHBoxLayout()

        self.preflight_back_btn = i18n.bind(QPushButton(), "nav.back")
        self.preflight_back_btn.setFlat(True)
        self.preflight_back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.preflight_back_btn.setStyleSheet(
            "QPushButton { color: #4f5d75; font-weight: bold; padding-right: 14px; }")
        self.preflight_back_btn.clicked.connect(
            lambda: self.page_container.setCurrentIndex(PAGE_DEVICES))
        nav_header.addWidget(self.preflight_back_btn)

        self.cq_tab_btn = i18n.bind(QPushButton(), "nav.contact_quality")
        self.cq_tab_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.cq_tab_btn.setFlat(True)
        self.cq_tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cq_tab_btn.clicked.connect(lambda: self.switch_setup_tab("CQ"))
        nav_header.addWidget(self.cq_tab_btn)

        self.eq_tab_btn = i18n.bind(QPushButton(), "nav.eeg_quality")
        self.eq_tab_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        self.eq_tab_btn.setFlat(True)
        self.eq_tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.eq_tab_btn.clicked.connect(lambda: self.switch_setup_tab("EQ"))
        nav_header.addWidget(self.eq_tab_btn)

        nav_header.addStretch()
        nav_header.addLayout(self.build_language_toggle())

        self.phrases_btn = i18n.bind(QPushButton(), "nav.phrases")
        self.phrases_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.phrases_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.phrases_btn.setStyleSheet("QPushButton { background-color: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; padding: 6px 12px; border-radius: 4px; margin-left: 8px; } QPushButton:hover { background-color: #e2e8f0; }")
        self.phrases_btn.clicked.connect(self.open_phrase_manager_dialog)
        nav_header.addWidget(self.phrases_btn)

        self.config_btn = i18n.bind(QPushButton(), "nav.api_settings")
        self.config_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.config_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.config_btn.setStyleSheet("QPushButton { background-color: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; padding: 6px 12px; border-radius: 4px; } QPushButton:hover { background-color: #e2e8f0; }")
        self.config_btn.clicked.connect(self.open_credentials_dialog)
        nav_header.addWidget(self.config_btn)

        layout.addLayout(nav_header)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(40)

        left_column_layout = QVBoxLayout()

        self.device_name_label = i18n.bind(QLabel(), "setup.device_connecting")
        self.device_name_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.device_name_label.setStyleSheet("color: #4f5d75; background-color: #f8f9fa; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0; margin-bottom: 5px;")
        self.device_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.device_name_label.setFixedHeight(40)
        left_column_layout.addWidget(self.device_name_label)

        left_column_layout.addStretch()
        self.head_map = HeadsetMapWidget()
        left_column_layout.addWidget(self.head_map, alignment=Qt.AlignmentFlag.AlignCenter)

        self.two_channel_note = i18n.bind(QLabel(), "setup.two_channel_note")
        self.two_channel_note.setWordWrap(True)
        self.two_channel_note.setFont(QFont("Segoe UI", 9))
        self.two_channel_note.setStyleSheet("color: #64748b;")
        self.two_channel_note.setVisible(False)
        self.two_channel_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_column_layout.addWidget(self.two_channel_note)
        left_column_layout.addStretch()

        body_layout.addLayout(left_column_layout)

        text_layout = QVBoxLayout()
        self.instructions_title = QLabel("")
        self.instructions_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.instructions_title.setStyleSheet("color: #1a1a1a;")
        self.instructions_title.setWordWrap(True)
        text_layout.addWidget(self.instructions_title)

        self.instructions_body = QLabel("")
        self.instructions_body.setFont(QFont("Segoe UI", 11))
        self.instructions_body.setWordWrap(True)
        self.instructions_body.setStyleSheet("color: #4a5568; line-height: 150%;")
        text_layout.addWidget(self.instructions_body)
        text_layout.addStretch()

        self.completion_percentage_label = QLabel("0%")
        self.completion_percentage_label.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        self.completion_percentage_label.setStyleSheet("color: #cbd5e1;")
        text_layout.addWidget(self.completion_percentage_label)

        self.completion_hint_label = QLabel("")
        self.completion_hint_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.completion_hint_label.setStyleSheet("color: #64748b;")
        self.completion_hint_label.setWordWrap(True)
        text_layout.addWidget(self.completion_hint_label)

        body_layout.addLayout(text_layout)
        layout.addLayout(body_layout, stretch=1)

        footer_layout = QHBoxLayout()
        self.setup_network_log = QLabel("BCI: " + t("status.waiting"))
        self.setup_network_log.setFont(QFont("Segoe UI", 10))
        footer_layout.addWidget(self.setup_network_log)
        footer_layout.addStretch()

        self.continue_btn = i18n.bind(QPushButton(), "setup.continue")
        self.continue_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.continue_btn.setFixedSize(160, 42)
        self.continue_btn.setEnabled(False)
        self.continue_btn.setStyleSheet("""
            QPushButton:enabled { background-color: #d9145a; color: white; border-radius: 4px; }
            QPushButton:disabled { background-color: #e2e8f0; color: #94a3b8; border-radius: 4px; }
        """)
        self.continue_btn.clicked.connect(self.transition_to_keyboard)
        footer_layout.addWidget(self.continue_btn)
        layout.addLayout(footer_layout)

        self.switch_setup_tab("CQ")

    # ── screen 3: the board ──────────────────────────────────────────────
    def build_keyboard_screen(self):
        self.keyboard_page = QWidget()
        self.keyboard_page.setStyleSheet("background-color: #f8fafc;")
        self.main_layout = QVBoxLayout(self.keyboard_page)

        self.boards = {"ALPHA": BOARD_2_ALPHA, "PHRASES": BOARD_1_PHRASES}
        self.current_board_name = "ALPHA"
        self.current_matrix = self.boards[self.current_board_name]

        self.SCAN_ROWS = 0
        self.SCAN_COLS = 1
        self.scanning_state = self.SCAN_ROWS

        self.active_row = 0
        self.active_col = 0

        self.scan_intervals = [2000, 1500, 1000, 600]
        self.speed_keys = ["speed.slow", "speed.medium", "speed.fast", "speed.very_fast"]
        self.speed_index = 1
        self.composed_text = ""

        # --- THRESHOLDS, COOLDOWN, & PAUSE STATES ---
        self.MENTAL_THRESHOLD = 0.35
        self.FACIAL_THRESHOLD = 0.70
        self.SELECTION_COOLDOWN_MS = 2500

        # --- UNIFIED 0.5-SECOND SUSTAINED HOLD TIMERS ---
        self.HOLD_DURATION_SEC = 0.5
        self.mental_hold_start = None
        self.mental_active_cmd = None
        self.facial_hold_start = None
        self.facial_active_act = None

        self.latch_released = True
        self.facial_latch_released = True
        self.in_cooldown = False
        self.is_paused = False

        self.cooldown_remaining_ms = 0
        self.cooldown_phase_key = ""

        # The live state is held as (key, params), never as rendered text:
        # switching language has to re-say what is happening right now, not
        # leave an English sentence frozen inside a Chinese banner.
        self.mental_state = ("telemetry.neutral", {"power": "0.00"})
        self.facial_state = ("telemetry.facial_ready", {})
        self.board_status = ("status.scanner_active", {})

        # Message & Quick Action Control Bay
        message_bar_layout = QHBoxLayout()

        self.display_box = QLabel(t("board.composed", text=""))
        self.display_box.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.display_box.setStyleSheet("background-color: #1e1e24; color: #2ecc71; padding: 15px; border-radius: 8px; border: 2px solid #111115;")
        self.display_box.setWordWrap(True)
        message_bar_layout.addWidget(self.display_box, stretch=1)

        action_btn_layout = QVBoxLayout()
        action_btn_layout.setSpacing(6)

        self.speak_btn = i18n.bind(QPushButton(), "board.speak")
        self.speak_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.speak_btn.setFixedSize(150, 36)
        self.speak_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.speak_btn.setStyleSheet("QPushButton { background-color: #d9145a; color: white; border-radius: 6px; } QPushButton:hover { background-color: #b00f46; }")
        self.speak_btn.clicked.connect(self.speak_message)
        action_btn_layout.addWidget(self.speak_btn)

        self.backspace_btn = i18n.bind(QPushButton(), "board.backspace")
        self.backspace_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.backspace_btn.setFixedSize(150, 30)
        self.backspace_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.backspace_btn.setStyleSheet("QPushButton { background-color: #4f5d75; color: white; border-radius: 6px; } QPushButton:hover { background-color: #3b4758; }")
        self.backspace_btn.clicked.connect(lambda: self.process_selection("BACKSPACE"))
        action_btn_layout.addWidget(self.backspace_btn)

        self.pause_btn = i18n.bind(QPushButton(), "board.pause")
        self.pause_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.pause_btn.setFixedSize(150, 30)
        self.pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_btn.setStyleSheet("QPushButton { background-color: #f39c12; color: white; border-radius: 6px; } QPushButton:hover { background-color: #d35400; }")
        self.pause_btn.clicked.connect(lambda: self.process_selection("PAUSE SCANNER"))
        action_btn_layout.addWidget(self.pause_btn)

        self.exit_app_btn = i18n.bind(QPushButton(), "board.exit")
        self.exit_app_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.exit_app_btn.setFixedSize(150, 30)
        self.exit_app_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.exit_app_btn.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; border-radius: 6px; } QPushButton:hover { background-color: #c0392b; }")
        self.exit_app_btn.clicked.connect(self.close)
        action_btn_layout.addWidget(self.exit_app_btn)

        message_bar_layout.addLayout(action_btn_layout)
        self.main_layout.addLayout(message_bar_layout)

        # Dynamic Unified Telemetry & State Tracker Box
        self.telemetry_label = QLabel()
        self.telemetry_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.main_layout.addWidget(self.telemetry_label)

        # Live headset quality, so a drifting sensor is visible without leaving
        # the board.
        quality_row = QHBoxLayout()
        self.quality_pill = QualityPill()
        quality_row.addWidget(self.quality_pill)

        self.quality_warning_lbl = QLabel("")
        self.quality_warning_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.quality_warning_lbl.setStyleSheet("color: #d9145a;")
        self.quality_warning_lbl.setVisible(False)
        quality_row.addWidget(self.quality_warning_lbl)
        quality_row.addStretch()
        self.main_layout.addLayout(quality_row)

        # Tuning Bar
        tuning_panel = QWidget()
        tuning_panel.setStyleSheet("background-color: #ffffff; border-radius: 6px; border: 1px solid #e2e8f0;")
        tuning_layout = QHBoxLayout(tuning_panel)
        tuning_layout.setContentsMargins(15, 6, 15, 6)

        self.mental_slider_lbl = QLabel(t("board.mental_sens", value=f"{self.MENTAL_THRESHOLD:.2f}"))
        self.mental_slider_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.mental_slider_lbl.setStyleSheet("color: #4f5d75; border: none;")
        tuning_layout.addWidget(self.mental_slider_lbl)

        self.mental_slider = QSlider(Qt.Orientation.Horizontal)
        self.mental_slider.setRange(5, 95)
        self.mental_slider.setValue(int(self.MENTAL_THRESHOLD * 100))
        self.mental_slider.setFixedWidth(110)
        self.mental_slider.setStyleSheet("QSlider::handle:horizontal { background-color: #d9145a; border-radius: 5px; }")
        self.mental_slider.valueChanged.connect(self.handle_mental_slider_changed)
        tuning_layout.addWidget(self.mental_slider)

        tuning_layout.addSpacing(20)

        self.facial_slider_lbl = QLabel(t("board.facial_sens", value=f"{self.FACIAL_THRESHOLD:.2f}"))
        self.facial_slider_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.facial_slider_lbl.setStyleSheet("color: #4f5d75; border: none;")
        tuning_layout.addWidget(self.facial_slider_lbl)

        self.facial_slider = QSlider(Qt.Orientation.Horizontal)
        self.facial_slider.setRange(5, 95)
        self.facial_slider.setValue(int(self.FACIAL_THRESHOLD * 100))
        self.facial_slider.setFixedWidth(110)
        self.facial_slider.setStyleSheet("QSlider::handle:horizontal { background-color: #d9145a; border-radius: 5px; }")
        self.facial_slider.valueChanged.connect(self.handle_facial_slider_changed)
        tuning_layout.addWidget(self.facial_slider)

        tuning_layout.addSpacing(20)

        self.cooldown_slider_lbl = QLabel(t("board.cooldown", value=f"{self.SELECTION_COOLDOWN_MS/1000:.1f}"))
        self.cooldown_slider_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.cooldown_slider_lbl.setStyleSheet("color: #4f5d75; border: none;")
        tuning_layout.addWidget(self.cooldown_slider_lbl)

        self.cooldown_slider = QSlider(Qt.Orientation.Horizontal)
        self.cooldown_slider.setRange(5, 50)
        self.cooldown_slider.setValue(int(self.SELECTION_COOLDOWN_MS / 100))
        self.cooldown_slider.setFixedWidth(110)
        self.cooldown_slider.setStyleSheet("QSlider::handle:horizontal { background-color: #d9145a; border-radius: 5px; }")
        self.cooldown_slider.valueChanged.connect(self.handle_cooldown_slider_changed)
        tuning_layout.addWidget(self.cooldown_slider)

        tuning_layout.addStretch()

        self.facial_note_lbl = i18n.bind(QLabel(), "board.facial_unsupported")
        self.facial_note_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.facial_note_lbl.setStyleSheet("color: #d9145a; border: none;")
        self.facial_note_lbl.setVisible(False)
        tuning_layout.addWidget(self.facial_note_lbl)

        self.main_layout.addWidget(tuning_panel)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.main_layout.addWidget(self.grid_container, stretch=1)

        self.build_board_grid()

        status_layout = QHBoxLayout()
        self.status_label = i18n.bind(QLabel(), "board.mode")
        self.status_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: #1e293b; padding-right: 10px;")
        status_layout.addWidget(self.status_label)

        speed_title = i18n.bind(QLabel(), "board.speed")
        speed_title.setFont(QFont("Segoe UI", 11))
        status_layout.addWidget(speed_title)

        self.speed_widgets = []
        for key in self.speed_keys:
            lbl = i18n.bind(QLabel(), key)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            lbl.setFixedSize(85, 22)
            status_layout.addWidget(lbl)
            self.speed_widgets.append(lbl)

        status_layout.addStretch()

        self.mental_selector = i18n.bind(QCheckBox(), "board.include_mental")
        self.mental_selector.setChecked(self.init_include_mental)
        self.mental_selector.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.mental_selector.setStyleSheet("QCheckBox { color: #334155; spacing: 4px; padding-right: 10px; }")
        self.mental_selector.toggled.connect(self.handle_stream_selectors_toggled)
        status_layout.addWidget(self.mental_selector)

        self.facial_selector = i18n.bind(QCheckBox(), "board.include_facial")
        self.facial_selector.setChecked(self.init_include_facial)
        self.facial_selector.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.facial_selector.setStyleSheet("QCheckBox { color: #334155; spacing: 4px; padding-right: 15px; }")
        self.facial_selector.toggled.connect(self.handle_stream_selectors_toggled)
        status_layout.addWidget(self.facial_selector)

        self.keyboard_network_status_label = QLabel()
        self.keyboard_network_status_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        status_layout.addWidget(self.keyboard_network_status_label)
        self.set_board_status("status.scanner_active", "#2ecc71")

        self.controls_label = QLabel("")
        self.controls_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.controls_label.setStyleSheet("color: #4f5d75; padding: 5px;")
        status_layout.addWidget(self.controls_label)
        self.main_layout.addLayout(status_layout)

        self.handle_stream_selectors_toggled()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance_scanner)

        self.cooldown_ticker = QTimer(self)
        self.cooldown_ticker.timeout.connect(self.tick_cooldown_countdown)

        self.update_telemetry_box("neutral")
        self.update_status_bar()

    # ── live device state ────────────────────────────────────────────────
    def update_device_diagnostics(self, battery_pct, signal_pct):
        self.battery_percent = battery_pct
        self.quality_pill.set_battery(battery_pct)

    def refresh_quality_pill(self):
        self.quality_pill.set_device(self.selected_headset)
        self.quality_pill.set_contact(self.contact_percent)
        self.quality_pill.set_eeg(self.eeg_percent)
        self.quality_pill.set_battery(self.battery_percent)

    def handle_mental_slider_changed(self, value):
        self.MENTAL_THRESHOLD = value / 100.0
        self.mental_slider_lbl.setText(
            t("board.mental_sens", value=f"{self.MENTAL_THRESHOLD:.2f}"))
        self.update_telemetry_box("neutral")

    def handle_facial_slider_changed(self, value):
        self.FACIAL_THRESHOLD = value / 100.0
        self.facial_slider_lbl.setText(
            t("board.facial_sens", value=f"{self.FACIAL_THRESHOLD:.2f}"))
        self.update_telemetry_box("neutral")

    def handle_cooldown_slider_changed(self, value):
        self.SELECTION_COOLDOWN_MS = value * 100
        self.cooldown_slider_lbl.setText(
            t("board.cooldown", value=f"{self.SELECTION_COOLDOWN_MS/1000:.1f}"))

    def update_telemetry_box(self, style_preset="neutral"):
        if self.in_cooldown:
            return

        if self.mental_selector.isChecked():
            mental_part = t(self.mental_state[0], **self.mental_state[1])
        else:
            mental_part = t("telemetry.disabled")

        if not self.device_facial_supported:
            facial_part = t("telemetry.unsupported")
        elif self.facial_selector.isChecked():
            facial_part = t(self.facial_state[0], **self.facial_state[1])
        else:
            facial_part = t("telemetry.disabled")

        self.telemetry_label.setText(
            t("telemetry.line", mental=mental_part, facial=facial_part))

        if style_preset == "neutral":
            self.telemetry_label.setStyleSheet("background-color: #1e1e24; color: #edf2f4; padding: 10px; border-radius: 6px; margin-top: 5px; border: 1px solid #334155;")
        elif style_preset == "warning":
            self.telemetry_label.setStyleSheet("background-color: #f39c12; color: #ffffff; padding: 10px; border-radius: 6px; margin-top: 5px; border: 1px solid #d35400;")
        elif style_preset == "locked":
            self.telemetry_label.setStyleSheet("background-color: #334155; color: #cbd5e1; padding: 10px; border-radius: 6px; margin-top: 5px; border: 1px solid #475569;")
        elif style_preset == "mental_trigger":
            self.telemetry_label.setStyleSheet("background-color: #d9145a; color: #ffffff; padding: 10px; border-radius: 6px; margin-top: 5px; border: 1px solid #b00f46;")
        elif style_preset == "facial_trigger":
            self.telemetry_label.setStyleSheet("background-color: #4f5d75; color: #ffffff; padding: 10px; border-radius: 6px; margin-top: 5px; border: 1px solid #2b2d42;")

    def set_board_status(self, key, colour, **params):
        """The line under the board, kept as a key so it can be re-said."""
        self.board_status = (key, params)
        self.keyboard_network_status_label.setText("BCI: " + t(key, **params))
        self.keyboard_network_status_label.setStyleSheet(
            f"color: {colour}; font-weight: bold;")

    def handle_stream_selectors_toggled(self):
        m_on = self.mental_selector.isChecked()
        f_on = self.facial_selector.isChecked() and self.device_facial_supported

        params = {
            "select_thought": self.select_thought.capitalize(),
            "select_facial": self.select_facial.capitalize(),
            "speed_thought": self.speed_thought.capitalize(),
            "speed_facial": self.speed_facial.capitalize(),
        }

        if m_on and f_on:
            self.controls_label.setText(t("controls.both", **params))
        elif m_on:
            self.controls_label.setText(t("controls.mental", **params))
        elif f_on:
            self.controls_label.setText(t("controls.facial", **params))
        else:
            self.controls_label.setText(t("controls.none"))

        save_config({
            "include_mental_commands": m_on,
            "include_facial_expressions": self.facial_selector.isChecked(),
        })

        self.update_telemetry_box("neutral")

    def build_board_grid(self):
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            widget = child.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        self.grid_widgets = []
        for r in range(len(self.current_matrix)):
            row_widgets = []
            for c in range(len(self.current_matrix[r])):
                token = self.current_matrix[r][c]
                # The cell carries the token; the label is only what it looks
                # like in the language currently selected.
                label = QLabel(i18n.cell(token) if token else "")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
                label.setWordWrap(True)
                label.setStyleSheet("border: 1px solid #e2e8f0; background-color: #ffffff; border-radius: 6px; padding: 5px; color: #1e293b;")
                self.grid_layout.addWidget(label, r, c)
                row_widgets.append(label)
            self.grid_widgets.append(row_widgets)

    def switch_setup_tab(self, mode):
        self.current_setup_tab = mode
        self.head_map.display_mode = mode
        self.head_map.update()

        if mode == "CQ":
            self.cq_tab_btn.setStyleSheet("background: transparent; color: #d9145a; border-bottom: 3px solid #d9145a; padding-bottom: 3px; font-weight: bold;")
            self.eq_tab_btn.setStyleSheet("background: transparent; color: #94a3b8; border-bottom: 3px solid transparent; padding-bottom: 3px; font-weight: normal;")
            self.instructions_title.setText(t("setup.cq_title"))
            self.instructions_body.setText(self.contact_guidance())
        else:
            self.eq_tab_btn.setStyleSheet("background: transparent; color: #d9145a; border-bottom: 3px solid #d9145a; padding-bottom: 3px; font-weight: bold;")
            self.cq_tab_btn.setStyleSheet("background: transparent; color: #94a3b8; border-bottom: 3px solid transparent; padding-bottom: 3px; font-weight: normal;")
            self.instructions_title.setText(t("setup.eq_title"))
            self.instructions_body.setText(t("setup.eq_body"))
        self.update_preflight_metrics()

    def contact_guidance(self) -> str:
        """The advice that matches the headset actually in use.

        Insight's reference sensors are two cones behind the left ear, EPOC's
        are felt pads that need saline, and MN8's sensors are in the earpieces.
        Printing one of those three sets of instructions for all of them is how
        a caregiver ends up looking for a part their headset does not have.
        """
        prefix = devices.describe(self.selected_headset)["prefix"]
        family = {
            "INSIGHT": "insight", "INSIGHT2": "insight",
            "EPOC": "epoc", "EPOCPLUS": "epoc", "EPOCX": "epoc",
            "EPOCFLEX": "epoc", "FLEX": "epoc", "FLEX2": "epoc",
            "MN8": "mn8",
        }.get(prefix)
        if not family:
            return t("setup.cq_body")
        return t("setup.cq_body." + family)

    def process_contact_quality(self, cq_map):
        self.head_map.update_quality("CQ", cq_map)
        self.contact_percent = devices.quality_percent(self.head_map.cq_status.values())
        self.quality_pill.set_contact(self.contact_percent)
        self.update_quality_warning()
        self.update_preflight_metrics()

    def process_eeg_quality(self, eq_map):
        self.head_map.update_quality("EQ", eq_map)
        self.eeg_percent = devices.quality_percent(self.head_map.eq_status.values())
        self.quality_pill.set_eeg(self.eeg_percent)
        self.update_preflight_metrics()

    def update_quality_warning(self):
        """Name the sensors that went bad, while the board is in use.

        Saying "contact 60%" during a session is not actionable; saying which
        electrode to push back down is.
        """
        weak = devices.weak_sensors(self.head_map.cq_status)
        if weak and self.page_container.currentIndex() == PAGE_BOARD:
            self.quality_warning_lbl.setText(t("pill.warning", names=", ".join(weak)))
            self.quality_warning_lbl.setVisible(True)
        else:
            self.quality_warning_lbl.setVisible(False)

    def update_preflight_metrics(self):
        cq_pct = devices.quality_percent(self.head_map.cq_status.values())
        eq_pct = devices.quality_percent(self.head_map.eq_status.values())
        total = len(self.head_map.cq_status) or 0

        self.two_channel_note.setVisible(0 < total <= 2)

        shown = cq_pct if self.current_setup_tab == "CQ" else eq_pct
        self.completion_percentage_label.setText(f"{shown}%")

        missing = len(devices.weak_sensors(self.head_map.cq_status))

        # Continue is never blocked. A perfect fit is what you want, but a
        # caregiver may need the board with a sensor that will not sit, or
        # before any reading has arrived at all, and refusing to open it does
        # not improve the signal — it just leaves the person without a voice.
        self.continue_btn.setEnabled(True)

        if total and cq_pct == 100 and eq_pct == 100:
            self.completion_percentage_label.setStyleSheet("color: #2ecc71;")
            self.completion_hint_label.setText(t("setup.ready"))
            self.completion_hint_label.setStyleSheet("color: #27ae60;")
        elif not total:
            self.completion_percentage_label.setStyleSheet("color: #cbd5e1;")
            self.completion_hint_label.setText(t("setup.no_data"))
            self.completion_hint_label.setStyleSheet("color: #64748b;")
        else:
            self.completion_percentage_label.setStyleSheet("color: #cbd5e1;")
            waiting = (t("setup.waiting_one") if missing == 1
                       else t("setup.waiting_many", count=missing))
            self.completion_hint_label.setText(
                waiting + " " + t("setup.continue_anyway"))
            self.completion_hint_label.setStyleSheet("color: #64748b;")

    def update_hardware_banner(self, device_id):
        i18n.unbind(self.device_name_label)
        self.device_name_label.setText(t("setup.device", headset=device_id.upper()))
        self.device_name_label.setStyleSheet("color: #2ecc71; background-color: #f8f9fa; padding: 8px; border-radius: 6px; border: 1px solid #2ecc71; font-weight: bold;")

    def transition_to_keyboard(self):
        self.page_container.setCurrentIndex(PAGE_BOARD)
        self.timer.start(self.scan_intervals[self.speed_index])
        self.update_ui_highlights()
        self.update_status_bar()
        self.refresh_quality_pill()

    def display_network_logs(self, code, params=None):
        text = t(code, **(params or {}))
        self.setup_network_log.setText(f"BCI: {text}")
        if code in ("status.live", "status.linked"):
            self.setup_network_log.setStyleSheet("color: #27ae60; font-weight: bold;")
        elif code in ("status.failed", "status.no_cortex_file", "status.config_error",
                      "status.stream_refused"):
            self.setup_network_log.setStyleSheet("color: #d9145a; font-weight: bold;")
        else:
            self.setup_network_log.setStyleSheet("color: #f39c12; font-weight: bold;")

        if code == "status.live" and self.device_status_lbl:
            i18n.unbind(self.device_status_lbl)
            self.device_status_lbl.setText(text)

    def route_bci_command(self, command, power):
        if self.page_container.currentIndex() != PAGE_BOARD or self.in_cooldown or self.is_paused:
            self.mental_hold_start = None
            self.mental_active_cmd = None
            return

        if not self.mental_selector.isChecked():
            self.mental_hold_start = None
            self.mental_active_cmd = None
            return

        clean_command = command.strip().lower()

        if clean_command == "neutral":
            self.mental_hold_start = None
            self.mental_active_cmd = None
            self.mental_state = ("telemetry.neutral", {"power": f"{power:.2f}"})
            self.update_telemetry_box("neutral")
            self.latch_released = True
            return

        is_select_cmd = (clean_command == self.select_thought.lower())
        is_speed_cmd = (clean_command == self.speed_thought.lower())

        if not is_select_cmd and not is_speed_cmd:
            self.mental_hold_start = None
            self.mental_active_cmd = None
            return

        mapped_action = t("action.select") if is_select_cmd else t("action.speed")

        if power < self.MENTAL_THRESHOLD:
            self.mental_hold_start = None
            self.mental_active_cmd = None
            self.mental_state = ("telemetry.below",
                                 {"command": clean_command.upper(),
                                  "action": mapped_action, "power": f"{power:.2f}"})
            self.update_telemetry_box("warning")
            self.latch_released = True
            return

        if not self.latch_released:
            self.mental_hold_start = None
            self.mental_active_cmd = None
            self.mental_state = ("telemetry.locked",
                                 {"command": clean_command.upper(),
                                  "action": mapped_action, "power": f"{power:.2f}"})
            self.update_telemetry_box("locked")
            return

        # --- 0.5-SECOND SUSTAINED HOLD LOGIC FOR MENTAL COMMANDS ---
        if self.mental_hold_start is None or self.mental_active_cmd != clean_command:
            self.mental_hold_start = time.time()
            self.mental_active_cmd = clean_command

        elapsed = time.time() - self.mental_hold_start

        if elapsed < self.HOLD_DURATION_SEC:
            self.mental_state = ("telemetry.holding",
                                 {"command": clean_command.upper(),
                                  "action": mapped_action, "elapsed": f"{elapsed:.1f}",
                                  "needed": f"{self.HOLD_DURATION_SEC:.1f}"})
            self.update_telemetry_box("warning")
        else:
            self.mental_state = ("telemetry.triggered",
                                 {"command": clean_command.upper(),
                                  "power": f"{power:.2f}"})
            self.update_telemetry_box("mental_trigger")
            self.latch_released = False
            self.mental_hold_start = None
            self.mental_active_cmd = None

            if is_select_cmd:
                self.trigger_select_event()
            elif is_speed_cmd:
                self.trigger_speed_change()

    def route_facial_command(self, u_act, u_pow, l_act, l_pow):
        if self.page_container.currentIndex() != PAGE_BOARD or self.in_cooldown or self.is_paused:
            self.facial_hold_start = None
            self.facial_active_act = None
            return

        if not self.facial_selector.isChecked() or not self.device_facial_supported:
            self.facial_hold_start = None
            self.facial_active_act = None
            return

        u_act_clean = u_act.strip().lower()
        l_act_clean = l_act.strip().lower()

        if u_act_clean == "frown": u_act_clean = "furrow"

        target_sel_fac = self.select_facial.lower()
        target_spd_fac = self.speed_facial.lower()

        select_active = (
            (l_act_clean == target_sel_fac and l_pow >= self.FACIAL_THRESHOLD) or
            (u_act_clean == target_sel_fac and u_pow >= self.FACIAL_THRESHOLD)
        )

        speed_active = (
            (l_act_clean == target_spd_fac and l_pow >= self.FACIAL_THRESHOLD) or
            (u_act_clean == target_spd_fac and u_pow >= self.FACIAL_THRESHOLD)
        )

        if not select_active and not speed_active:
            self.facial_hold_start = None
            self.facial_active_act = None
            self.facial_latch_released = True
            if self.facial_state[0] != "telemetry.facial_ready":
                self.facial_state = ("telemetry.facial_ready", {})
                self.update_telemetry_box("neutral")
            return

        if not self.facial_latch_released:
            self.facial_hold_start = None
            self.facial_active_act = None
            return

        active_target = target_sel_fac if select_active else target_spd_fac
        is_select = select_active

        # --- 0.5-SECOND SUSTAINED HOLD LOGIC FOR FACIAL EXPRESSIONS ---
        if self.facial_hold_start is None or self.facial_active_act != active_target:
            self.facial_hold_start = time.time()
            self.facial_active_act = active_target

        elapsed = time.time() - self.facial_hold_start
        act_name = active_target.upper()
        action_label = t("action.select") if is_select else t("action.speed_short")

        if elapsed < self.HOLD_DURATION_SEC:
            self.facial_state = ("telemetry.holding",
                                 {"command": act_name, "action": action_label,
                                  "elapsed": f"{elapsed:.1f}",
                                  "needed": f"{self.HOLD_DURATION_SEC:.1f}"})
            self.update_telemetry_box("warning")
        else:
            pow_val = l_pow if (l_act_clean == active_target) else u_pow
            self.facial_state = ("telemetry.triggered_facial",
                                 {"command": act_name, "action": action_label,
                                  "power": f"{pow_val:.2f}"})
            self.update_telemetry_box("facial_trigger")
            self.facial_latch_released = False
            self.facial_hold_start = None
            self.facial_active_act = None

            if is_select:
                self.trigger_select_event()
            else:
                self.trigger_speed_change()

    def advance_scanner(self):
        if self.is_paused: return
        if self.scanning_state == self.SCAN_ROWS:
            self.active_row = (self.active_row + 1) % len(self.current_matrix)
        elif self.scanning_state == self.SCAN_COLS:
            self.active_col = (self.active_col + 1) % len(self.current_matrix[self.active_row])
        self.update_ui_highlights()

    def update_ui_highlights(self):
        for r in range(len(self.grid_widgets)):
            for c in range(len(self.grid_widgets[r])):
                widget = self.grid_widgets[r][c]
                if not widget: continue

                # Read the TOKEN from the matrix, never the visible label: the
                # label changes with the language, the token never does.
                token = self.current_matrix[r][c]
                is_flip_button = (token == "FLIP OVER")
                is_starter_col = (self.current_board_name == "PHRASES" and c == 0)
                is_special_action = (token in ["BACKSPACE", "SPEAK", "PAUSE SCANNER", "CLEAR MESSAGE"])

                base_style = "border: 1px solid #e2e8f0; background-color: #ffffff; color: #1e293b; border-radius: 6px; padding: 5px;"
                if is_starter_col:
                    base_style = "border: 1px dashed #4f5d75; background-color: #f1f5f9; color: #4f5d75; font-weight: bold; border-radius: 6px; padding: 5px;"
                elif is_special_action:
                    base_style = "border: 1px solid #cbd5e1; background-color: #f1f5f9; color: #0f172a; font-weight: bold; border-radius: 6px; padding: 5px;"
                elif is_flip_button:
                    base_style = "border: 1px solid #cbd5e1; background-color: #f8fafc; color: #d9145a; font-weight: bold; border-radius: 6px; padding: 5px;"

                if self.scanning_state == self.SCAN_ROWS:
                    if r == self.active_row:
                        widget.setStyleSheet("border: 2px solid #d9145a; background-color: #fdf2f8; color: #1e1e24; border-radius: 6px; padding: 5px;")
                    else:
                        widget.setStyleSheet(base_style)

                elif self.scanning_state == self.SCAN_COLS:
                    if r == self.active_row and c == self.active_col:
                        widget.setStyleSheet("border: 2px solid #b00f46; background-color: #d9145a; color: #ffffff; font-weight: bold; border-radius: 6px; padding: 5px;")
                    elif r == self.active_row:
                        widget.setStyleSheet("border: 1px solid #d9145a; background-color: #fff1f2; color: #64748b; border-radius: 6px; padding: 5px;")
                    else:
                        widget.setStyleSheet("border: 1px solid #f1f5f9; background-color: #ffffff; color: #cbd5e1; border-radius: 6px; padding: 5px;")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            if self.page_container.currentIndex() == PAGE_PREFLIGHT:
                # Keyboard override for setting up without a headset on.
                channels = self.head_map.channels or devices.INSIGHT_CHANNELS
                self.head_map.set_channels(channels)
                self.process_contact_quality({c: 4 for c in channels})
                self.process_eeg_quality({c: 4 for c in channels})
            elif self.page_container.currentIndex() == PAGE_BOARD:
                if not self.in_cooldown and not self.is_paused:
                    self.trigger_select_event()
        elif event.key() == Qt.Key.Key_S and self.page_container.currentIndex() == PAGE_BOARD:
            if not self.in_cooldown and not self.is_paused:
                self.trigger_speed_change()
        elif event.key() == Qt.Key.Key_P and self.page_container.currentIndex() == PAGE_BOARD:
            self.process_selection("PAUSE SCANNER")

    def trigger_select_event(self):
        if self.scanning_state == self.SCAN_ROWS:
            self.scanning_state = self.SCAN_COLS
            self.active_col = 0
            self.update_ui_highlights()
            self.start_cooldown_phase("phase.row_locked")

        elif self.scanning_state == self.SCAN_COLS:
            selected_token = self.current_matrix[self.active_row][self.active_col]
            self.process_selection(selected_token)

            self.scanning_state = self.SCAN_ROWS
            self.active_row = 0
            self.update_ui_highlights()
            self.start_cooldown_phase("phase.selection_complete")

    def start_cooldown_phase(self, phase_key):
        self.in_cooldown = True
        self.timer.stop()
        self.cooldown_phase_key = phase_key
        self.cooldown_remaining_ms = self.SELECTION_COOLDOWN_MS

        self.render_cooldown_in_state_tracker()
        self.cooldown_ticker.start(100)

    def tick_cooldown_countdown(self):
        self.cooldown_remaining_ms -= 100
        if self.cooldown_remaining_ms <= 0:
            self.cooldown_ticker.stop()
            self.end_selection_cooldown()
        else:
            self.render_cooldown_in_state_tracker()

    def render_cooldown_in_state_tracker(self):
        sec_str = f"{self.cooldown_remaining_ms/1000:.1f}"
        self.telemetry_label.setText(t("telemetry.cooldown",
                                       phase=t(self.cooldown_phase_key),
                                       seconds=sec_str))
        self.telemetry_label.setStyleSheet("background-color: #d9145a; color: #ffffff; padding: 10px; border-radius: 6px; margin-top: 5px; border: 1px solid #b00f46; font-size: 12px; font-weight: bold;")

        self.set_board_status("status.cooldown", "#d9145a", seconds=sec_str)

    def end_selection_cooldown(self):
        self.in_cooldown = False
        self.latch_released = True
        self.facial_latch_released = True
        self.mental_hold_start = None
        self.mental_active_cmd = None
        self.facial_hold_start = None
        self.facial_active_act = None

        if not self.is_paused:
            self.set_board_status("status.scanner_active", "#2ecc71")
            self.timer.start(self.scan_intervals[self.speed_index])
            self.update_telemetry_box("neutral")

        self.update_ui_highlights()

    def trigger_speed_change(self):
        self.speed_index = (self.speed_index + 1) % len(self.scan_intervals)
        self.timer.setInterval(self.scan_intervals[self.speed_index])
        self.update_status_bar()

    def update_status_bar(self):
        for i, lbl in enumerate(self.speed_widgets):
            if i == self.speed_index:
                lbl.setStyleSheet("background-color: #d9145a; color: #ffffff; border-radius: 4px; font-weight: bold;")
            else:
                lbl.setStyleSheet("background-color: #e2e8f0; color: #475569; border-radius: 4px;")

    def speak_message(self):
        """Triggers asynchronous offline TTS speech for the composed text."""
        text_to_speak = self.composed_text.strip()
        if text_to_speak:
            self.tts_worker = TTSThread(text_to_speak, language=i18n.language())
            self.tts_worker.start()

    def process_selection(self, token):
        if not token or token.strip() == "": return

        if token == "FLIP OVER":
            self.current_board_name = "PHRASES" if self.current_board_name == "ALPHA" else "ALPHA"
            self.current_matrix = self.boards[self.current_board_name]
            self.build_board_grid()
            self.update_ui_highlights()
            self.update_status_bar()
            return

        elif token == "SPEAK":
            self.speak_message()
            return

        elif token == "BACKSPACE":
            if self.composed_text:
                self.composed_text = self.composed_text[:-1]
            self.display_box.setText(t("board.composed", text=self.composed_text))
            return

        elif token == "PAUSE SCANNER":
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.timer.stop()
                i18n.bind(self.pause_btn, "board.resume")
                self.pause_btn.setStyleSheet("QPushButton { background-color: #2ecc71; color: white; border-radius: 6px; }")
                self.set_board_status("status.scanner_paused", "#f39c12")
                self.mental_state = ("telemetry.paused", {})
                self.facial_state = ("telemetry.paused", {})
                self.update_telemetry_box("locked")
            else:
                i18n.bind(self.pause_btn, "board.pause")
                self.pause_btn.setStyleSheet("QPushButton { background-color: #f39c12; color: white; border-radius: 6px; }")
                self.set_board_status("status.scanner_active", "#2ecc71")
                self.mental_state = ("telemetry.neutral", {"power": "0.00"})
                self.facial_state = ("telemetry.facial_ready", {})
                self.update_telemetry_box("neutral")
                self.timer.start(self.scan_intervals[self.speed_index])
            return

        elif token == "SPACE":
            self.composed_text += " "
        elif token == "CLEAR MESSAGE":
            self.composed_text = ""
        elif token in ["WAIT", "PLEASE GUESS"]:
            self.composed_text += f" [{i18n.cell(token)}] "
        else:
            # What gets spoken is the label, not the token, so a Chinese board
            # composes a Chinese sentence.
            label = i18n.cell(token)
            if len(token) == 1 or token == "QU":
                self.composed_text += label
            else:
                if self.composed_text and not self.composed_text.endswith(" "):
                    self.composed_text += " "
                self.composed_text += label + " "

        self.display_box.setText(t("board.composed", text=self.composed_text))

def apply_app_icon(app):
    """Put the app's own mark on the window, the Dock and the taskbar.

    The executable carries an icon of its own, which is what Explorer and the
    Start menu read, but Qt draws the title bar and the macOS Dock from
    setWindowIcon and would otherwise show a default.
    """
    if os.name == "nt":
        # Windows groups taskbar buttons by Application User Model ID, and a
        # process that does not set one inherits the host interpreter's. Without
        # this, a source run shows Python's icon no matter what Qt is told.
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "com.emotiv.scanningboard")
        except Exception:
            # Cosmetic only, and shell32 is not worth failing a launch over.
            pass

    icon = window_icon_path()
    if icon:
        app.setWindowIcon(QIcon(icon))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_app_icon(app)
    window = BCICommunicationBoard()
    window.showMaximized()
    sys.exit(app.exec())
