import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QDialog,
    QFormLayout, QLineEdit, QDialogButtonBox, QMessageBox, QListWidget, QHBoxLayout, QGroupBox, QSpacerItem, QSizePolicy, QInputDialog, QProgressBar, QCheckBox
)
from PyQt5.QtGui import QFont, QIntValidator
from PyQt5.QtCore import Qt, QTimer, QAbstractNativeEventFilter, QAbstractEventDispatcher
from PyQt5.QtCore import QObject, QEvent
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QToolTip
from PyQt5.QtWidgets import QGridLayout

import pyperclip
import time
import os
import sys
import win32gui
import json

import re


from core.C2ServerAPIExample import GameChivalry
from core.guiServer import Chivalry
import core.wehbooks as wehbooks
import ctypes
import ctypes.wintypes as wintypes

# Windows clipboard update message
WM_CLIPBOARDUPDATE = 0x031D

class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt_x", wintypes.LONG),
        ("pt_y", wintypes.LONG),
    ]

class WinClipboardEventFilter(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    def nativeEventFilter(self, eventType, message):
        try:
            if eventType != 'windows_generic_MSG':
                return False, 0
            msg = MSG.from_address(int(message))
            if msg.message == WM_CLIPBOARDUPDATE:
                # Fire callback on clipboard update
                self._callback()
        except Exception:
            pass
        return False, 0

user32 = ctypes.windll.user32
user32.AddClipboardFormatListener.argtypes = [wintypes.HWND]
user32.AddClipboardFormatListener.restype = wintypes.BOOL

class InstantToolTipFilter(QObject):
    """Global event filter that shows tooltips after a small delay.
    Suppresses the default delayed ToolTip event so we control timing.
    """
    def __init__(self, delay_ms=500, parent=None):
        super().__init__(parent)
        self.delay_ms = int(delay_ms)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._show_pending)
        self._pending_widget = None

    def eventFilter(self, obj, ev):
        from PyQt5.QtWidgets import QWidget
        et = ev.type()
        if isinstance(obj, QWidget):
            if et == QEvent.Enter:
                if obj.toolTip():
                    self._pending_widget = obj
                    self._timer.start(self.delay_ms)
                else:
                    self._cancel()
                return False
            if et == QEvent.ToolTip:
                # suppress the built-in delayed tooltip
                return True
            if et in (QEvent.Leave, QEvent.MouseButtonPress):
                QToolTip.hideText()
                self._cancel()
                return False
            if et == QEvent.MouseMove:
                # keep timer running; no restart to avoid jitter
                return False
        return False

    def _cancel(self):
        if self._timer.isActive():
            self._timer.stop()
        self._pending_widget = None

    def _show_pending(self):
        w = self._pending_widget
        self._pending_widget = None
        if not w:
            return
        try:
            # Only show if cursor still within widget and tooltip is set
            if not w.toolTip():
                return
            pos = QCursor.pos()
            if not w.rect().contains(w.mapFromGlobal(pos)):
                return
            QToolTip.showText(pos, w.toolTip(), w)
        except Exception:
            # Be robust: never break the app from tooltip logic
            pass

user32.RemoveClipboardFormatListener.argtypes = [wintypes.HWND]
user32.RemoveClipboardFormatListener.restype = wintypes.BOOL


def check_chivalry_window():
    """Check if Chivalry 2 window is available"""
    try:
        hwnd = win32gui.FindWindow(None, "Chivalry 2  ")  # Note the spaces after the 2
        return hwnd != 0
    except Exception:
        return False

class ChivalryWaitingDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Waiting for Chivalry 2")
        self.setFixedSize(500, 350)
        self.setModal(True)

        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(15, 15, 15, 15)

        # Title
        title = QLabel("Waiting for Chivalry 2")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        # Let global theme handle colors, reduce bottom margin
        title.setContentsMargins(0, 0, 0, 5)
        layout.addWidget(title)

        # Instructions
        instructions = QLabel()
        instructions.setText(
            "Please launch your Chivalry 2 game.\n\n"
            "The admin tool will automatically continue once the game is detected."
        )
        instructions.setWordWrap(True)
        instructions.setAlignment(Qt.AlignCenter)
        # Let global theme handle colors and styling, reduce margins
        instructions.setContentsMargins(10, 5, 10, 5)
        instructions.setMinimumHeight(80)
        instructions.setMaximumHeight(80)
        instructions.setSizePolicy(instructions.sizePolicy().horizontalPolicy(), instructions.sizePolicy().Fixed)
        layout.addWidget(instructions)

        # Status label - avoid CSS styling to prevent cramping
        self.status_label = QLabel("Searching for Chivalry 2 window...")
        self.status_label.setAlignment(Qt.AlignCenter)

        # Set font using Qt methods instead of CSS
        font = QFont("Segoe UI", 12)
        font.setBold(True)
        self.status_label.setFont(font)

        # Let the global theme handle colors - no manual color setting
        self.status_label.setContentsMargins(10, 5, 10, 5)

        layout.addWidget(self.status_label)

        # Progress bar (indeterminate)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setMinimumHeight(25)
        self.progress_bar.setStyleSheet("margin: 10px 0px;")
        layout.addWidget(self.progress_bar)

        # Add some spacing before buttons
        layout.addSpacing(5)

        # Button layout
        button_layout = QHBoxLayout()

        # Theme toggle button
        self.theme_button = QPushButton("Dark Mode")
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setMinimumHeight(35)
        # Let global theme handle styling
        button_layout.addWidget(self.theme_button)

        # Skip button
        skip_button = QPushButton("Skip Waiting (Continue Anyway)")
        skip_button.clicked.connect(self.accept)
        skip_button.setMinimumHeight(35)
        # Let global theme handle styling
        button_layout.addWidget(skip_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Force layout to be calculated immediately
        layout.activate()
        self.adjustSize()

        # Timer to check for Chivalry 2 window
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_window)
        self.timer.start(1000)  # Check every second

        # Update theme button text based on current theme
        self.update_theme_button()

    def toggle_theme(self):
        """Toggle between dark and light theme"""
        app = QApplication.instance()
        current_is_dark = load_theme_preference()
        new_is_dark = not current_is_dark

        # Apply new theme
        if new_is_dark:
            apply_dark_theme(app)
        else:
            apply_light_theme(app)

        # Save preference
        save_theme_preference(new_is_dark)

        # Update button text
        self.update_theme_button()

        # Force refresh of this dialog's appearance
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def update_theme_button(self):
        """Toggle between dark and light theme"""
        is_dark = load_theme_preference()
        if is_dark:
            self.theme_button.setText("Light Mode")
        else:
            self.theme_button.setText("Dark Mode")

    def check_window(self):

        if check_chivalry_window():
            self.status_label.setText("Chivalry 2 window Detected.")
            self.status_label.setStyleSheet("font-weight: bold; color: green;")
            self.timer.stop()
            QTimer.singleShot(1500, self.accept)  # Wait 1.5 seconds then close
        else:
            self.status_label.setText(f"Searching for Chivalry 2 window...")

def parse_player_list_from_clipboard(text: str = None):
    """Parse players from provided clipboard text or current clipboard.
    Strategy:
      - Find the last occurrence of the header row (with Name/PlayFabPlayerId/EOSPlayerId...),
        and parse only the rows that follow it. This avoids mixing old and new snapshots
        if the clipboard happens to contain multiple blocks.
      - Return a list of (name, playfab_id) with simple de-duplication by PlayFab ID.
    """
    if text is None:
        try:
            text = pyperclip.paste()
        except Exception:
            text = ""
    lines = (text or "").strip().splitlines()

    # Find the last header line index
    header_indices = [i for i, l in enumerate(lines)
                      if ('Name' in l and 'PlayFabPlayerId' in l and 'EOSPlayerId' in l)]
    start_idx = header_indices[-1] + 1 if header_indices else (2 if len(lines) >= 3 else 0)

    players = []
    seen_ids = set()
    for line in lines[start_idx:]:
        if ' - ' not in line:
            continue
        parts = [p.strip() for p in line.split(' - ')]
        if len(parts) < 2:
            continue
        name = parts[0]
        playfab_id = parts[1]
        # Skip if looks like header row
        if name.lower() == 'name' or playfab_id.lower().startswith('playfab'):
            continue
        # Basic sanity for PlayFab ID (hex-like and length >= 12)
        if len(playfab_id) < 12:
            continue
        if playfab_id in seen_ids:
            continue
        seen_ids.add(playfab_id)
        players.append((name, playfab_id))

    return players

class ActionForm(QDialog):
    def __init__(self, action_name, player_id, player_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{action_name} Player")
        self.resize(450, 350)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModal)

        # Try to connect to game
        self.game = None
        try:
            self.game = GameChivalry()
        except Exception as e:
            print(f"[ACTION FORM] Could not connect to Chivalry 2: {e}")

        # Main layout
        main_layout = QVBoxLayout()

        # Form layout for player info and reason
        form_layout = QFormLayout()
        self.player_id_input = QLineEdit(player_id)
        self.player_id_input.setReadOnly(True)
        self.player_name = QLineEdit(player_name)
        self.player_name.setReadOnly(True)
        form_layout.addRow("Player ID:", self.player_id_input)
        form_layout.addRow("Player Name:", self.player_name)
        # Load last-used values for convenience
        default_reason_key = 'last_ban_reason' if action_name.lower() == 'ban' else 'last_kick_reason'
        self.reason_input = QLineEdit(get_persisted_value(default_reason_key, ""))
        form_layout.addRow("Reason:", self.reason_input)

        if action_name.lower() == "ban":
            self.time_input = QLineEdit(get_persisted_value('last_ban_duration', ""))
            self.time_input.setPlaceholderText("Duration in hours")
            form_layout.addRow("Time (hours):", self.time_input)
        else:
            self.time_input = None

        main_layout.addLayout(form_layout)

        # Preset buttons section
        preset_group = QGroupBox("Reason Presets")
        preset_layout = QVBoxLayout()

        # Determine preset slots by action type: 0-4 for Ban, 5-9 for Kick
        is_ban = (action_name.lower() == "ban")
        self.preset_slots = list(range(0, 5)) if is_ban else list(range(5, 10))

        # Help icon with tooltip for hover preview
        tip_icon = QLabel("Tip")
        tip_icon.setToolTip("You can hover a loading button to preview the saved reason" + (" and duration" if is_ban else ""))
        tip_icon.setFixedSize(30, 20)
        tip_icon.setAlignment(Qt.AlignCenter)
        tip_icon.setStyleSheet("QLabel { color: #888888; font-weight: bold; border: 1px solid #888888; border-radius: 8px; }")
        preset_layout.addWidget(tip_icon, 0, Qt.AlignRight)

        # Load preset buttons (single row of 5 buttons)
        load_layout1 = QHBoxLayout()
        self.load_buttons = []
        for idx, slot in enumerate(self.preset_slots):
            btn = QPushButton(f"Slot {idx}")
            btn.clicked.connect(lambda checked, s=slot: self.load_preset(s))
            btn.setMaximumWidth(80)
            self.load_buttons.append(btn)
            load_layout1.addWidget(btn)

        preset_layout.addWidget(QLabel(("Load Presets:" if is_ban else "Load Presets:")))
        preset_layout.addLayout(load_layout1)

        # Overwrite preset buttons (single row of 5 buttons)
        save_layout1 = QHBoxLayout()
        self.save_buttons = []
        for idx, slot in enumerate(self.preset_slots):
            btn = QPushButton(f"Slot {idx}")
            btn.clicked.connect(lambda checked, s=slot: self.save_preset(s))
            btn.setMaximumWidth(80)
            self.save_buttons.append(btn)
            save_layout1.addWidget(btn)

        preset_layout.addWidget(QLabel(("Save / Overwrite Presets:" if is_ban else "Save / Overwrite Presets:")))
        preset_layout.addLayout(save_layout1)

        # Clear preset buttons (single row of 5 buttons)
        clear_layout1 = QHBoxLayout()
        self.clear_buttons = []
        for idx, slot in enumerate(self.preset_slots):
            btn = QPushButton("Clear")
            btn.clicked.connect(lambda checked, s=slot: self.clear_preset(s))
            btn.setFixedWidth(80)
            self.clear_buttons.append(btn)
            clear_layout1.addWidget(btn)

        preset_layout.addWidget(QLabel(("Clear Presets:" if is_ban else "Clear Presets:")))
        preset_layout.addLayout(clear_layout1)

        preset_group.setLayout(preset_layout)
        main_layout.addWidget(preset_group)

        # Tickbox to not notify in-game

        self.notify_in_game = QCheckBox("Notify in-game")
        self.notify_in_game.setChecked(True)
        main_layout.addWidget(self.notify_in_game)

        # Action buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.perform_action)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        # Apply persisted values for admin/server/add time inputs in parent dashboard
        parent = self.parent()
        if parent and isinstance(parent, AdminDashboard):
            # Pre-fill admin/server message inputs
            parent.admin_message_input.setText(get_persisted_value('last_admin_msg', ""))
            parent.server_message_input.setText(get_persisted_value('last_server_msg', ""))

        self.action_name = action_name
        self.setLayout(main_layout)

        # Update button tooltips with preset contents
        self.update_preset_tooltips()

    def load_preset(self, slot):
        """Load a preset into the inputs (reason and duration if present)"""
        from core.guiServer import Chivalry
        chiv = Chivalry()
        preset_text = chiv.LoadPreset(slot)

        if preset_text:
            reason_val = preset_text
            duration_val = None
            if '|||' in preset_text:
                reason_val, duration_val = preset_text.split('|||', 1)
                reason_val = reason_val.strip()
                duration_val = duration_val.strip()
            # Fill reason
            self.reason_input.setText(reason_val)
            # Fill duration if this is a Ban form and duration is present
            if self.time_input is not None and duration_val is not None:
                self.time_input.setText(duration_val)
            QMessageBox.information(self, "Preset Loaded", f"Preset {slot} loaded successfully!")
        else:
            QMessageBox.warning(self, "No Preset", f"No preset found in slot {slot}.")

    def save_preset(self, slot):
        """Save the current reason (and duration if present) to a preset slot"""
        reason = self.reason_input.text().strip()
        if not reason:
            QMessageBox.warning(self, "Empty Reason", "Please enter a reason before saving to preset.")
            return
        # Include duration if this is a Ban form
        preset_payload = reason
        if self.time_input is not None:
            duration = self.time_input.text().strip()
            if duration:
                preset_payload = f"{reason}|||{duration}"

        from core.guiServer import Chivalry
        chiv = Chivalry()
        success = chiv.SavePreset(slot, preset_payload)

        if success:
            QMessageBox.information(self, "Preset Saved", f"Preset saved to slot {slot} successfully!")
            self.update_preset_tooltips()
        else:
            QMessageBox.warning(self, "Save Failed", f"Failed to save preset {slot}.")

    def update_preset_tooltips(self):
        """Update tooltips for load buttons to show preset contents (reason and optional duration)"""
        from core.guiServer import Chivalry
        chiv = Chivalry()
        presets = chiv.GetAllPresets()

        # Get current theme to use appropriate colors
        is_dark_theme = load_theme_preference()

        for idx, btn in enumerate(self.load_buttons):
            slot = self.preset_slots[idx]
            preset_text = presets.get(str(slot), "")
            if preset_text:
                reason_val, duration_val = preset_text.split('|||', 1) if '|||' in preset_text else (preset_text, "")
                reason_val = reason_val.strip()
                duration_val = duration_val.strip()
                # Truncate reason for tooltip
                display_reason = reason_val[:50] + "..." if len(reason_val) > 50 else reason_val
                tooltip_text = f"Slot {idx}: {display_reason}"
                if duration_val:
                    tooltip_text += f"  |  duration: {duration_val}"
                btn.setToolTip(tooltip_text)

                # Use theme-appropriate colors for filled slots
                if is_dark_theme:
                    btn.setStyleSheet("QPushButton { background-color: #2d5a2d; color: #ffffff; }")
                else:
                    btn.setStyleSheet("QPushButton { background-color: #e6ffe6; color: #333333; }")
            else:
                btn.setToolTip(f"Slot {idx}: Empty")
                btn.setStyleSheet("")

    def clear_preset(self, slot):
        """Clear a preset slot (remove reason and duration)."""
        from core.guiServer import Chivalry
        chiv = Chivalry()
        success = chiv.SavePreset(slot, "")
        if success:
            QMessageBox.information(self, "Preset Cleared", f"Preset {slot} cleared successfully!")
            self.update_preset_tooltips()
        else:
            QMessageBox.warning(self, "Clear Failed", f"Failed to clear preset {slot}.")

    def perform_action(self):
        reason = self.reason_input.text().strip()
        if not reason:
            QMessageBox.warning(self, "Error", "Please enter a reason.")
            return
        player_id = self.player_id_input.text()
        player_name = self.player_name.text()
        if self.action_name.lower() == "ban":
            time_str = self.time_input.text().strip()
            if not time_str.isdigit():
                QMessageBox.warning(self, "Error", "Please enter a valid number for time.")
                return
            time_hour = int(time_str)
            print(f"[{self.action_name.upper()}] Player ID={player_id}, Reason={reason}, Time={time_hour} hours")

            # Try to execute the ban command if game is connected
            action_executed = False
            if hasattr(self.game, 'banbyid'):
                try:
                    self.game.banbyid(player_id, time_hour, reason)
                    action_executed = True
                    if self.notify_in_game.isChecked():
                        self.game.AdminSay(f"{player_name} has been banned from the server.")
                except Exception as e:
                    QMessageBox.warning(self, "Game Connection Error", f"Could not execute ban command:\n{str(e)}")

            # Only send Discord notification if the action was actually executed
            if action_executed:
                # Persist last-used values for bans
                set_persisted_value('last_ban_reason', reason)
                set_persisted_value('last_ban_duration', str(time_hour))
                wehbooks.MessageForAdmin(player_id, player_name, reason, time_hour, "ban")
        else:
            print(f"[{self.action_name.upper()}] Player ID={player_id}, Reason={reason}")

            # Try to execute the kick command if game is connected
            action_executed = False
            if hasattr(self.game, 'kickbyid'):
                try:
                    self.game.kickbyid(player_id, reason)
                    action_executed = True
                    if self.notify_in_game.isChecked():
                        self.game.AdminSay(f"{player_name} has been kicked from the server.")
                except Exception as e:
                    QMessageBox.warning(self, "Game Connection Error", f"Could not execute kick command:\n{str(e)}")

            # Only send Discord notification if the action was actually executed
            if action_executed:
                wehbooks.MessageForAdmin(player_id, player_name, reason, None, "kick")
        self.accept()

    def toggle_theme(self):
        """Toggle between dark and light theme"""
        app = QApplication.instance()
        current_is_dark = load_theme_preference()
        new_is_dark = not current_is_dark

        # Apply new theme
        if new_is_dark:
            apply_dark_theme(app)
        else:
            apply_light_theme(app)

        # Save preference
        save_theme_preference(new_is_dark)

        # Update preset button colors
        self.update_preset_tooltips()

        # Force refresh of this dialog's appearance
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

class PlayerActionDialog(QDialog):
    def __init__(self, player_id, player_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Actions for {player_name} (ID: {player_id})")
        self.resize(380, 150)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModal)
        self.player_id = player_id
        self.player_name = player_name
        layout = QVBoxLayout()
        label = QLabel(f"Choose an action for player <b>{player_name}</b> (ID: {player_id}):")
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        btn_ban = QPushButton("Ban")
        btn_ban.setStyleSheet("background-color:#e74c3c; color: white; font-weight: bold;")
        btn_ban.clicked.connect(self.ban_player)
        layout.addWidget(btn_ban)
        btn_kick = QPushButton("Kick")
        btn_kick.setStyleSheet("background-color:#f39c12; color: white; font-weight: bold;")
        btn_kick.clicked.connect(self.kick_player)
        layout.addWidget(btn_kick)

        # Player profile button
        btn_profile = QPushButton("Chivalry2Stats player profile")
        btn_profile.setStyleSheet("background-color:#3498db; color: white; font-weight: bold;")
        btn_profile.clicked.connect(self.open_player_profile)
        layout.addWidget(btn_profile)

        # Copy player ID button
        btn_copy_id = QPushButton("Copy Player's PlayFabID")
        btn_copy_id.setStyleSheet("background-color:#2ecc71; color: white; font-weight: bold;")
        btn_copy_id.clicked.connect(self.copy_player_id)
        layout.addWidget(btn_copy_id)

        self.setLayout(layout)

    def copy_player_id(self):
        pyperclip.copy(self.player_id)
        QMessageBox.information(self, "PlayFabID Copied", f"Player's PlayFabID {self.player_id} copied to clipboard.")

    def ban_player(self):
        form = ActionForm("Ban", self.player_id, self.player_name, parent=self)
        form.exec_()

    def kick_player(self):
        form = ActionForm("Kick", self.player_id, self.player_name, parent=self)
        form.exec_()

    def open_player_profile(self):
        """Open the player's profile page on chivalry2stats.com"""
        profile_url = f"https://chivalry2stats.com/player?id={self.player_id}"

        # Import webbrowser to open the URL
        import webbrowser
        try:
            webbrowser.open(profile_url)
            print(f"[PROFILE] Opening player profile: {profile_url}")
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to open player profile:\n{str(e)}"
            )

class PlayersWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Players List")
        self.resize(600, 800)
        self.setModal(True)
        self.setWindowModality(Qt.ApplicationModal)

        # Try to connect to game
        self.game = None
        try:
            self.game = GameChivalry()
        except Exception as e:
            print(f"[PLAYERS WINDOW] Could not connect to Chivalry 2: {e}")
        main_layout = QVBoxLayout()

        # Info row for server name and players count
        info_row = QHBoxLayout()
        self.server_label = QLabel("Server: -")
        self.player_count_label = QLabel("Players: 0")
        info_row.addWidget(self.server_label)
        info_row.addStretch(1)
        info_row.addWidget(self.player_count_label)
        top_layout = QHBoxLayout()
        title = QLabel("<h3>Players List:</h3>")
        title.setAlignment(Qt.AlignLeft)
        top_layout.addWidget(title)
        refresh_btn = QPushButton("Refresh Player List")
        # Register for clipboard update messages via native event filter
        app = QApplication.instance()
        try:
            self._cb_event_filter = WinClipboardEventFilter(self._on_native_clipboard_update)
            QAbstractEventDispatcher.instance().installNativeEventFilter(self._cb_event_filter)
        except Exception:
            self._cb_event_filter = None

        refresh_btn.clicked.connect(self.refresh_player_list)
        refresh_btn.setStyleSheet("""
            QPushButton {
                padding: 10px;
                font-weight: bold;
                background-color: #1976d2;
                color: white;
                border: 1px solid #1565c0;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1e88e5;
                border: 1px solid #1976d2;
            }
            QPushButton:pressed {
                background-color: #1565c0;
            }
        """)
        main_layout.addWidget(refresh_btn)
        main_layout.addLayout(info_row)
        main_layout.addLayout(top_layout)
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search by ID or Player Name...")
        self.search_bar.textChanged.connect(self.filter_players)
        self.player_list = QListWidget()
        main_layout.addWidget(self.player_list)
        main_layout.addWidget(self.search_bar)
        self.player_list.itemClicked.connect(self.open_player_actions)
        self.setLayout(main_layout)
        if self.game is not None:
            self.refresh_player_list()

    def refresh_player_list(self):
        self.awaiting_player_list = True
        try:
            if hasattr(self.game, 'ListPlayers'):
                self.game.ListPlayers()
            else:
                QMessageBox.warning(self, "No Game Connection", "Cannot refresh player list - Chivalry 2 not connected.\n\nPlease ensure Chivalry 2 is running.")
                self.awaiting_player_list = False
                return
        except Exception as e:
            QMessageBox.warning(self, "Game Connection Error", f"Could not refresh player list:\n{str(e)}")
            self.awaiting_player_list = False
            return

        # Fallback if clipboard update signal does not arrive
        QTimer.singleShot(1500, self._fallback_parse_clipboard)

    def on_clipboard_changed(self):
        """Qt clipboard signal handler; process only when awaiting player list."""
        if not getattr(self, 'awaiting_player_list', False):
            return
        try:
            text = pyperclip.paste()
        except Exception:
            text = ""
        if " - " in (text or ""):
            self.players = parse_player_list_from_clipboard()
            self.filtered_players = self.players.copy()
            self.populate_list()
            self._update_info_from_text(text)
            self.awaiting_player_list = False

    def _fallback_parse_clipboard(self):
        if not getattr(self, 'awaiting_player_list', False):
            return
        try:
            text = pyperclip.paste()
        except Exception:
            text = ""
        if " - " in (text or ""):
            self.players = parse_player_list_from_clipboard()
            self.filtered_players = self.players.copy()
            self.populate_list()
            self._update_info_from_text(text)
            self.awaiting_player_list = False

    def populate_list(self):
        self.player_list.clear()
        for name, pid in self.filtered_players:
            self.player_list.addItem(f"{name} - {pid}")

    def _update_info_from_text(self, text: str):
        """Extract server name and player count and update the info row labels.
        Expected header example:
        "ServerName - OATS Duelyard  [Flourish to Duel Pit FFA Discord oatsduelyard] 134.255.251.182:10180"
        """
        lines = (text or "").strip().splitlines()
        server_name = "-"
        if lines:
            header = lines[0].strip()
            # Remove a trailing IP:port from header if present
            header_no_ip = re.sub(r"\s*(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\s*$", "", header)

            # Preferred: capture the name after 'ServerName - ' up to a double space before the next section
            m = re.match(r"^\s*ServerName\s*-\s*(.+?)\s{2,}.*$", header_no_ip)
            if m:
                server_name = m.group(1).strip()
            else:
                # Fallbacks if format varies slightly
                if header_no_ip.lower().startswith("servername") and '-' in header_no_ip:
                    try:
                        after_dash = header_no_ip.split('-', 1)[1].strip()
                        # stop at first double-space chunk if present
                        server_name = after_dash.split('  ')[0].strip() or server_name
                    except Exception:
                        pass
                elif ' - ' in header_no_ip:
                    try:
                        server_name = header_no_ip.split(' - ', 1)[1].split('  ')[0].strip() or server_name
                    except Exception:
                        pass
            # Extra safety: strip any trailing IP:port if it slipped into the name
            server_name = re.sub(r"\s*(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\s*$", "", server_name)

        # Count players: skip the two header lines and count rows that look like player entries
        data_lines = lines[2:] if len(lines) >= 3 else []
        player_rows = [ln for ln in data_lines if " - " in ln]
        count = len(player_rows)
        self.server_label.setText(f"Server: {server_name}")
        self.player_count_label.setText(f"Players: {count}")

    def populate_list(self):
        self.player_list.clear()
        for name, pid in self.filtered_players:
            self.player_list.addItem(f"{name} - {pid}")

    def filter_players(self, text):
        text = text.lower()
        self.filtered_players = [
            (name, pid) for name, pid in self.players
            if text in name.lower() or text in pid.lower()
        ]
        self.populate_list()

    def open_player_actions(self, item):
        text = item.text()
        if " - " not in text:
            return
        name, pid = text.split(" - ", 1)
        dialog = PlayerActionDialog(pid, name, parent=self)
        dialog.exec_()

class ActionDialog(QDialog):
    def __init__(self, title, fields, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.inputs = {}
        self.setModal(True)
        self.setWindowModality(Qt.WindowModal)

        layout = QFormLayout()
        for field in fields:
            line_edit = QLineEdit()
            layout.addRow(field + ":", line_edit)
            self.inputs[field] = line_edit

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # IMPORTANT: set the layout so the dialog renders its controls
        self.setLayout(layout)

    def get_inputs(self):
        return [line_edit.text().strip() for line_edit in self.inputs.values()]

class ConsoleKeyDialog(QDialog):
    def __init__(self, current_vk: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Console Key")
        self.setModal(True)
        self.setWindowModality(Qt.WindowModal)
        self.resize(420, 180)

        self.captured_vk = None

        layout = QVBoxLayout()
        instructions = QLabel(
            "Press the key you use to open the in-game console.\n"
            "The key code will be saved and used for console operations."
        )
        instructions.setWordWrap(True)
        instructions.setAlignment(Qt.AlignCenter)
        layout.addWidget(instructions)

        self.status = QLabel("Waiting for key press...")
        self.status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status)

        if current_vk:
            try:
                vk_int = int(current_vk)
                self.status.setText(f"Current configured key: VK {vk_int} (press a key to change)")
            except Exception:
                pass

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ok_button = buttons.button(QDialogButtonBox.Ok)
        self.ok_button.setEnabled(False)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def keyPressEvent(self, event):
        try:
            # Prefer native VK on Windows
            vk = event.nativeVirtualKey() if hasattr(event, 'nativeVirtualKey') else None
        except Exception:
            vk = None
        if vk is None or vk == 0:
            # Fallback: use Qt key for common ASCII keys
            vk = event.key()
        self.captured_vk = int(vk)
        self.status.setText(f"Captured key: VK {self.captured_vk}. Click OK to save or press another key.")
        self.ok_button.setEnabled(True)

class AdminDashboard(QWidget):
    def __init__(self):
        super().__init__()

        # Try to connect to Chivalry 2, but don't fail if it's not available
        self.game = None
        self.chivalry_connected = False
        self.server_connected = False
        self.last_player_count = 0

        self.setWindowTitle("Admin Dashboard")
        self.resize(1400, 500)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(24, 16, 24, 16)
        main_layout.setSpacing(16)
        title = QLabel("Admin Dashboard")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setContentsMargins(0, 4, 0, 4)
        main_layout.addWidget(title)
        status_group = QGroupBox("Server Status")
        status_layout = QVBoxLayout()

        # Initialize status label (will be updated by update_connection_status)
        self.status_label = QLabel("Checking connection...")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.status_label)

        # Add webhook status
        self.webhook_status_label = QLabel()
        self.webhook_status_label.setAlignment(Qt.AlignCenter)
        self.update_webhook_status()
        status_layout.addWidget(self.webhook_status_label)

        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        # Admin Message Section
        admin_message_group = QGroupBox("Admin Message")
        admin_message_layout = QVBoxLayout()

        # Input + Send in one row
        admin_input_row = QHBoxLayout()
        self.admin_message_input = QLineEdit()
        self.admin_message_input.setPlaceholderText("Type the admin message to send...")
        # Pre-fill from persisted cache and persist on edit
        self.admin_message_input.setText(get_persisted_value('last_admin_msg', ""))
        self.admin_message_input.editingFinished.connect(lambda: set_persisted_value('last_admin_msg', self.admin_message_input.text().strip()))
        admin_input_row.addWidget(self.admin_message_input, 1)
        btn_send_admin_message = QPushButton("Send Admin Message")
        btn_send_admin_message.setMinimumWidth(160)
        btn_send_admin_message.clicked.connect(self.send_admin_message)
        admin_input_row.addWidget(btn_send_admin_message)
        admin_message_layout.addLayout(admin_input_row)

        admin_preset_layout = QVBoxLayout()
        self.admin_load_buttons = []
        self.admin_save_buttons = []
        self.admin_clear_buttons = []

        # Help icon with tooltip
        tip_icon_admin = QLabel("Tip")
        tip_icon_admin.setToolTip("You can hover a loading button to preview the saved message")
        tip_icon_admin.setFixedSize(30, 20)
        tip_icon_admin.setAlignment(Qt.AlignCenter)
        tip_icon_admin.setStyleSheet("QLabel { color: #888888; font-weight: bold; border: 1px solid #888888; border-radius: 8px; }")
        admin_preset_layout.addWidget(tip_icon_admin, 0, Qt.AlignRight)

        # Columns for each slot
        admin_columns_row = QHBoxLayout()
        for idx in range(ADMIN_PRESET_COUNT):
            col = QVBoxLayout()
            col.setSpacing(6)
            col.addWidget(QLabel(f"Slot {idx}"), 0)

            btn_load = QPushButton("Load")
            btn_load.clicked.connect(lambda _, s=idx: self.load_admin_preset(s))
            btn_load.setMinimumWidth(90)
            self.admin_load_buttons.append(btn_load)
            col.addWidget(btn_load)

            btn_save = QPushButton("Save / Overwrite")
            btn_save.clicked.connect(lambda _, s=idx: self.save_admin_preset(s))
            btn_save.setMinimumWidth(90)
            self.admin_save_buttons.append(btn_save)
            col.addWidget(btn_save)

            btn_clear = QPushButton("Clear")
            btn_clear.clicked.connect(lambda _, s=idx: self.clear_admin_preset(s))
            btn_clear.setMinimumWidth(90)
            self.admin_clear_buttons.append(btn_clear)
            col.addWidget(btn_clear)

            admin_columns_row.addLayout(col, 1)
        admin_preset_layout.addLayout(admin_columns_row)

        admin_message_layout.addLayout(admin_preset_layout)
        admin_message_group.setLayout(admin_message_layout)

        # Server Message Section
        server_message_group = QGroupBox("Server Message")
        server_message_layout = QVBoxLayout()

        # Input + Send in one row
        server_input_row = QHBoxLayout()
        self.server_message_input = QLineEdit()
        self.server_message_input.setPlaceholderText("Type the server message to send...")
        # Pre-fill from persisted cache and persist on edit
        self.server_message_input.setText(get_persisted_value('last_server_msg', ""))
        self.server_message_input.editingFinished.connect(lambda: set_persisted_value('last_server_msg', self.server_message_input.text().strip()))
        server_input_row.addWidget(self.server_message_input, 1)
        btn_send_server_message = QPushButton("Send Server Message")
        btn_send_server_message.setMinimumWidth(160)
        btn_send_server_message.clicked.connect(self.send_server_message)
        server_input_row.addWidget(btn_send_server_message)
        server_message_layout.addLayout(server_input_row)

        server_preset_layout = QVBoxLayout()
        self.server_load_buttons = []
        self.server_save_buttons = []
        self.server_clear_buttons = []

        # Help icon with tooltip
        tip_icon_server = QLabel("Tip")
        tip_icon_server.setToolTip("You can hover a loading button to preview the saved message")
        tip_icon_server.setFixedSize(30, 20)
        tip_icon_server.setAlignment(Qt.AlignCenter)
        tip_icon_server.setStyleSheet("QLabel { color: #888888; font-weight: bold; border: 1px solid #888888; border-radius: 8px; }")
        server_preset_layout.addWidget(tip_icon_server, 0, Qt.AlignRight)

        # Columns for each slot
        server_columns_row = QHBoxLayout()
        for idx in range(SERVER_PRESET_COUNT):
            col = QVBoxLayout()
            col.setSpacing(6)
            col.addWidget(QLabel(f"Slot {idx}"), 0)

            btn_load = QPushButton("Load")
            btn_load.clicked.connect(lambda _, s=idx: self.load_server_preset(s))
            btn_load.setMinimumWidth(90)
            self.server_load_buttons.append(btn_load)
            col.addWidget(btn_load)

            btn_save = QPushButton("Save / Overwrite")
            btn_save.clicked.connect(lambda _, s=idx: self.save_server_preset(s))
            btn_save.setMinimumWidth(90)
            self.server_save_buttons.append(btn_save)
            col.addWidget(btn_save)

            btn_clear = QPushButton("Clear")
            btn_clear.clicked.connect(lambda _, s=idx: self.clear_server_preset(s))
            btn_clear.setMinimumWidth(90)
            self.server_clear_buttons.append(btn_clear)
            col.addWidget(btn_clear)

            server_columns_row.addLayout(col, 1)
        server_preset_layout.addLayout(server_columns_row)

        server_message_layout.addLayout(server_preset_layout)
        server_message_group.setLayout(server_message_layout)

        # Commands Section
        commands_group = QGroupBox("Commands")
        commands_layout = QVBoxLayout()

        # Row of general actions
        actions_row = QHBoxLayout()
        btn_players = QPushButton("Players List")
        btn_players.clicked.connect(self.open_players_window)
        actions_row.addWidget(btn_players)

        btn_add_time = QPushButton("Add Time")
        btn_add_time.clicked.connect(self.open_add_time_dialog)
        actions_row.addWidget(btn_add_time)

        commands_layout.addLayout(actions_row)

        # Arbitration subgroup
        arb_group = QGroupBox("Arbitration")
        arb_layout = QVBoxLayout()

        btn_first_to = QPushButton("Match Arbitration (First To)")
        btn_first_to.clicked.connect(self.open_first_to_window)
        arb_layout.addWidget(btn_first_to)

        arb_group.setLayout(arb_layout)
        commands_layout.addWidget(arb_group)

        # Keep Admin/Server preset panels under Commands
        admin_server_row = QHBoxLayout()
        admin_server_row.setSpacing(12)
        admin_message_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        server_message_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        admin_server_row.addWidget(admin_message_group, 1)
        admin_server_row.addWidget(server_message_group, 1)
        commands_layout.addLayout(admin_server_row)

        commands_group.setLayout(commands_layout)
        main_layout.addWidget(commands_group)

        # Settings Section
        settings_group = QGroupBox("Settings")
        settings_layout = QVBoxLayout()

        btn_webhook_config = QPushButton("Configure Discord Webhook")
        btn_webhook_config.clicked.connect(self.configure_discord_webhook)
        settings_layout.addWidget(btn_webhook_config)

        btn_discord_id_config = QPushButton("Configure Discord User ID")
        btn_discord_id_config.clicked.connect(self.configure_discord_user_id)
        settings_layout.addWidget(btn_discord_id_config)

        # Configure Console Key button
        btn_console_key = QPushButton("Configure Console Key")
        btn_console_key.clicked.connect(self.configure_console_key)
        settings_layout.addWidget(btn_console_key)

        # Theme toggle button
        self.theme_button = QPushButton("Dark Mode")
        self.theme_button.clicked.connect(self.toggle_theme)
        settings_layout.addWidget(self.theme_button)

        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.setLayout(main_layout)

        # Now that UI is initialized, set up connection monitoring
        self.check_game_connection()

        # Set up periodic connection checking timer
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self.check_game_connection)
        self.connection_timer.start(5000)  # Check every 5 seconds

        # Update theme button text based on current theme
        self.update_theme_button()

        # Initialize tooltips/colors for admin/server presets
        self.update_admin_preset_tooltips()
        self.update_server_preset_tooltips()

        # Keep track of player window instance
        self.players_window = None
        self.first_to_window = None

    def center_on_screen(self):
        try:
            screen = self.screen() or QApplication.primaryScreen()
            if not screen:
                return
            avail = screen.availableGeometry()
            frame = self.frameGeometry()
            frame.moveCenter(avail.center())
            self.move(frame.topLeft())
        except Exception as e:
            print(f"[UI] Centering failed: {e}")

    def showEvent(self, event):
        super().showEvent(event)
        # Center after the widget has a native window and final frame metrics
        QTimer.singleShot(0, self.center_on_screen)

    def check_game_connection(self):
        """Check game and server connection status"""
        # Check if Chivalry 2 window exists
        game_window_exists = check_chivalry_window()

        # Try to connect to game if window exists but we're not connected
        if game_window_exists and not self.chivalry_connected:
            try:
                self.game = GameChivalry()
                self.chivalry_connected = True
                print("[CONNECTION] Successfully connected to Chivalry 2")
            except Exception as e:
                print(f"[CONNECTION] Could not connect to Chivalry 2: {e}")
                self.chivalry_connected = False
                self.game = None

        # If window doesn't exist, mark as disconnected
        elif not game_window_exists and self.chivalry_connected:
            print("[CONNECTION] Chivalry 2 window no longer found - disconnecting")
            self.chivalry_connected = False
            self.server_connected = False
            self.game = None

        # Note: We don't automatically check server connection to avoid disrupting gameplay
        # Server connection status will be determined only when user manually refreshes player list

        # Update status display
        self.update_connection_status()

    # ---- Admin/Server presets helpers ----
    def update_admin_preset_tooltips(self):
        is_dark_theme = load_theme_preference()
        for idx, btn in enumerate(getattr(self, 'admin_load_buttons', [])):
            preset_text = get_admin_preset(idx)
            if preset_text:
                display = (preset_text[:50] + "...") if len(preset_text) > 50 else preset_text
                btn.setToolTip(f"Slot {idx}: {display}")
                if is_dark_theme:
                    btn.setStyleSheet("QPushButton { background-color: #2d5a2d; color: #ffffff; }")
                else:
                    btn.setStyleSheet("QPushButton { background-color: #e6ffe6; color: #333333; }")
            else:
                btn.setToolTip(f"Slot {idx}: Empty")
                btn.setStyleSheet("")

    def update_server_preset_tooltips(self):
        is_dark_theme = load_theme_preference()
        for idx, btn in enumerate(getattr(self, 'server_load_buttons', [])):
            preset_text = get_server_preset(idx)
            if preset_text:
                display = (preset_text[:50] + "...") if len(preset_text) > 50 else preset_text
                btn.setToolTip(f"Slot {idx}: {display}")
                if is_dark_theme:
                    btn.setStyleSheet("QPushButton { background-color: #2d5a2d; color: #ffffff; }")
                else:
                    btn.setStyleSheet("QPushButton { background-color: #e6ffe6; color: #333333; }")
            else:
                btn.setToolTip(f"Slot {idx}: Empty")
                btn.setStyleSheet("")

    def load_admin_preset(self, slot):
        text = get_admin_preset(slot)
        if text:
            self.admin_message_input.setText(text)
            QMessageBox.information(self, "Preset Loaded", f"Admin Message preset {slot} loaded successfully!")
        else:
            QMessageBox.warning(self, "No Preset", f"No Admin Message preset found in slot {slot}.")

    def save_admin_preset(self, slot):
        text = self.admin_message_input.text().strip()
        if not text:
            QMessageBox.warning(self, "Empty Message", "Please enter a message before saving to preset.")
            return
        set_admin_preset(slot, text)
        QMessageBox.information(self, "Preset Saved", f"Admin Message preset saved to slot {slot} successfully!")
        self.update_admin_preset_tooltips()

    def clear_admin_preset(self, slot):
        set_admin_preset(slot, "")
        QMessageBox.information(self, "Preset Cleared", f"Admin Message preset {slot} cleared successfully!")
        self.update_admin_preset_tooltips()

    def load_server_preset(self, slot):
        text = get_server_preset(slot)
        if text:
            self.server_message_input.setText(text)
            QMessageBox.information(self, "Preset Loaded", f"Server Message preset {slot} loaded successfully!")
        else:
            QMessageBox.warning(self, "No Preset", f"No Server Message preset found in slot {slot}.")

    def save_server_preset(self, slot):
        text = self.server_message_input.text().strip()
        if not text:
            QMessageBox.warning(self, "Empty Message", "Please enter a message before saving to preset.")
            return
        set_server_preset(slot, text)
        QMessageBox.information(self, "Preset Saved", f"Server Message preset saved to slot {slot} successfully!")
        self.update_server_preset_tooltips()

    def clear_server_preset(self, slot):
        set_server_preset(slot, "")
        QMessageBox.information(self, "Preset Cleared", f"Server Message preset {slot} cleared successfully!")
        self.update_server_preset_tooltips()


        # Note: We don't automatically check server connection to avoid disrupting gameplay
        # Server connection status will be determined only when user manually refreshes player list

        # Update status display
        self.update_connection_status()

    def update_connection_status(self):
        """Update the connection status display"""
        if self.chivalry_connected:
            self.status_label.setText("Chivalry 2 Connected")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.status_label.setText("Chivalry 2 Not Connected")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")

    def update_webhook_status(self):
        """Update the webhook status display"""
        status = wehbooks.get_webhook_status()

        if status['primary_active'] and status['secondary_active']:
            self.webhook_status_label.setText("Discord: Primary + Secondary Active")
            self.webhook_status_label.setStyleSheet("color: green;")
        elif status['primary_active']:
            self.webhook_status_label.setText("Discord: Primary Active")
            self.webhook_status_label.setStyleSheet("color: green;")
        elif status['secondary_active']:
            self.webhook_status_label.setText("Discord: Secondary Active")
            self.webhook_status_label.setStyleSheet("color: green;")
        else:
            self.webhook_status_label.setText("Discord: Not Configured")
            self.webhook_status_label.setStyleSheet("color: orange;")

    def send_admin_message(self):
        msg = self.admin_message_input.text().strip()
        # Persist last admin message
        if msg:
            set_persisted_value('last_admin_msg', msg)

        if not msg:
            QMessageBox.warning(self, "Error", "Please enter a message to send.")
            return
        print(f"[ADMIN MESSAGE] {msg}")

        # Try to send to game if connected
        message_sent = False
        if self.chivalry_connected and hasattr(self.game, 'AdminSay'):
            try:
                self.game.AdminSay(msg)
                message_sent = True
                #QMessageBox.information(self, "Message Sent", "Admin message sent successfully to game and Discord!")
            except Exception as e:
                QMessageBox.warning(self, "Game Error", f"Failed to send message to game:\n{str(e)}")

        # Only send Discord notification if the message was actually sent to game
        #if message_sent:
            # wehbooks.MessageForAdmin("N/A", "N/A", msg, None, "adminsay")

        #self.admin_message_input.clear()

    def send_server_message(self):
        msg = self.server_message_input.text().strip()
        # Persist last server message
        if msg:
            set_persisted_value('last_server_msg', msg)

        if not msg:
            QMessageBox.warning(self, "Error", "Please enter a message to send.")
            return
        print(f"[SERVER MESSAGE] {msg}")

        # Try to send to game if connected
        message_sent = False
        if self.chivalry_connected and hasattr(self.game, 'ServerSay'):
            try:
                self.game.ServerSay(msg)
                message_sent = True
            except Exception as e:
                QMessageBox.warning(self, "Game Error", f"Failed to send message to game:\n{str(e)}")

        # Only send Discord notification if the message was actually sent to game
        #if message_sent:
            # wehbooks.MessageForAdmin("N/A", "N/A", msg, None, "serversay")

        # self.server_message_input.clear()

    def open_players_window(self):
        # Pre-fill dashboard fields from persisted values
        self.admin_message_input.setText(get_persisted_value('last_admin_msg', ""))
        self.server_message_input.setText(get_persisted_value('last_server_msg', ""))

        # Check if player window already exists and is visible
        if self.players_window is not None and self.players_window.isVisible():
            # Window already exists, just bring it to front (no auto-refresh)
            self.players_window.raise_()
            self.players_window.activateWindow()
        else:
            # Create new window or reuse closed one
            if self.players_window is None:
                self.players_window = PlayersWindow(self)
                # Connect the finished signal to clean up reference when window is closed
                self.players_window.finished.connect(lambda: setattr(self, 'players_window', None))

            # Set focus to the dialog and bring it to front (no auto-refresh)
            self.players_window.show()
            self.players_window.raise_()
            self.players_window.activateWindow()
            self.players_window.exec_()

    def open_add_time_dialog(self):
        dialog = ActionDialog("Add Time", ["Time to add (minutes)"], parent=self)
        # Pre-fill last add time value
        dialog.inputs["Time to add (minutes)"] .setText(get_persisted_value('last_add_time', ""))
        if dialog.exec_() == QDialog.Accepted:
            added_time = dialog.get_inputs()[0]
            print(f" +{added_time}min")

            # Try to add time to game if connected
            time_added = False
            if self.chivalry_connected and hasattr(self.game, 'AddTime'):
                try:
                    self.game.AddTime(added_time)
                    time_added = True
                    # Delay the success message to avoid stealing focus from game during console operations
                    QTimer.singleShot(2000, lambda: QMessageBox.information(self, "Time Added", f"Successfully added {added_time} minutes to the game!"))
                except Exception as e:
                    QMessageBox.warning(self, "Game Error", f"Failed to add time to game:\n{str(e)}")

            # Only send Discord notification if time was actually added to game
            if time_added:
                # Persist last add time
                set_persisted_value('last_add_time', str(added_time))
                #wehbooks.MessageForAdmin("N/A", "N/A", f"Added {added_time} minutes", added_time, "time")

    def open_first_to_window(self):
        if self.first_to_window is not None and self.first_to_window.isVisible():
            self.first_to_window.raise_()
            self.first_to_window.activateWindow()
            return
        self.first_to_window = FirstToScoreboardWindow(self)
        self.first_to_window.setAttribute(Qt.WA_DeleteOnClose, True)
        self.first_to_window.finished.connect(lambda: setattr(self, 'first_to_window', None))
        self.first_to_window.show()
        self.first_to_window.raise_()
        self.first_to_window.activateWindow()
        self.first_to_window.exec_()

    def prompt_wide_text(self, title, label, text):
        dlg = QInputDialog(self)
        dlg.setWindowTitle(title)
        dlg.setLabelText(label)
        dlg.setTextValue(text)
        dlg.setInputMode(QInputDialog.TextInput)
        dlg.resize(900, 150)
        try:
            le = dlg.findChild(QLineEdit)
            if le is not None:
                le.setMinimumWidth(820)
                le.setMinimumHeight(24)
                le.setCursorPosition(len(text))
        except Exception:
            pass
        ok = dlg.exec_()
        return dlg.textValue(), ok == QDialog.Accepted

    def configure_discord_webhook(self):
        """Allow user to reconfigure Discord webhooks"""
        import os

        # Get current webhook URLs if they exist
        current_primary_url = ""
        current_secondary_url = ""
        localconfig = "localconfig"
        if os.path.exists(localconfig):
            try:
                with open(localconfig, 'r', encoding='utf-8') as f:
                    lines = f.read().strip().split('\n')
                    if len(lines) >= 1 and lines[0] != "None":
                        current_primary_url = lines[0]
                    if len(lines) >= 2 and lines[1] != "None":
                        current_secondary_url = lines[1]
            except Exception:
                pass

        # Prompt for primary webhook URL
        primary_url, ok = self.prompt_wide_text(
            "Primary Discord Webhook Configuration",
            "Enter your primary Discord Webhook URL:\n(Leave empty to disable Discord notifications)",
            current_primary_url
        )

        if not ok:
            return

        primary_url = primary_url.strip()
        if primary_url and not primary_url.startswith("https://discord.com/api/webhooks/"):
            QMessageBox.warning(
                self,
                "Invalid URL",
                "Primary Discord webhook URL must start with:\n"
                "https://discord.com/api/webhooks/"
            )
            return

        # Prompt for secondary webhook URL (only if primary is configured)
        secondary_url = ""
        if primary_url:
            secondary_url, ok2 = self.prompt_wide_text(
                "Secondary Discord Webhook Configuration",
                "Enter your secondary Discord Webhook URL (optional):\n(Leave empty to use only the primary webhook)",
                current_secondary_url
            )

            if ok2 and secondary_url.strip():
                secondary_url = secondary_url.strip()
                if not secondary_url.startswith("https://discord.com/api/webhooks/"):
                    QMessageBox.warning(
                        self,
                        "Invalid URL",
                        "Secondary Discord webhook URL must start with:\n"
                        "https://discord.com/api/webhooks/"
                    )
                    return
            else:
                secondary_url = ""

        # Save the URLs to file, preserving all other lines in localconfig
        try:
            # Read all existing lines
            lines = []
            if os.path.exists(localconfig):
                with open(localconfig, 'r', encoding='utf-8') as f:
                    lines = f.read().splitlines()
            # Ensure at least 3 header lines and 10 preset lines
            min_len = 13
            if len(lines) < min_len:
                lines += [""] * (min_len - len(lines))
            # Update header values
            lines[0] = primary_url if primary_url else 'None'
            lines[1] = secondary_url if secondary_url else 'None'
            # Preserve existing Discord user ID in line 2 if present, else keep current content
            if len(lines) < 3:
                lines += ["None"] * (3 - len(lines))
            # Write all lines back
            with open(localconfig, 'w', encoding='utf-8') as f:
                for line in lines:
                    f.write(line + "\n")

            # Reinitialize webhooks
            webhook_initialized = wehbooks.initialize_webhook()

            # Update the status display
            self.update_webhook_status()

            if primary_url or secondary_url:
                if webhook_initialized:
                    message = "Discord webhook(s) have been configured successfully!"
                    if primary_url and secondary_url:
                        message = "Both primary and secondary Discord webhooks have been configured successfully!"
                    elif primary_url:
                        message = "Primary Discord webhook has been configured successfully!"
                    elif secondary_url:
                        message = "Secondary Discord webhook has been configured successfully!"

                    QMessageBox.information(
                        self,
                        "Configuration Successful",
                        message
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Configuration Error",
                        "Unable to initialize Discord webhook(s).\n"
                        "Please check that the URL(s) are correct and valid (active) links."
                    )
            else:
                QMessageBox.information(
                    self,
                    "Webhooks Disabled",
                    "Discord notifications have been disabled."
                )

        except Exception as e:
            QMessageBox.warning(
                self,
                "Save Error",
                f"Unable to save configuration:\n{str(e)}"
            )

    def configure_discord_user_id(self):
        """Allow user to configure Discord User ID"""
        import os

        # Get current Discord user ID if it exists
        current_discord_user_id = ""
        localconfig = "localconfig"
        if os.path.exists(localconfig):
            try:
                with open(localconfig, 'r', encoding='utf-8') as f:
                    lines = f.read().strip().split('\n')
                    if len(lines) >= 3 and lines[2] != "None":
                        current_discord_user_id = lines[2]
            except Exception:
                pass

        # Prompt for new Discord user ID
        discord_user_id, ok = QInputDialog.getText(
            self,
            "Discord User ID Configuration",
            "Enter your Discord User ID:\n"
            "(This will be used for @mentions in notifications)\n"
            "(Leave empty to disable mentions)",
            text=current_discord_user_id
        )

        if not ok:
            return

        discord_user_id = discord_user_id.strip()

        # Save the Discord user ID to file, preserving all other lines
        try:
            # Read all existing lines
            lines = []
            if os.path.exists(localconfig):
                with open(localconfig, 'r', encoding='utf-8') as f:
                    lines = f.read().splitlines()
            # Ensure at least 3 header lines and 10 preset lines
            min_len = 13
            if len(lines) < min_len:
                lines += [""] * (min_len - len(lines))
            # Update header values
            if len(lines) < 1:
                lines.append('None')
            if len(lines) < 2:
                lines.append('None')
            if len(lines) < 3:
                lines.append('None')
            lines[2] = discord_user_id if discord_user_id else 'None'
            # Write all lines back
            with open(localconfig, 'w', encoding='utf-8') as f:
                for line in lines:
                    f.write(line + "\n")

            if discord_user_id:
                QMessageBox.information(
                    self,
                    "Configuration Successful",
                    f"Discord User ID has been set to: {discord_user_id}"
                )
            else:
                QMessageBox.information(
                    self,
                    "Configuration Successful",
                    "Discord User ID has been cleared. Mentions will be disabled."
                )

        except Exception as e:
            QMessageBox.warning(
                self,
                "Save Error",
                f"Unable to save Discord User ID:\n{str(e)}"
            )

    def configure_console_key(self):
        """Prompt user to press the key used to open the in-game console and persist its VK code."""
        # Load current value if any
        try:
            current_vk = get_persisted_value('console_vk', "")
        except Exception:
            current_vk = ""

        dlg = ConsoleKeyDialog(current_vk=current_vk, parent=self)
        if dlg.exec_() == QDialog.Accepted and dlg.captured_vk is not None:
            # Save as integer string to localconfig via persisted storage
            set_persisted_value('console_vk', str(dlg.captured_vk))
            QMessageBox.information(self, "Console Key Saved", f"Console key saved as VK {dlg.captured_vk}.")

    def toggle_theme(self):
        """Toggle between dark and light theme"""
        app = QApplication.instance()
        current_is_dark = load_theme_preference()
        new_is_dark = not current_is_dark

        # Apply new theme
        if new_is_dark:
            apply_dark_theme(app)
        else:
            apply_light_theme(app)

        # Save preference
        save_theme_preference(new_is_dark)

        # Update button text
        self.update_theme_button()

        # Update preset button colors if this is an action dialog
        if hasattr(self, 'update_preset_tooltips'):
            self.update_preset_tooltips()

        # Update colors/tooltips for Admin/Server preset buttons
        if hasattr(self, 'update_admin_preset_tooltips'):
            self.update_admin_preset_tooltips()
        if hasattr(self, 'update_server_preset_tooltips'):
            self.update_server_preset_tooltips()

        # Force refresh of this window's appearance
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def update_theme_button(self):
        """Update theme button text based on current theme"""
        is_dark = load_theme_preference()
        if is_dark:
            self.theme_button.setText("Light Mode")
        else:
            self.theme_button.setText("Dark Mode")

class FirstToScoreboardWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowTitle("Match Arbitration (First To)")
        self.resize(1100, 700)
        self.setSizeGripEnabled(True)

        # State
        self.game = None
        self.chivalry_connected = False
        self.p1_score = 0
        self.p2_score = 0

        main = QVBoxLayout(self)
        main.setContentsMargins(20, 16, 20, 16)
        main.setSpacing(12)

        # Title
        ttl = QLabel("Match Arbitration (First To)")
        ttl.setFont(QFont("Segoe UI", 18, QFont.Bold))
        ttl.setAlignment(Qt.AlignCenter)
        main.addWidget(ttl)

        # Match settings
        settings = QGroupBox("Match Settings")
        settings_l = QFormLayout()
        settings_l.setLabelAlignment(Qt.AlignRight)
        settings_l.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        settings_l.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.rounds_input = QLineEdit()
        self.rounds_input.setPlaceholderText("e.g. 5")
        self.rounds_input.setValidator(QIntValidator(1, 999, self))
        settings_l.addRow("Rounds to win:", self.rounds_input)

        self.start_msg_input = QLineEdit()
        self.start_msg_input.setPlaceholderText("e.g. Duel starting now!")
        settings_l.addRow("Start message:", self.start_msg_input)

        self.win_msg_input = QLineEdit()
        self.win_msg_input.setPlaceholderText("e.g. Congratulations to the winner! And GG to the both of you.")
        settings_l.addRow("End message:", self.win_msg_input)

        settings.setLayout(settings_l)
        settings.layout().setContentsMargins(12, 8, 12, 8)
        main.addWidget(settings)

        # Broadcast
        broadcast = QGroupBox("Broadcast")
        b_l = QVBoxLayout()
        b_l.setContentsMargins(12, 8, 12, 8)

        notification_row = QHBoxLayout()

        self.ft_discord_notification = QCheckBox("Broadcast match results to Discord")
        self.ft_discord_notification.setChecked(False)

        tag_row = QHBoxLayout()
        tag_row.addWidget(QLabel("Tag prefix (optional):"))
        self.broadcast_tag_input = QLineEdit()
        self.broadcast_tag_input.setPlaceholderText("Tournament")
        tip_icon_tag = QLabel("Tip")
        tip_icon_tag.setToolTip("Brackets are added automatically")
        tip_icon_tag.setFixedSize(30, 20)
        tip_icon_tag.setAlignment(Qt.AlignCenter)
        tip_icon_tag.setStyleSheet("QLabel { color: #888888; font-weight: bold; border: 1px solid #888888; border-radius: 8px; }")
        tag_row.addWidget(tip_icon_tag, 0, Qt.AlignRight)
        tag_row.addWidget(self.broadcast_tag_input, 1)
        b_l.addLayout(tag_row)

        self.announce_start_btn = QPushButton("Announce the start of the match")
        self.announce_start_btn.setMinimumHeight(40)
        self.announce_start_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.announce_start_btn.clicked.connect(self.announce_start)
        b_l.addWidget(self.announce_start_btn)

        notification_row.addWidget(self.ft_discord_notification)
        notification_row.setAlignment(Qt.AlignCenter)
        b_l.addLayout(notification_row)

        broadcast.setLayout(b_l)
        main.addWidget(broadcast)

        # Players
        players_grid = QGridLayout()
        players_grid.setColumnStretch(0, 1)
        players_grid.setColumnStretch(1, 1)

        def build_player(label_text: str):
            box = QGroupBox(label_text)
            v = QVBoxLayout(); v.setContentsMargins(12, 8, 12, 8)
            name_row = QHBoxLayout()
            name_row.addWidget(QLabel("Name:"))
            name_edit = QLineEdit(); name_edit.setPlaceholderText(label_text)
            name_row.addWidget(name_edit, 1)
            v.addLayout(name_row)

            btn_row = QHBoxLayout()
            add = QPushButton("Add 1 Point"); add.setMinimumHeight(40)
            rem = QPushButton("Remove 1 Point"); rem.setMinimumHeight(40)
            btn_row.addWidget(add); btn_row.addWidget(rem)
            v.addLayout(btn_row)

            box.setLayout(v)
            return box, name_edit, add, rem

        p1_box, self.player1_input, self.add_p1_btn, self.remove_p1_btn = build_player("Player 1")
        p2_box, self.player2_input, self.add_p2_btn, self.remove_p2_btn = build_player("Player 2")
        self.player1_input.textChanged.connect(self.update_scoreboard_label)
        self.player2_input.textChanged.connect(self.update_scoreboard_label)
        self.add_p1_btn.clicked.connect(lambda: self.adjust_score(1, +1))
        self.remove_p1_btn.clicked.connect(lambda: self.adjust_score(1, -1))
        self.add_p2_btn.clicked.connect(lambda: self.adjust_score(2, +1))
        self.remove_p2_btn.clicked.connect(lambda: self.adjust_score(2, -1))

        players_grid.addWidget(p1_box, 0, 0)
        players_grid.addWidget(p2_box, 0, 1)
        main.addLayout(players_grid)

        # scoreboard line fills space
        self.scoreboard_label = QLabel()
        self.scoreboard_label.setAlignment(Qt.AlignCenter)
        self.scoreboard_label.setFont(QFont("Segoe UI", 64, QFont.DemiBold))
        self.scoreboard_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main.addWidget(self.scoreboard_label, 1)

        # bottom actions
        bottom = QHBoxLayout()
        bottom.setStretch(1,1)
        self.reset_score_btn = QPushButton("Reset score")
        self.reset_score_btn.setMinimumHeight(36)
        self.reset_score_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.reset_score_btn.clicked.connect(self.reset_score)
        self.reset_board_btn = QPushButton("Reset board")
        self.reset_board_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.reset_board_btn.setMinimumHeight(36)
        self.reset_board_btn.clicked.connect(self.reset_board)
        bottom.addWidget(self.reset_score_btn)
        bottom.addWidget(self.reset_board_btn)
        main.addLayout(bottom)

        self.update_scoreboard_label()
        self.center_on_screen()

    def center_on_screen(self):
        try:
            screen = self.screen() or QApplication.primaryScreen()
            if not screen:
                return
            avail = screen.availableGeometry()
            frame = self.frameGeometry()
            frame.moveCenter(avail.center())
            self.move(frame.topLeft())
        except Exception as e:
            print(f"[UI] Centering failed: {e}")

    def parse_rounds_to_win(self) -> int:
        txt = (self.rounds_input.text() or "").strip()
        try:
            return int(txt) if txt else 0
        except Exception:
            return 0

    def display_name(self, raw: str, fallback: str) -> str:
        t = (raw or "").strip()
        return t if t else fallback

    def update_scoreboard_label(self):
        p1 = self.display_name(self.player1_input.text(), "Player 1")
        p2 = self.display_name(self.player2_input.text(), "Player 2")
        self.scoreboard_label.setText(f"{p1} : {self.p1_score} – {self.p2_score} : {p2}")

    def announce_start(self):
        msg = (self.start_msg_input.text() or "").strip()
        if not msg:
            QMessageBox.warning(self, "No Message", "Please enter a start announcement message first.")
            return
        self._send_server_message(msg)

    def _send_server_message(self, msg: str):
        msg = self._format_with_tag((msg or "").strip())
        if not msg:
            return
        if not self._ensure_game():
            QMessageBox.warning(self, "Not Connected", "Cannot send message. Chivalry 2 is not connected.")
            return
        try:
            self.game.ServerSay(msg)
        except Exception as e:
            QMessageBox.warning(self, "Game Error", f"Failed to broadcast message to game:\n{str(e)}")


    def adjust_score(self, player: int, delta: int):
        if player == 1:
            self.p1_score = max(0, self.p1_score + delta)
        else:
            self.p2_score = max(0, self.p2_score + delta)

        # Broadcast the current scoreline
        p1 = self.display_name(self.player1_input.text(), "Player 1")
        p2 = self.display_name(self.player2_input.text(), "Player 2")
        self._send_server_message(f"{p1} : {self.p1_score} - {self.p2_score} : {p2}")

        self.update_scoreboard_label()
        self._check_for_winner()


    def _check_for_winner(self):
        rounds = self.parse_rounds_to_win()
        if rounds <= 0:
            return
        winner = None
        if self.p1_score >= rounds:
            winner = 1
        elif self.p2_score >= rounds:
            winner = 2
        if winner is None:
            return
        
        # Announce win if message provided
        result = f"{self.display_name(self.player1_input.text(), "")} wins {self.p1_score} to {self.p2_score}"  if winner == 1 else f"{self.display_name(self.player2_input.text(), "")} wins {self.p2_score} to {self.p1_score}"
        
        discord_result = ""
        discord_result = result
        discord_result += f" against {self.display_name(self.player2_input.text(), "")}." if winner == 1 else f" against {self.display_name(self.player1_input.text(), "")}."
        result += "."
        
        win_msg = (self.win_msg_input.text() or "").strip()
        self._send_server_message(result)
        if win_msg:
            self._send_server_message(win_msg)

        # Send Discord notification
        wehbooks.MessageForAdmin("N/A", "N/A", discord_result, None, "ft")

        # Disable adding further points until reset
        self.add_p1_btn.setEnabled(False)
        self.add_p2_btn.setEnabled(False)

    def reset_score(self):
        self.p1_score = 0
        self.p2_score = 0
        self.add_p1_btn.setEnabled(True)
        self.add_p2_btn.setEnabled(True)
        self.update_scoreboard_label()

    def reset_board(self):
        # Clear inputs and reset scores
        self.rounds_input.clear()
        self.player1_input.clear()
        self.player2_input.clear()
        self.start_msg_input.clear()
        self.win_msg_input.clear()
        self.reset_score()

    def _format_with_tag(self, msg: str) -> str:
        tag = (self.broadcast_tag_input.text() or "").strip()
        if tag:
            t = tag.strip()
            if not (t.startswith("[") and t.endswith("]")):
                t = f"[{t}]"
            return f"{t} {msg}"
        return msg

    def _ensure_game(self) -> bool:
        if self.game:
            return True
        try:
            if check_chivalry_window():
                self.game = GameChivalry()
                self.chivalry_connected = True
                return True
        except Exception:
            pass
        return False

# ---- Persistent last-used parameters (ban/kick/admin/server/add time) ----

def read_localconfig_lines():
    try:
        with open("localconfig", 'r', encoding='utf-8') as f:
            return f.read().splitlines()
    except Exception:
        return []


def write_localconfig_lines(lines):
    try:
        with open("localconfig", 'w', encoding='utf-8') as f:
            for line in lines:
                f.write(line + "\n")
        return True
    except Exception:
        return False


# localconfig layout:
# 0: primary webhook
# 1: secondary webhook
# 2: discord user id
# 3..12: 10 preset lines
# 13: theme
# 14: last ban reason
# 15: last ban duration
# 16: last kick reason
# 17: last admin message
# 18: last server message
# 19: last add-time minutes
PERSIST_INDEX = {
    'last_ban_reason': 14,
    'last_ban_duration': 15,
    'last_kick_reason': 16,
    'last_admin_msg': 17,
    'last_server_msg': 18,
    'last_add_time': 19,
    'console_vk': 26,
}


def get_persisted_value(key: str, default: str = "") -> str:
    lines = read_localconfig_lines()
    idx = PERSIST_INDEX[key]
    if len(lines) <= idx:
        return default
    val = lines[idx]
    return val if val is not None else default


def set_persisted_value(key: str, value: str) -> None:
    lines = read_localconfig_lines()
    # ensure list long enough
    max_idx = max(PERSIST_INDEX.values())
    if len(lines) <= max_idx:
        # pad with empty strings
        lines += [""] * (max_idx + 1 - len(lines))
    lines[PERSIST_INDEX[key]] = value if value is not None else ""
    write_localconfig_lines(lines)


# ---- Admin/Server message presets (3 each) ----
ADMIN_PRESET_BASE_INDEX = 20  # lines[20..22]
SERVER_PRESET_BASE_INDEX = 23  # lines[23..25]
ADMIN_PRESET_COUNT = 3
SERVER_PRESET_COUNT = 3


def _get_text_preset(base_index: int, slot: int) -> str:
    lines = read_localconfig_lines()
    idx = base_index + int(slot)
    if len(lines) <= idx:
        return ""
    return lines[idx]


def _set_text_preset(base_index: int, slot: int, value: str) -> None:
    lines = read_localconfig_lines()
    idx = base_index + int(slot)
    if len(lines) <= idx:
        lines += [""] * (idx + 1 - len(lines))
    lines[idx] = value if value is not None else ""
    write_localconfig_lines(lines)


def get_admin_preset(slot: int) -> str:
    return _get_text_preset(ADMIN_PRESET_BASE_INDEX, slot)


def set_admin_preset(slot: int, value: str) -> None:
    _set_text_preset(ADMIN_PRESET_BASE_INDEX, slot, value)


def get_server_preset(slot: int) -> str:
    return _get_text_preset(SERVER_PRESET_BASE_INDEX, slot)


def set_server_preset(slot: int, value: str) -> None:
    _set_text_preset(SERVER_PRESET_BASE_INDEX, slot, value)


def load_theme_preference():
    """Load theme preference from localconfig file"""
    import os
    localconfig = "localconfig"
    if os.path.exists(localconfig):
        try:
            with open(localconfig, 'r', encoding='utf-8') as f:
                lines = f.read().strip().split('\n')
                # Theme preference is stored on line 14 (index 13)
                if len(lines) >= 14 and lines[13].strip():
                    return lines[13].strip().lower() == 'dark'
        except Exception:
            pass
    return True  # Default to dark theme

def save_theme_preference(is_dark_theme):
    """Save theme preference to localconfig file"""
    import os
    localconfig = "localconfig"

    # Read existing configuration
    lines = ['None'] * 14  # Initialize with 14 lines
    if os.path.exists(localconfig):
        try:
            with open(localconfig, 'r', encoding='utf-8') as f:
                existing_lines = f.read().strip().split('\n')
                for i, line in enumerate(existing_lines):
                    if i < 14:
                        lines[i] = line
        except Exception:
            pass

    # Set theme preference on line 14 (index 13)
    lines[13] = 'dark' if is_dark_theme else 'light'

    # Write back to file
    try:
        with open(localconfig, 'w', encoding='utf-8') as f:
            for line in lines:
                f.write(f"{line}\n")
    except Exception as e:
        print(f"[THEME] Failed to save theme preference: {e}")

def apply_dark_theme(app):
    """Apply a dark theme to the entire application"""
    dark_stylesheet = """
    /* Main application styling */
    QApplication {
        background-color: #2b2b2b;
        color: #ffffff;
    }

    /* Main windows and dialogs */
    QWidget {
        background-color: #2b2b2b;
        color: #ffffff;
        selection-background-color: #3d5afe;
    }

    /* Group boxes */
    QGroupBox {
        background-color: #353535;
        border: 2px solid #555555;
        border-radius: 8px;
        margin-top: 1ex;
        padding-top: 10px;
        font-weight: bold;
        color: #ffffff;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 8px 0 8px;
        color: #ffffff;
        background-color: #353535;
    }

    /* Buttons */
    QPushButton {
        background-color: #404040;
        border: 1px solid #606060;
        border-radius: 4px;
        padding: 8px 16px;
        color: #ffffff;
        font-weight: bold;
        min-height: 20px;
    }

    QPushButton:hover {
        background-color: #505050;
        border: 1px solid #707070;
    }

    QPushButton:pressed {
        background-color: #303030;
        border: 1px solid #505050;
    }

    QPushButton:disabled {
        background-color: #2a2a2a;
        color: #666666;
        border: 1px solid #404040;
    }

    /* Input fields */
    QLineEdit {
        background-color: #404040;
        border: 2px solid #606060;
        border-radius: 4px;
        padding: 8px;
        color: #ffffff;
        selection-background-color: #3d5afe;
    }

    QLineEdit:focus {
        border: 2px solid #3d5afe;
    }

    /* Labels */
    QLabel {
        color: #ffffff;
        background-color: transparent;
    }

    /* List widgets */
    QListWidget {
        background-color: #353535;
        border: 1px solid #606060;
        border-radius: 4px;
        color: #ffffff;
        selection-background-color: #3d5afe;
        alternate-background-color: #404040;
    }

    QListWidget::item {
        padding: 8px;
        border-bottom: 1px solid #505050;
    }

    QListWidget::item:selected {
        background-color: #3d5afe;
        color: #ffffff;
    }

    QListWidget::item:hover {
        background-color: #454545;
    }

    /* Progress bars */
    QProgressBar {
        background-color: #404040;
        border: 1px solid #606060;
        border-radius: 4px;
        text-align: center;
        color: #ffffff;
    }

    QProgressBar::chunk {
        background-color: #3d5afe;
        border-radius: 3px;
    }

    /* Dialogs */
    QDialog {
        background-color: #2b2b2b;
        color: #ffffff;
    }

    /* Message boxes */
    QMessageBox {
        background-color: #2b2b2b;
        color: #ffffff;
    }

    QMessageBox QPushButton {
        min-width: 80px;
        min-height: 25px;
    }

    /* Input dialogs */
    QInputDialog {
        background-color: #2b2b2b;
        color: #ffffff;
    }

    /* Scroll bars */
    QScrollBar:vertical {
        background-color: #404040;
        width: 12px;
        border-radius: 6px;
    }

    QScrollBar::handle:vertical {
        background-color: #606060;
        border-radius: 6px;
        min-height: 20px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: #707070;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        border: none;
        background: none;
    }
    """

    app.setStyleSheet(dark_stylesheet)

def apply_light_theme(app):
    """Apply a light theme to the entire application"""
    light_stylesheet = """
    /* Main application styling */
    QApplication {
        background-color: #f5f5f5;
        color: #333333;
    }

    /* Main windows and dialogs */
    QWidget {
        background-color: #f5f5f5;
        color: #333333;
        selection-background-color: #3d5afe;
    }

    /* Group boxes */
    QGroupBox {
        background-color: #ffffff;
        border: 2px solid #cccccc;
        border-radius: 8px;
        margin-top: 1ex;
        padding-top: 10px;
        font-weight: bold;
        color: #333333;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 8px 0 8px;
        color: #333333;
        background-color: #ffffff;
    }

    /* Buttons */
    QPushButton {
        background-color: #ffffff;
        border: 1px solid #cccccc;
        border-radius: 4px;
        padding: 8px 16px;
        color: #333333;
        font-weight: bold;
        min-height: 20px;
    }

    QPushButton:hover {
        background-color: #f0f0f0;
        border: 1px solid #999999;
    }

    QPushButton:pressed {
        background-color: #e0e0e0;
        border: 1px solid #888888;
    }

    QPushButton:disabled {
        background-color: #f8f8f8;
        color: #999999;
        border: 1px solid #dddddd;
    }

    /* Input fields */
    QLineEdit {
        background-color: #ffffff;
        border: 2px solid #cccccc;
        border-radius: 4px;
        padding: 8px;
        color: #333333;
        selection-background-color: #3d5afe;
    }

    QLineEdit:focus {
        border: 2px solid #3d5afe;
    }

    /* Labels */
    QLabel {
        color: #333333;
        background-color: transparent;
    }

    /* List widgets */
    QListWidget {
        background-color: #ffffff;
        border: 1px solid #cccccc;
        border-radius: 4px;
        color: #333333;
        selection-background-color: #3d5afe;
        alternate-background-color: #f8f8f8;
    }

    QListWidget::item {
        padding: 8px;
        border-bottom: 1px solid #eeeeee;
    }

    QListWidget::item:selected {
        background-color: #3d5afe;
        color: #ffffff;
    }

    QListWidget::item:hover {
        background-color: #f0f0f0;
    }

    /* Progress bars */
    QProgressBar {
        background-color: #ffffff;
        border: 1px solid #cccccc;
        border-radius: 4px;
        text-align: center;
        color: #333333;
    }

    QProgressBar::chunk {
        background-color: #3d5afe;
        border-radius: 3px;
    }

    /* Dialogs */
    QDialog {
        background-color: #f5f5f5;
        color: #333333;
    }

    /* Message boxes */
    QMessageBox {
        background-color: #f5f5f5;
        color: #333333;
    }

    QMessageBox QPushButton {
        min-width: 80px;
        min-height: 25px;
    }

    /* Input dialogs */
    QInputDialog {
        background-color: #f5f5f5;
        color: #333333;
    }

    /* Scroll bars */
    QScrollBar:vertical {
        background-color: #f0f0f0;
        width: 12px;
        border-radius: 6px;
    }

    QScrollBar::handle:vertical {
        background-color: #cccccc;
        border-radius: 6px;
        min-height: 20px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: #999999;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        border: none;
        background: none;
    }
    """

    app.setStyleSheet(light_stylesheet)

def main():
    app = QApplication(sys.argv)
    # Install global tooltip filter with 0.5s delay
    app._instant_tt = InstantToolTipFilter(delay_ms=500)
    app.installEventFilter(app._instant_tt)


    # Load and apply saved theme preference
    is_dark_theme = load_theme_preference()
    if is_dark_theme:
        apply_dark_theme(app)
    else:
        apply_light_theme(app)

    # Check if we should wait for Chivalry 2
    if "--no-wait" not in sys.argv and not check_chivalry_window():
        waiting_dialog = ChivalryWaitingDialog()
        waiting_dialog.exec_()

    # Initialize Discord webhooks at startup
    import core.wehbooks as wehbooks
    webhook_initialized = wehbooks.initialize_webhook()
    if webhook_initialized:
        print("[STARTUP] Discord webhook(s) initialized successfully")
    else:
        print("[STARTUP] Discord webhooks not configured or failed to initialize")

    window = AdminDashboard()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
