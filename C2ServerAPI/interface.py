import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QDialog,
    QFormLayout, QLineEdit, QDialogButtonBox, QMessageBox, QListWidget, QHBoxLayout,
    QGroupBox, QSpacerItem, QSizePolicy, QInputDialog, QProgressBar, QCheckBox, QToolTip, QGridLayout,
    QScrollArea, QFrame, QListWidgetItem, QStyledItemDelegate, QStyle
)
from PyQt5.QtGui import QFont, QIntValidator, QCursor, QDesktopServices, QColor, QBrush
from PyQt5.QtCore import Qt, QTimer, QObject, QEvent, QUrl, pyqtSignal

import pyperclip
import os
import json
import datetime
import win32gui
import re


from core.C2ServerAPIExample import GameChivalry
import core.wehbooks as wehbooks


class InstantToolTipFilter(QObject):
    """Global event filter that shows tooltips after a small delay."""
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
                return True
            if et in (QEvent.Leave, QEvent.MouseButtonPress):
                QToolTip.hideText()
                self._cancel()
                return False
            if et == QEvent.MouseMove:
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
            if not w.toolTip():
                return
            pos = QCursor.pos()
            if not w.rect().contains(w.mapFromGlobal(pos)):
                return
            QToolTip.showText(pos, w.toolTip(), w)
        except Exception:
            pass


def check_chivalry_window():
    """Check if Chivalry 2 window is available"""
    try:
        hwnd = win32gui.FindWindow(None, "Chivalry 2  ")
        return hwnd != 0
    except Exception:
        return False

class ChivalryWaitingDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Waiting for Chivalry 2")
        self.setFixedSize(500, 350)

        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(15, 15, 15, 15)

        title = QLabel("Waiting for Chivalry 2")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setContentsMargins(0, 0, 0, 5)
        layout.addWidget(title)

        instructions = QLabel()
        instructions.setText(
            "Please launch your Chivalry 2 game.\n\n"
            "The admin tool will automatically continue once the game is detected."
        )
        instructions.setWordWrap(True)
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setContentsMargins(10, 5, 10, 5)
        instructions.setMinimumHeight(80)
        instructions.setMaximumHeight(80)
        instructions.setSizePolicy(instructions.sizePolicy().horizontalPolicy(), instructions.sizePolicy().Fixed)
        layout.addWidget(instructions)

        self.status_label = QLabel("Searching for Chivalry 2 window...")
        self.status_label.setAlignment(Qt.AlignCenter)

        font = QFont("Segoe UI", 12)
        font.setBold(True)
        self.status_label.setFont(font)

        self.status_label.setContentsMargins(10, 5, 10, 5)

        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setMinimumHeight(25)
        self.progress_bar.setStyleSheet("margin: 10px 0px;")
        layout.addWidget(self.progress_bar)

        layout.addSpacing(5)

        button_layout = QHBoxLayout()

        self.theme_button = QPushButton("Dark Mode")
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setMinimumHeight(35)
        button_layout.addWidget(self.theme_button)

        skip_button = QPushButton("Skip Waiting (Continue Anyway)")
        skip_button.clicked.connect(self.accept)
        skip_button.setMinimumHeight(35)
        button_layout.addWidget(skip_button)

        layout.addLayout(button_layout)

        launch_layout = QHBoxLayout()

        steam_button = QPushButton("Launch via Steam")
        steam_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("steam://rungameid/1824220")))
        steam_button.setMinimumHeight(35)
        launch_layout.addWidget(steam_button)

        epic_button = QPushButton("Launch via Epic Games")
        epic_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("com.epicgames.launcher://apps/bd46d4ce259349e5bd8b3ded20274737%3A4c4a6c0767304c9d830f3f36f2b29018%3APeppermint?action=launch&silent=true")))
        epic_button.setMinimumHeight(35)
        launch_layout.addWidget(epic_button)

        xbox_button = QPushButton("Launch via Xbox")
        xbox_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("msxbox://game/?productId=9N7CJX93ZGWN")))
        xbox_button.setMinimumHeight(35)
        launch_layout.addWidget(xbox_button)

        layout.addLayout(launch_layout)

        self.setLayout(layout)

        layout.activate()
        self.adjustSize()

        self.timer = QTimer()
        self.timer.timeout.connect(self.check_window)
        self.timer.start(1000)

        self.update_theme_button()

    def closeEvent(self, event):
        """Handle window close button"""
        self.timer.stop()
        event.ignore()
        self.reject()

    def reject(self):
        """Handle dialog rejection"""
        self.timer.stop()
        super().reject()

    def toggle_theme(self):
        """Toggle between dark and light theme"""
        app = QApplication.instance()
        current_is_dark = load_theme_preference()
        new_is_dark = not current_is_dark

        if new_is_dark:
            apply_dark_theme(app)
        else:
            apply_light_theme(app)

        save_theme_preference(new_is_dark)
        self.update_theme_button()

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
            QTimer.singleShot(1500, self.accept)
        else:
            self.status_label.setText(f"Searching for Chivalry 2 window...")

def parse_player_list_from_clipboard(text: str = None):
    """Parse players from provided clipboard text or current clipboard."""
    if text is None:
        try:
            text = pyperclip.paste()
        except Exception:
            text = ""
    lines = (text or "").strip().splitlines()

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
        if name.lower() == 'name' or playfab_id.lower().startswith('playfab'):
            continue
        if len(playfab_id) < 12:
            continue
        if playfab_id in seen_ids:
            continue
        seen_ids.add(playfab_id)
        players.append((name, playfab_id))

    return players


def _make_tip_badge(tooltip_text: str, parent=None) -> QLabel:
    """Standard '?' tooltip badge used across the dashboard.

    Uses palette roles so it follows the active theme without
    per-theme restyling on toggle.
    """
    lbl = QLabel("?", parent)
    lbl.setToolTip(tooltip_text)
    lbl.setFixedSize(20, 20)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet(
        "QLabel { color: #888888; font-weight: bold;"
        " border: 1px solid #888888; border-radius: 10px; }"
    )
    return lbl


def _make_preset_column(slot_idx: int, on_load, on_save, on_clear) -> QVBoxLayout:
    """Build one Load/Save/Clear stack for a numbered preset slot.

    Returns a QVBoxLayout with the three buttons attached as
    _btn_load / _btn_save / _btn_clear so the caller can keep
    references for later restyling.
    """
    col = QVBoxLayout()
    col.setSpacing(6)
    col.addWidget(QLabel(f"Slot {slot_idx}"), 0)

    btn_load = QPushButton("Load")
    btn_load.setMinimumWidth(90)
    btn_load.clicked.connect(lambda _, s=slot_idx: on_load(s))
    col.addWidget(btn_load)

    btn_save = QPushButton("Save / Overwrite")
    btn_save.setMinimumWidth(90)
    btn_save.clicked.connect(lambda _, s=slot_idx: on_save(s))
    col.addWidget(btn_save)

    btn_clear = QPushButton("Clear")
    btn_clear.setMinimumWidth(90)
    btn_clear.clicked.connect(lambda _, s=slot_idx: on_clear(s))
    col.addWidget(btn_clear)

    col._btn_load = btn_load
    col._btn_save = btn_save
    col._btn_clear = btn_clear
    return col


class _SanctionedRowDelegate(QStyledItemDelegate):
    """Honors per-item background / foreground brushes set via
    QListWidgetItem.setBackground / setForeground, even when a global
    stylesheet targets QListWidget::item.

    Qt 5 suppresses data-role colours as soon as ANY ::item rule exists
    in a stylesheet, and its default paint path also overrides them on
    hover/selection with the theme's :hover / :selected colours. This
    delegate paints the background manually, overlays a translucent
    black to darken on hover/selection (theme-independent), strips
    those state flags from the option so super() can't repaint over
    our work, and forces the foreground through option.palette.
    """
    def paint(self, painter, option, index):
        bg = index.data(Qt.BackgroundRole)
        fg = index.data(Qt.ForegroundRole)

        if isinstance(bg, QBrush) and bg.style() != Qt.NoBrush:
            painter.fillRect(option.rect, bg)
            if option.state & QStyle.State_Selected:
                painter.fillRect(option.rect, QColor(0, 0, 0, 70))
            elif option.state & QStyle.State_MouseOver:
                painter.fillRect(option.rect, QColor(0, 0, 0, 40))
            # Strip hover/selection flags so the default paint path
            # can't redraw the theme's blue selection or grey hover
            # on top of our overlay.
            option.state &= ~QStyle.State_Selected
            option.state &= ~QStyle.State_MouseOver
            option.backgroundBrush = QBrush()

        if isinstance(fg, QBrush):
            option.palette.setBrush(option.palette.Text, fg)
            option.palette.setBrush(option.palette.HighlightedText, fg)

        super().paint(painter, option, index)


def _colored_button_qss(color: str) -> str:
    """QSS for a solid coloured QPushButton with matching hover/pressed shades.

    `color` is a #rrggbb hex. Hover darkens ~15%, pressed ~30%.
    Avoids the #rrggbbaa (alpha) trick which renders semi-transparent
    and composites oddly against the parent dialog in Qt 5, and ensures
    hover doesn't fall back to the theme's generic grey.
    """
    def _shade(factor: float) -> str:
        h = color.lstrip('#')
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"
    return (
        f"QPushButton {{ background-color:{color}; color:white;"
        f" font-weight:bold; border-radius:4px; }}"
        f"QPushButton:hover   {{ background-color:{_shade(0.85)}; }}"
        f"QPushButton:pressed {{ background-color:{_shade(0.70)}; }}"
    )


def _populated_preset_qss(is_dark_theme: bool) -> str:
    """QSS applied to Load preset buttons whose slot has stored content.

    Subtle green tint with a matching hover shade — ensures hover doesn't
    fall back to the theme's generic grey, which looked wrong against
    the green normal state.
    """
    if is_dark_theme:
        return (
            "QPushButton { background-color: #2d5a2d; color: #ffffff; }"
            "QPushButton:hover { background-color: #3a6f3a; }"
        )
    return (
        "QPushButton { background-color: #e6ffe6; color: #333333; }"
        "QPushButton:hover { background-color: #d3f0d3; }"
    )


class ActionForm(QDialog):
    # RAM-only session memory for the "Notify in-game" checkbox.
    # Persists for the lifetime of the process but is NOT written to
    # localconfig — intentional, since the user wants the preference to
    # reset between launches.
    _notify_in_game_last = True

    @staticmethod
    def _remember_notify_in_game(checked: bool) -> None:
        ActionForm._notify_in_game_last = bool(checked)

    def __init__(self, action_name, player_id, player_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{action_name} Player")
        self.resize(450, 350)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModal)

        self.game = None
        try:
            self.game = GameChivalry()
        except Exception as e:
            print(f"[ACTION FORM] Could not connect to Chivalry 2: {e}")

        main_layout = QVBoxLayout()

        form_layout = QFormLayout()
        self.player_id_input = QLineEdit(player_id)
        self.player_id_input.setReadOnly(True)
        self.player_name = QLineEdit(player_name)
        self.player_name.setReadOnly(True)
        form_layout.addRow("Player ID:", self.player_id_input)
        form_layout.addRow("Player Name:", self.player_name)
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

        if action_name.lower() == "ban":
            quick_preset_group = QGroupBox("Quick Presets")
            quick_preset_layout = QHBoxLayout()

            btn_ffa_24h = QPushButton("FFA 24h")
            btn_ffa_24h.clicked.connect(self.apply_ffa_24h_preset)
            btn_ffa_24h.setStyleSheet(_colored_button_qss('#3498db'))
            quick_preset_layout.addWidget(btn_ffa_24h)

            btn_ffa_perma = QPushButton("FFA Permaban")
            btn_ffa_perma.clicked.connect(self.apply_ffa_perma_preset)
            btn_ffa_perma.setStyleSheet(_colored_button_qss('#e67e22'))
            quick_preset_layout.addWidget(btn_ffa_perma)

            btn_cheating = QPushButton("Cheating")
            btn_cheating.clicked.connect(self.apply_cheating_preset)
            btn_cheating.setStyleSheet(_colored_button_qss('#e74c3c'))
            quick_preset_layout.addWidget(btn_cheating)

            quick_preset_group.setLayout(quick_preset_layout)
            main_layout.addWidget(quick_preset_group)

        preset_group = QGroupBox("Reason Presets")
        preset_layout = QVBoxLayout()

        is_ban = (action_name.lower() == "ban")
        self.preset_slots = list(range(0, 5)) if is_ban else list(range(5, 10))

        preset_layout.addWidget(
            _make_tip_badge("Hover a Load button to preview the saved reason"
                            + (" and duration" if is_ban else "")),
            0, Qt.AlignRight,
        )

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

        self.notify_in_game = QCheckBox("Notify in-game")
        self.notify_in_game.setChecked(ActionForm._notify_in_game_last)
        self.notify_in_game.toggled.connect(ActionForm._remember_notify_in_game)
        main_layout.addWidget(self.notify_in_game)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.perform_action)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        parent = self.parent()
        if parent and isinstance(parent, AdminDashboard):
            parent.admin_message_input.setText(get_persisted_value('last_admin_msg', ""))
            parent.server_message_input.setText(get_persisted_value('last_server_msg', ""))

        self.action_name = action_name
        self.setLayout(main_layout)

        self.update_preset_tooltips()

    def load_preset(self, slot):
        """Load a preset into the inputs"""
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
            self.reason_input.setText(reason_val)
            if self.time_input is not None and duration_val is not None:
                self.time_input.setText(duration_val)
            QMessageBox.information(self, "Preset Loaded", f"Preset {slot} loaded successfully!")
        else:
            QMessageBox.warning(self, "No Preset", f"No preset found in slot {slot}.")

    def apply_ffa_24h_preset(self):
        """Execute FFA 24h ban"""
        self.execute_quick_preset("FFA", 24)

    def apply_ffa_perma_preset(self):
        """Execute FFA permaban"""
        self.execute_quick_preset("FFA", 999999)

    def apply_cheating_preset(self):
        """Execute Cheating permaban"""
        self.execute_quick_preset("Cheating", 999999)

    def execute_quick_preset(self, reason, duration_hours):
        """Execute a quick preset"""
        saved_reason = self.reason_input.text()
        saved_duration = self.time_input.text() if self.time_input is not None else None

        self.reason_input.setText(reason)
        if self.time_input is not None:
            self.time_input.setText(str(duration_hours))

        self.perform_action()

        self.reason_input.setText(saved_reason)
        if self.time_input is not None and saved_duration is not None:
            self.time_input.setText(saved_duration)

    def save_preset(self, slot):
        """Save the current reason to a preset slot"""
        reason = self.reason_input.text().strip()
        if not reason:
            QMessageBox.warning(self, "Empty Reason", "Please enter a reason before saving to preset.")
            return
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
        """Update tooltips for load buttons to show preset contents"""
        from core.guiServer import Chivalry
        chiv = Chivalry()
        presets = chiv.GetAllPresets()

        is_dark_theme = load_theme_preference()

        for idx, btn in enumerate(self.load_buttons):
            slot = self.preset_slots[idx]
            preset_text = presets.get(str(slot), "")
            if preset_text:
                reason_val, duration_val = preset_text.split('|||', 1) if '|||' in preset_text else (preset_text, "")
                reason_val = reason_val.strip()
                duration_val = duration_val.strip()
                display_reason = reason_val[:50] + "..." if len(reason_val) > 50 else reason_val
                tooltip_text = f"Slot {idx}: {display_reason}"
                if duration_val:
                    tooltip_text += f"  |  duration: {duration_val}"
                btn.setToolTip(tooltip_text)

                btn.setStyleSheet(_populated_preset_qss(is_dark_theme))
            else:
                btn.setToolTip(f"Slot {idx}: Empty")
                btn.setStyleSheet("")

    def clear_preset(self, slot):
        """Clear a preset slot"""
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
            print(f"[BAN] Player ID={player_id}, Reason={reason}, Time={time_hour} hours")

            action_executed = False
            if hasattr(self.game, 'banbyid'):
                try:
                    self.game.banbyid(player_id, time_hour, reason)
                    action_executed = True
                    if self.notify_in_game.isChecked():
                        self.game.AdminSay(f"{player_name} has been banned from the server.")
                except Exception as e:
                    QMessageBox.warning(self, "Game Connection Error", f"Could not execute ban command:\n{str(e)}")

            if action_executed:
                set_persisted_value('last_ban_reason', reason)
                set_persisted_value('last_ban_duration', str(time_hour))
                wehbooks.MessageForAdmin(player_id, player_name, reason, time_hour, "ban")

        elif self.action_name.lower() == "warn":
            print(f"[WARN] Player ID={player_id}, Reason={reason}")
            # Warning is Discord-only — no in-game command needed
            wehbooks.MessageForAdmin(player_id, player_name, reason, None, "warn")
            set_persisted_value('last_kick_reason', reason)

        else:
            print(f"[KICK] Player ID={player_id}, Reason={reason}")

            action_executed = False
            if hasattr(self.game, 'kickbyid'):
                try:
                    self.game.kickbyid(player_id, reason)
                    action_executed = True
                    if self.notify_in_game.isChecked():
                        self.game.AdminSay(f"{player_name} has been kicked from the server.")
                except Exception as e:
                    QMessageBox.warning(self, "Game Connection Error", f"Could not execute kick command:\n{str(e)}")

            if action_executed:
                set_persisted_value('last_kick_reason', reason)
                wehbooks.MessageForAdmin(player_id, player_name, reason, None, "kick")

        self.accept()

def _load_all_sanctions() -> list:
    """Return every record from discordlogshistory, oldest-first."""
    records = []
    if not os.path.exists(DISCORD_LOG_FILE):
        return records
    try:
        with open(DISCORD_LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass
    return records


def _load_sanctions_for_player(player_id: str) -> list:
    """Return all discordlogshistory records whose PlayFabID matches player_id."""
    records = []
    if not os.path.exists(DISCORD_LOG_FILE):
        return records
    try:
        with open(DISCORD_LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    if record.get('PlayFabID', '').upper() == player_id.upper():
                        records.append(record)
                except Exception:
                    pass
    except Exception:
        pass
    return records


def _compute_all_player_statuses() -> dict:
    """Single-pass scan of discordlogshistory.

    Returns {playfab_id_upper: 'banned' | 'cautioned'} for players whose
    most severe current status is non-None. 'banned' wins over 'cautioned'.
    """
    now           = datetime.datetime.now(datetime.timezone.utc)
    one_month_ago = now - datetime.timedelta(days=30)
    banned, cautioned = set(), set()

    for record in _load_all_sanctions():
        pid = record.get('PlayFabID', '').upper()
        if not pid:
            continue
        action = record.get('action', '')
        ts_raw = record.get('timestamp', '')
        if not ts_raw:
            continue
        try:
            ts = datetime.datetime.fromisoformat(ts_raw.replace('Z', '+00:00'))
        except Exception:
            continue

        if action == 'ban':
            dur = record.get('Duration', '')
            if dur:
                try:
                    if ts + datetime.timedelta(hours=float(dur.rstrip('h'))) > now:
                        banned.add(pid)
                except Exception:
                    pass
        elif action in ('kick', 'warn') and ts >= one_month_ago:
            cautioned.add(pid)

    return {**{p: 'cautioned' for p in cautioned}, **{p: 'banned' for p in banned}}


class _ThemeBus(QObject):
    """Broadcasts theme toggles to live theme-aware widgets.

    Subscribers connect to `theme_changed` on construction and
    disconnect on destruction. Used by sanction cards so they
    re-tint without needing to be rebuilt.
    """
    theme_changed = pyqtSignal(bool)  # True = dark, False = light


_theme_bus = _ThemeBus()


def _build_sanction_card(record: dict, is_dark: bool = None,
                         embed_playfabid: bool = False) -> QFrame:
    """Card representing one sanction record.

    Visual language matches the app's QGroupBox containers: themed
    base background, subtle border, 8px radius. The action type is
    communicated through a small coloured badge in the header, with
    the username promoted alongside it so the card scans at a glance.

    Pass `is_dark` to avoid repeated theme-preference reads when
    building many cards in a row. Pass `embed_playfabid=True` to
    include a PlayFabID row inside the card - used by the sanction
    search dialog where cards appear without a per-player header.

    Live theme updates: each card subscribes to `_theme_bus.theme_changed`
    and re-applies its themed stylesheet in place. The subscription is
    torn down when the frame is destroyed, so closed dialogs don't leak.
    """
    if is_dark is None:
        is_dark = load_theme_preference()

    action   = record.get('action',   '')
    duration = record.get('Duration', '')
    reason   = record.get('Reason',   '')
    username = record.get('Username', '')

    # Action -> label + badge colour. Legacy records without an 'action'
    # key are inferred from which fields are populated.
    if action == 'ban'   or (not action and duration):
        action_label, accent = 'BAN',     '#e74c3c'
    elif action == 'kick' or (not action and reason and username):
        action_label, accent = 'KICK',    '#f39c12'
    elif action == 'warn':
        action_label, accent = 'WARNING', '#d4ac0d'
    elif action == 'unban' or (not action and not reason):
        action_label, accent = 'UNBAN',   '#2ecc71'
    else:
        action_label, accent = (action.upper() or '?'), '#95a5a6'

    ts_raw = record.get('timestamp', '')
    try:
        ts = ts_raw[:10] + '  ' + ts_raw[11:16] + ' UTC'
    except Exception:
        ts = ts_raw

    frame = QFrame()
    frame.setObjectName("SanctionCard")

    layout = QVBoxLayout(frame)
    layout.setContentsMargins(12, 9, 12, 9)
    layout.setSpacing(5)

    # -- Header: badge + username + timestamp -----------------------------
    header = QHBoxLayout()
    header.setSpacing(8)

    badge = QLabel(action_label)
    badge.setFont(QFont('Segoe UI', 8, QFont.Bold))
    badge.setStyleSheet(
        f"QLabel {{ color: white; background-color: {accent};"
        f" border-radius: 3px; padding: 2px 8px; }}"
    )
    header.addWidget(badge)

    if username:
        lbl_user = QLabel(username)
        lbl_user.setFont(QFont('Segoe UI', 9, QFont.Bold))
        lbl_user.setTextInteractionFlags(Qt.TextSelectableByMouse)
        header.addWidget(lbl_user)

    header.addStretch()
    lbl_ts = QLabel(ts)
    lbl_ts.setFont(QFont('Segoe UI', 8))
    header.addWidget(lbl_ts)
    layout.addLayout(header)

    # -- Theme-dependent styling (re-applicable) --------------------------
    def _apply_theme(dark: bool):
        if dark:
            bg, border, muted, key_col = '#353535', '#555555', '#aaaaaa', '#b5b5b5'
        else:
            bg, border, muted, key_col = '#ffffff', '#cccccc', '#888888', '#777777'
        frame.setStyleSheet(f"""
            QFrame#SanctionCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QFrame#SanctionCard QLabel {{
                background-color: transparent;
                border: none;
            }}
            QFrame#SanctionCard QLabel[role="key"] {{
                color: {key_col};
            }}
        """)
        lbl_ts.setStyleSheet(f"color: {muted}; font-size: 8pt;")

    _apply_theme(is_dark)
    _theme_bus.theme_changed.connect(_apply_theme)

    # Closures hold strong refs through the signal connection; release
    # them when the frame dies so sanction dialogs don't leak cards.
    def _cleanup():
        try:
            _theme_bus.theme_changed.disconnect(_apply_theme)
        except (TypeError, RuntimeError):
            pass
    frame.destroyed.connect(_cleanup)

    def _add_row(label_text: str, value: str):
        if not value:
            return
        row = QHBoxLayout()
        row.setSpacing(8)
        key = QLabel(label_text.upper())
        key.setProperty("role", "key")
        key.setFont(QFont('Segoe UI', 7, QFont.Bold))
        key.setFixedWidth(66)
        key.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        val = QLabel(value)
        val.setWordWrap(True)
        val.setFont(QFont('Segoe UI', 8))
        val.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row.addWidget(key)
        row.addWidget(val, 1)
        layout.addLayout(row)

    # Username is rendered in the header; no longer a body row.
    if embed_playfabid:
        _add_row('PlayFabID', record.get('PlayFabID', ''))
    _add_row('Reason',   reason)
    _add_row('Duration', duration)

    mod_id = record.get('ModeratorID', '')
    if mod_id:
        mod_name = record.get('ModeratorName', '')
        _add_row('Moderator', f'{mod_id} ({mod_name})' if mod_name else mod_id)

    return frame


class PlayerActionDialog(QDialog):
    def __init__(self, player_id, player_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Actions for {player_name} (ID: {player_id})")
        self.resize(820, 460)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModal)
        self.player_id = player_id
        self.player_name = player_name

        root = QHBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(12, 12, 12, 12)

        # ── Left: Actions group ───────────────────────────────────────
        actions_group = QGroupBox("Actions")
        left = QVBoxLayout(actions_group)
        left.setSpacing(6)
        left.setContentsMargins(12, 10, 12, 10)

        label = QLabel(
            f"<div align='center'><b>{player_name}</b>"
            f"<br/><small style='color:gray;'>{player_id}</small></div>"
        )
        label.setWordWrap(True)
        left.addWidget(label)
        left.addSpacing(4)

        def _action_btn(text, color, slot):
            b = QPushButton(text)
            b.setMinimumHeight(38)
            b.setStyleSheet(_colored_button_qss(color))
            b.clicked.connect(slot)
            return b

        left.addWidget(_action_btn("Ban",                    '#e74c3c', self.ban_player))
        left.addWidget(_action_btn("Kick",                   '#f39c12', self.kick_player))
        left.addWidget(_action_btn("Warn",                   '#d4ac0d', self.warn_player))
        left.addWidget(_action_btn("Chivalry2Stats Profile", '#3498db', self.open_player_profile))
        left.addWidget(_action_btn("Copy PlayFabID",         '#2ecc71', self.copy_player_id))
        left.addStretch()

        actions_group.setFixedWidth(230)
        root.addWidget(actions_group)

        # ── Right: sanction history ──────────────────────────────────
        sanctions = _load_sanctions_for_player(player_id)
        now       = datetime.datetime.now(datetime.timezone.utc)
        month_ago = now - datetime.timedelta(days=30)

        # Most-recent warn, only kept if issued within 30 days
        pinned_warning = None
        for record in reversed(sanctions):
            if record.get('action') == 'warn':
                try:
                    ts = datetime.datetime.fromisoformat(
                        record['timestamp'].replace('Z', '+00:00'))
                    if ts >= month_ago:
                        pinned_warning = record
                except Exception:
                    pass
                break

        right_col = QVBoxLayout()
        right_col.setSpacing(8)

        is_dark = load_theme_preference()

        if pinned_warning:
            pin_group = QGroupBox("Active Warning (within the last 30 days)")
            pin_layout = QVBoxLayout(pin_group)
            pin_layout.setContentsMargins(10, 8, 10, 8)
            pin_layout.addWidget(_build_sanction_card(pinned_warning, is_dark))
            right_col.addWidget(pin_group)

        count = len(sanctions)
        history_group = QGroupBox(
            f"Sanction History — {count} record{'s' if count != 1 else ''}"
        )
        hist_layout = QVBoxLayout(history_group)
        hist_layout.setContentsMargins(8, 8, 8, 8)

        pinned_id  = pinned_warning.get('id') if pinned_warning else None
        scrollable = [r for r in reversed(sanctions) if r.get('id') != pinned_id]

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        scroll_content = QWidget()
        scroll_layout  = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(6)
        scroll_layout.setContentsMargins(2, 2, 2, 2)

        if scrollable:
            for record in scrollable:
                scroll_layout.addWidget(_build_sanction_card(record, is_dark))
        elif not pinned_warning:
            empty = QLabel("No sanctions found in log history.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: gray; font-style: italic; padding: 24px;")
            scroll_layout.addWidget(empty)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        hist_layout.addWidget(scroll)

        right_col.addWidget(history_group, 1)
        root.addLayout(right_col, 1)

    def copy_player_id(self):
        pyperclip.copy(self.player_id)
        QMessageBox.information(self, "PlayFabID Copied", f"Player's PlayFabID {self.player_id} copied to clipboard.")

    def ban_player(self):
        form = ActionForm("Ban", self.player_id, self.player_name, parent=self)
        form.exec_()

    def kick_player(self):
        form = ActionForm("Kick", self.player_id, self.player_name, parent=self)
        form.exec_()

    def warn_player(self):
        form = ActionForm("Warn", self.player_id, self.player_name, parent=self)
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

        self.game = None
        try:
            self.game = GameChivalry()
        except Exception as e:
            print(f"[PLAYERS WINDOW] Could not connect to Chivalry 2: {e}")
        main_layout = QVBoxLayout()

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
        self.player_list.setItemDelegate(_SanctionedRowDelegate(self.player_list))
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

        QTimer.singleShot(1500, self._parse_player_list_from_clipboard)

    def _parse_player_list_from_clipboard(self):
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
        white = QBrush(QColor('white'))
        statuses = _compute_all_player_statuses()
        for name, pid in self.filtered_players:
            item = QListWidgetItem(f"{name} - {pid}")
            status = statuses.get(pid.upper())
            if status == 'banned':
                item.setBackground(QBrush(QColor('#c0392b')))
                item.setForeground(white)
            elif status == 'cautioned':
                item.setBackground(QBrush(QColor('#d35400')))
                item.setForeground(white)
            self.player_list.addItem(item)

    def _update_info_from_text(self, text: str):

        lines = (text or "").strip().splitlines()
        server_name = "-"
        if lines:
            header = lines[0].strip()
            header_no_ip = re.sub(r"\s*(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\s*$", "", header)

            m = re.match(r"^\s*ServerName\s*-\s*(.+?)\s{2,}.*$", header_no_ip)
            if m:
                server_name = m.group(1).strip()
            else:
                if header_no_ip.lower().startswith("servername") and '-' in header_no_ip:
                    try:
                        after_dash = header_no_ip.split('-', 1)[1].strip()
                        server_name = after_dash.split('  ')[0].strip() or server_name
                    except Exception:
                        pass
                elif ' - ' in header_no_ip:
                    try:
                        server_name = header_no_ip.split(' - ', 1)[1].split('  ')[0].strip() or server_name
                    except Exception:
                        pass
            server_name = re.sub(r"\s*(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\s*$", "", server_name)
            
        data_lines = lines[2:] if len(lines) >= 3 else []
        player_rows = [ln for ln in data_lines if " - " in ln]
        count = len(player_rows)
        self.server_label.setText(f"Server: {server_name}")
        self.player_count_label.setText(f"Players: {count}")

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

class AddTimeDialog(QDialog):
    """Custom dialog for adding time with improved layout"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Time")
        # Non-modal main dialog
        self.setMinimumWidth(400)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title label
        title_label = QLabel("Add time to the current map")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 10px;")
        main_layout.addWidget(title_label)

        # Description label
        desc_label = QLabel("Number of minutes to add:")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("font-size: 10pt; margin-bottom: 5px;")
        main_layout.addWidget(desc_label)

        # Input field
        self.time_input = QLineEdit()
        self.time_input.setPlaceholderText("e.g., 5")
        self.time_input.setAlignment(Qt.AlignCenter)
        self.time_input.setStyleSheet("font-size: 11pt; padding: 8px;")
        main_layout.addWidget(self.time_input)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.ok_button = QPushButton("Add Time")
        self.ok_button.setStyleSheet("font-size: 10pt; padding: 8px;")
        self.ok_button.clicked.connect(self.accept)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet("font-size: 10pt; padding: 8px;")
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def get_time(self):
        """Return the entered time value"""
        return self.time_input.text().strip()

    def set_time(self, time_value):
        """Set the time input field value"""
        self.time_input.setText(time_value)

class UnbanPlayerDialog(QDialog):
    """Custom dialog for unbanning a player with improved layout"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Unban Player")
        # Non-modal main dialog
        self.setMinimumWidth(450)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title label
        title_label = QLabel("Unban Player")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 10px;")
        main_layout.addWidget(title_label)

        # Description label
        desc_label = QLabel("Enter the player's PlayFabID:")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("font-size: 10pt; margin-bottom: 5px;")
        main_layout.addWidget(desc_label)

        # Input field
        self.playfabid_input = QLineEdit()
        self.playfabid_input.setPlaceholderText("e.g., 1234567890ABCDEF")
        self.playfabid_input.setAlignment(Qt.AlignCenter)
        self.playfabid_input.setStyleSheet("font-size: 11pt; padding: 8px; font-family: monospace;")
        self.playfabid_input.setMaxLength(16)
        main_layout.addWidget(self.playfabid_input)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.ok_button = QPushButton("Unban Player")
        self.ok_button.setStyleSheet("font-size: 10pt; padding: 8px;")
        self.ok_button.clicked.connect(self.accept)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet("font-size: 10pt; padding: 8px;")
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def get_playfabid(self):
        """Return the entered PlayFabID, trimmed."""
        return self.playfabid_input.text().strip()

class ConsoleKeyDialog(QDialog):
    def __init__(self, current_vk: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Console Key")
        # Non-modal main dialog
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

class SanctionSearchDialog(QDialog):
    """Full-history search dialog: filter by Username, PlayFabID, or both."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sanction History Search")
        self.resize(720, 600)
        self.setModal(True)

        # Load the full history once
        self._all_records = list(reversed(_load_all_sanctions()))  # most-recent first

        root = QVBoxLayout()
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)
        self.setLayout(root)

        # ── Search bar + inline count label ───────────────────────────
        bar_row = QHBoxLayout()
        bar_row.setSpacing(10)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search by Username or PlayFabID…")
        self._search_input.setMinimumHeight(34)
        self._search_input.setClearButtonEnabled(True)
        self._search_input.textChanged.connect(self._refresh)
        bar_row.addWidget(self._search_input, 1)

        self._result_label = QLabel()
        self._result_label.setStyleSheet("color: gray; font-style: italic;")
        self._result_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._result_label.setMinimumWidth(110)
        bar_row.addWidget(self._result_label, 0)

        root.addLayout(bar_row)

        # ── Scroll area ───────────────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.NoFrame)
        root.addWidget(self._scroll, 1)

        self._refresh()

    # ── Internal helpers ──────────────────────────────────────────────

    def _refresh(self):
        term = self._search_input.text().strip().lower()

        if not term:
            matches = self._all_records
        else:
            seen    = set()
            matches = []
            for record in self._all_records:
                rid = record.get('id', '')
                if rid in seen:
                    continue
                if (term in record.get('Username',  '').lower() or
                        term in record.get('PlayFabID', '').lower()):
                    seen.add(rid)
                    matches.append(record)

        count = len(matches)
        if not term:
            self._result_label.setText(f"{count} total")
        else:
            self._result_label.setText(
                f"{count} match" + ("" if count == 1 else "es")
            )

        # Rebuild scroll content
        content = QWidget()
        layout  = QVBoxLayout(content)
        layout.setSpacing(6)
        layout.setContentsMargins(4, 4, 4, 4)

        if matches:
            is_dark = load_theme_preference()
            for record in matches:
                layout.addWidget(_build_sanction_card(record, is_dark, embed_playfabid=True))
        else:
            empty = QLabel("No matching records found.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: gray; font-style: italic; padding: 24px;")
            layout.addWidget(empty)

        layout.addStretch()
        self._scroll.setWidget(content)


class AdminDashboard(QWidget):
    def __init__(self):
        super().__init__()

        # Try to connect to Chivalry 2, but don't fail if it's not available
        self.game = None
        self.chivalry_connected = False

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
        admin_message_group = QGroupBox("Admin Message")
        admin_message_layout = QVBoxLayout()

        admin_input_row = QHBoxLayout()
        self.admin_message_input = QLineEdit()
        self.admin_message_input.setPlaceholderText("Type the admin message to send...")
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

        admin_preset_layout.addWidget(
            _make_tip_badge("Hover a Load button to preview the saved message"),
            0, Qt.AlignRight,
        )

        admin_columns_row = QHBoxLayout()
        for idx in range(ADMIN_PRESET_COUNT):
            col = _make_preset_column(
                idx, self.load_admin_preset, self.save_admin_preset, self.clear_admin_preset
            )
            self.admin_load_buttons.append(col._btn_load)
            self.admin_save_buttons.append(col._btn_save)
            self.admin_clear_buttons.append(col._btn_clear)
            admin_columns_row.addLayout(col, 1)
        admin_preset_layout.addLayout(admin_columns_row)

        admin_message_layout.addLayout(admin_preset_layout)
        admin_message_group.setLayout(admin_message_layout)

        server_message_group = QGroupBox("Server Message")
        server_message_layout = QVBoxLayout()

        server_input_row = QHBoxLayout()
        self.server_message_input = QLineEdit()
        self.server_message_input.setPlaceholderText("Type the server message to send...")
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

        server_preset_layout.addWidget(
            _make_tip_badge("Hover a Load button to preview the saved message"),
            0, Qt.AlignRight,
        )

        server_columns_row = QHBoxLayout()
        for idx in range(SERVER_PRESET_COUNT):
            col = _make_preset_column(
                idx, self.load_server_preset, self.save_server_preset, self.clear_server_preset
            )
            self.server_load_buttons.append(col._btn_load)
            self.server_save_buttons.append(col._btn_save)
            self.server_clear_buttons.append(col._btn_clear)
            server_columns_row.addLayout(col, 1)
        server_preset_layout.addLayout(server_columns_row)

        server_message_layout.addLayout(server_preset_layout)
        server_message_group.setLayout(server_message_layout)

        commands_group = QGroupBox("Commands")
        commands_layout = QVBoxLayout()

        actions_row = QHBoxLayout()
        btn_players = QPushButton("Players List")
        btn_players.clicked.connect(self.open_players_window)
        actions_row.addWidget(btn_players)

        btn_add_time = QPushButton("Add Time")
        btn_add_time.clicked.connect(self.open_add_time_dialog)
        actions_row.addWidget(btn_add_time)

        btn_unban = QPushButton("Unban Player")
        btn_unban.clicked.connect(self.open_unban_dialog)
        actions_row.addWidget(btn_unban)

        commands_layout.addLayout(actions_row)

        arb_group = QGroupBox("Arbitration")
        arb_layout = QVBoxLayout()

        btn_first_to = QPushButton("Match Arbitration (First To)")
        btn_first_to.clicked.connect(self.open_first_to_window)
        arb_layout.addWidget(btn_first_to)

        arb_group.setLayout(arb_layout)
        commands_layout.addWidget(arb_group)

        admin_server_row = QHBoxLayout()
        admin_server_row.setSpacing(12)
        admin_message_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        server_message_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        admin_server_row.addWidget(admin_message_group, 1)
        admin_server_row.addWidget(server_message_group, 1)
        commands_layout.addLayout(admin_server_row)

        commands_group.setLayout(commands_layout)
        main_layout.addWidget(commands_group)

        btn_sanction_search = QPushButton("Sanction History")
        btn_sanction_search.clicked.connect(lambda: SanctionSearchDialog(self).exec_())
        main_layout.addWidget(btn_sanction_search)

        settings_group = QGroupBox("Settings")
        settings_layout = QVBoxLayout()

        btn_webhook_config = QPushButton("Configure Discord Webhook")
        btn_webhook_config.clicked.connect(self.configure_discord_webhook)
        settings_layout.addWidget(btn_webhook_config)

        btn_discord_id_config = QPushButton("Configure Discord User ID")
        btn_discord_id_config.clicked.connect(self.configure_discord_user_id)
        settings_layout.addWidget(btn_discord_id_config)

        btn_discord_bot_token = QPushButton("Set Discord Bot Token")
        btn_discord_bot_token.clicked.connect(self.configure_discord_bot_token)
        settings_layout.addWidget(btn_discord_bot_token)

        btn_discord_channel_id = QPushButton("Set Discord Channel ID")
        btn_discord_channel_id.clicked.connect(self.configure_discord_channel_id)
        settings_layout.addWidget(btn_discord_channel_id)

        btn_fetch_discord = QPushButton("Fetch Discord Channel Messages")
        btn_fetch_discord.clicked.connect(self.fetch_discord_channel_messages)
        settings_layout.addWidget(btn_fetch_discord)

        btn_console_key = QPushButton("Configure Console Key")
        btn_console_key.clicked.connect(self.configure_console_key)
        settings_layout.addWidget(btn_console_key)

        self.theme_button = QPushButton("Dark Mode")
        self.theme_button.clicked.connect(self.toggle_theme)
        settings_layout.addWidget(self.theme_button)

        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.setLayout(main_layout)

        self.check_game_connection()

        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self.check_game_connection)
        self.connection_timer.start(5000)

        self.update_theme_button()

        self.update_admin_preset_tooltips()
        self.update_server_preset_tooltips()

        self.players_window = None
        self.first_to_window = None
        self.add_time_dialog = None
        self.unban_player_dialog = None
        self.console_key_dialog = None

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
        QTimer.singleShot(0, self.center_on_screen)

    def check_game_connection(self):
        """Check game and server connection status"""
        game_window_exists = check_chivalry_window()

        if game_window_exists and not self.chivalry_connected:
            try:
                self.game = GameChivalry()
                self.chivalry_connected = True
                print("[CONNECTION] Successfully connected to Chivalry 2")
            except Exception as e:
                print(f"[CONNECTION] Could not connect to Chivalry 2: {e}")
                self.chivalry_connected = False
                self.game = None

        elif not game_window_exists and self.chivalry_connected:
            print("[CONNECTION] Chivalry 2 window no longer found - disconnecting")
            self.chivalry_connected = False
            self.game = None

        self.update_connection_status()

    def update_admin_preset_tooltips(self):
        is_dark_theme = load_theme_preference()
        for idx, btn in enumerate(getattr(self, 'admin_load_buttons', [])):
            preset_text = get_admin_preset(idx)
            if preset_text:
                display = (preset_text[:50] + "...") if len(preset_text) > 50 else preset_text
                btn.setToolTip(f"Slot {idx}: {display}")
                btn.setStyleSheet(_populated_preset_qss(is_dark_theme))
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
                btn.setStyleSheet(_populated_preset_qss(is_dark_theme))
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
        if msg:
            set_persisted_value('last_admin_msg', msg)

        if not msg:
            QMessageBox.warning(self, "Error", "Please enter a message to send.")
            return
        print(f"[ADMIN MESSAGE] {msg}")

        if self.chivalry_connected and hasattr(self.game, 'AdminSay'):
            try:
                self.game.AdminSay(msg)
            except Exception as e:
                QMessageBox.warning(self, "Game Error", f"Failed to send message to game:\n{str(e)}")

    def send_server_message(self):
        msg = self.server_message_input.text().strip()
        if msg:
            set_persisted_value('last_server_msg', msg)

        if not msg:
            QMessageBox.warning(self, "Error", "Please enter a message to send.")
            return
        print(f"[SERVER MESSAGE] {msg}")

        if self.chivalry_connected and hasattr(self.game, 'ServerSay'):
            try:
                self.game.ServerSay(msg)
            except Exception as e:
                QMessageBox.warning(self, "Game Error", f"Failed to send message to game:\n{str(e)}")

    def open_players_window(self):
        self.admin_message_input.setText(get_persisted_value('last_admin_msg', ""))
        self.server_message_input.setText(get_persisted_value('last_server_msg', ""))

        if self.players_window is not None and self.players_window.isVisible():
            self.players_window.raise_()
            self.players_window.activateWindow()
        else:
            if self.players_window is None:
                self.players_window = PlayersWindow(self)
                self.players_window.finished.connect(lambda: setattr(self, 'players_window', None))

            self.players_window.show()
            self.players_window.raise_()
            self.players_window.activateWindow()

    def open_add_time_dialog(self):
        # Check if dialog already exists and is visible
        if self.add_time_dialog is not None and self.add_time_dialog.isVisible():
            # Dialog already exists, just bring it to front
            self.add_time_dialog.raise_()
            self.add_time_dialog.activateWindow()
            return

        # Create new dialog
        self.add_time_dialog = AddTimeDialog(parent=self)
        # Pre-fill last add time value
        self.add_time_dialog.set_time(get_persisted_value('last_add_time', ""))

        # Connect accepted signal to handle the action
        def on_accepted():
            added_time = self.add_time_dialog.get_time()
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

        self.add_time_dialog.accepted.connect(on_accepted)
        # Connect finished signal to clean up reference when dialog is closed
        self.add_time_dialog.finished.connect(lambda: setattr(self, 'add_time_dialog', None))

        # Show non-modal dialog
        self.add_time_dialog.show()
        self.add_time_dialog.raise_()
        self.add_time_dialog.activateWindow()

    def open_unban_dialog(self):
        """Open dialog to unban a player by PlayFabID"""
        # Check if dialog already exists and is visible
        if self.unban_player_dialog is not None and self.unban_player_dialog.isVisible():
            # Dialog already exists, just bring it to front
            self.unban_player_dialog.raise_()
            self.unban_player_dialog.activateWindow()
            return

        # Create new dialog
        self.unban_player_dialog = UnbanPlayerDialog(parent=self)

        # Connect accepted signal to handle the action
        def on_accepted():
            player_id = self.unban_player_dialog.get_playfabid()

            # Validate PlayFabID: must be exactly 16 characters, uppercase letters and numbers only
            if not player_id or len(player_id) != 16 or not player_id.isupper() or not player_id.isalnum():
                QMessageBox.warning(
                    self,
                    "Invalid PlayFabID",
                    "PlayFabID must be exactly 16 characters long and contain only uppercase letters and numbers."
                )
                return

            print(f"[UNBAN] Player ID={player_id}")

            # Try to execute the unban command if game is connected
            if self.chivalry_connected and hasattr(self.game, 'unbanbyid'):
                try:
                    self.game.unbanbyid(player_id)

                    # Send ServerSay message to confirm unban
                    if hasattr(self.game, 'ServerSay'):
                        try:
                            self.game.ServerSay(f"{player_id} unban successful.")
                        except Exception as e:
                            print(f"[UNBAN] Could not send ServerSay message: {e}")

                    # Ask user to confirm if the unban was successful by checking the ServerSay message
                    def ask_confirmation():
                        confirm = QMessageBox.question(
                            self,
                            "Unban Confirmation",
                            f"Did the ServerSay message appear in the game confirming the unban?\n\n"
                            f"Message: '{player_id} unban successful.'",
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.Yes
                        )

                        if confirm == QMessageBox.Yes:
                            # Send Discord webhook notification only if user confirms success
                            wehbooks.MessageForAdmin(player_id, "N/A", None, None, "unban")
                            QMessageBox.information(
                                self,
                                "Player Unbanned",
                                f"Successfully unbanned player with ID: {player_id}\n\nDiscord notification sent."
                            )
                        else:
                            QMessageBox.warning(
                                self,
                                "Unban Not Confirmed",
                                f"Unban was not confirmed. Discord notification was not sent.\n\n"
                                f"Please verify the unban status manually."
                            )

                    # Delay the confirmation dialog to give time for the ServerSay message to appear
                    QTimer.singleShot(2000, ask_confirmation)

                except Exception as e:
                    QMessageBox.warning(self, "Game Connection Error", f"Could not execute unban command:\n{str(e)}")
            else:
                QMessageBox.warning(self, "Not Connected", "Cannot unban player - Chivalry 2 is not connected.\n\nPlease ensure Chivalry 2 is running.")

        self.unban_player_dialog.accepted.connect(on_accepted)
        # Connect finished signal to clean up reference when dialog is closed
        self.unban_player_dialog.finished.connect(lambda: setattr(self, 'unban_player_dialog', None))

        # Show non-modal dialog
        self.unban_player_dialog.show()
        self.unban_player_dialog.raise_()
        self.unban_player_dialog.activateWindow()

    def open_first_to_window(self):
        if self.first_to_window is not None and self.first_to_window.isVisible():
            self.first_to_window.raise_()
            self.first_to_window.activateWindow()
            return
        self.first_to_window = FirstToScoreboardWindow(self)
        self.first_to_window.setAttribute(Qt.WA_DeleteOnClose, True)
        self.first_to_window.finished.connect(lambda: setattr(self, 'first_to_window', None))
        # Show non-modal dialog
        self.first_to_window.show()
        self.first_to_window.raise_()
        self.first_to_window.activateWindow()

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
        current_primary_url   = get_persisted_value('primary_webhook', '')
        current_secondary_url = get_persisted_value('secondary_webhook', '')
        if current_primary_url   == 'None': current_primary_url   = ''
        if current_secondary_url == 'None': current_secondary_url = ''

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

        try:
            set_persisted_value('primary_webhook',   primary_url   or 'None')
            set_persisted_value('secondary_webhook', secondary_url or 'None')

            # Reinitialize webhooks
            webhook_initialized = wehbooks.initialize_webhook()

            # Update the status display
            self.update_webhook_status()

            if primary_url or secondary_url:
                if webhook_initialized:
                    if primary_url and secondary_url:
                        message = "Both primary and secondary Discord webhooks have been configured successfully!"
                    elif primary_url:
                        message = "Primary Discord webhook has been configured successfully!"
                    else:
                        message = "Secondary Discord webhook has been configured successfully!"

                    QMessageBox.information(self, "Configuration Successful", message)
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
        current_discord_user_id = get_persisted_value('discord_user_id', '')
        if current_discord_user_id == 'None':
            current_discord_user_id = ''

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

        try:
            set_persisted_value('discord_user_id', discord_user_id or 'None')

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

    def configure_discord_bot_token(self):
        """Allow user to set the Discord Bot Token used for channel scraping."""
        current_token = get_persisted_value('discord_bot_token', '')
        if current_token == 'None':
            current_token = ''

        token, ok = self.prompt_wide_text(
            "Discord Bot Token",
            "Enter your Discord Bot Token:\n"
            "(Discord Developer Portal > Your Application > Bot > Token)\n"
            "(Leave empty to clear)",
            current_token
        )
        if not ok:
            return

        token = token.strip()
        set_persisted_value('discord_bot_token', token if token else 'None')

    def configure_discord_channel_id(self):
        """Allow user to set the Discord Channel ID to scrape."""
        current_channel = get_persisted_value('discord_channel_id', '')
        if current_channel == 'None':
            current_channel = ''

        channel_id, ok = QInputDialog.getText(
            self,
            "Discord Channel ID",
            "Enter the Discord Channel ID to scrape:\n"
            "(Right-click the channel in Discord > Copy Channel ID)\n"
            "(Developer Mode must be enabled in Discord settings)",
            text=current_channel
        )
        if not ok:
            return

        channel_id = channel_id.strip()
        if channel_id and not channel_id.isdigit():
            QMessageBox.warning(self, "Invalid Channel ID", "Channel ID must be a numeric value.")
            return

        set_persisted_value('discord_channel_id', channel_id if channel_id else 'None')

    def fetch_discord_channel_messages(self):
        """Fetch all webhook messages from the configured Discord channel and save to discordlogshistory."""
        import urllib.request
        import urllib.error
        import json
        import time

        token = get_persisted_value('discord_bot_token', '')
        channel_id = get_persisted_value('discord_channel_id', '')

        if not token or token == 'None':
            QMessageBox.warning(
                self, "Not Configured",
                "No Discord Bot Token configured.\n"
                "Please use 'Set Discord Bot Token' first."
            )
            return
        if not channel_id or channel_id == 'None':
            QMessageBox.warning(
                self, "Not Configured",
                "No Discord Channel ID configured.\n"
                "Please use 'Set Discord Channel ID' first."
            )
            return

        progress_dialog = QDialog(self)
        progress_dialog.setWindowTitle("Fetching Messages...")
        progress_dialog.setModal(True)
        pd_layout = QVBoxLayout()
        pd_label = QLabel("Connecting to Discord API, please wait...")
        pd_layout.addWidget(pd_label)
        pd_progress = QProgressBar()
        pd_progress.setRange(0, 0)
        pd_layout.addWidget(pd_progress)
        progress_dialog.setLayout(pd_layout)
        progress_dialog.resize(380, 80)
        progress_dialog.show()
        QApplication.processEvents()

        all_messages = []
        before = None
        headers = {
            'Authorization': f'Bot {token}',
            'Content-Type': 'application/json',
            'User-Agent': 'OVAAdminTool/1.0'
        }

        try:
            while True:
                url = f'https://discord.com/api/v10/channels/{channel_id}/messages?limit=100'
                if before:
                    url += f'&before={before}'

                req = urllib.request.Request(url, headers=headers)

                try:
                    with urllib.request.urlopen(req, timeout=15) as response:
                        data = json.loads(response.read().decode('utf-8'))
                except urllib.error.HTTPError as e:
                    if e.code == 429:
                        try:
                            error_data = json.loads(e.read().decode('utf-8'))
                            retry_after = float(error_data.get('retry_after', 1.0))
                        except Exception:
                            retry_after = 1.0
                        pd_label.setText(f"Rate limited — retrying in {retry_after:.1f}s...")
                        QApplication.processEvents()
                        time.sleep(retry_after)
                        continue
                    elif e.code == 401:
                        progress_dialog.close()
                        QMessageBox.critical(self, "Authentication Failed",
                                             "Invalid Bot Token. Please reconfigure the Discord Bot Scraper.")
                        return
                    elif e.code == 403:
                        progress_dialog.close()
                        QMessageBox.critical(self, "Access Denied",
                                             "The bot does not have permission to read this channel.\n"
                                             "Make sure it has the 'Read Message History' permission.")
                        return
                    elif e.code == 404:
                        progress_dialog.close()
                        QMessageBox.critical(self, "Channel Not Found",
                                             "Channel ID not found. Please verify the Channel ID is correct.")
                        return
                    else:
                        progress_dialog.close()
                        QMessageBox.critical(self, "HTTP Error", f"Discord API returned HTTP {e.code}.")
                        return

                if not data:
                    break

                webhook_messages = [m for m in data if m.get('webhook_id')]
                all_messages.extend(webhook_messages)
                before = data[-1]['id']
                pd_label.setText(f"Fetched {len(all_messages)} webhook messages so far...")
                QApplication.processEvents()

                if len(data) < 100:
                    break

                time.sleep(0.25)

        except Exception as e:
            progress_dialog.close()
            QMessageBox.critical(self, "Error", f"An unexpected error occurred:\n{str(e)}")
            return

        if not all_messages:
            progress_dialog.close()
            return

        # Sort oldest first (by snowflake ID, which is chronological)
        all_messages.sort(key=lambda m: m['id'])

        # --- Read the existing log once ------------------------------------
        # We need three things from it: the set of already-stored message IDs
        # (to filter out duplicates), the records themselves (so we can
        # back-fill missing moderator names in place), and the set of IDs
        # currently lacking a resolved name so we know what still needs a
        # Discord API lookup.
        existing_records = []
        existing_ids_set = set()
        ids_missing_name = set()
        if os.path.exists(DISCORD_LOG_FILE):
            try:
                with open(DISCORD_LOG_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = json.loads(line)
                        except Exception:
                            # Preserve malformed lines untouched for safety
                            existing_records.append(line)
                            continue
                        existing_records.append(rec)
                        if rec.get('id'):
                            existing_ids_set.add(rec['id'])
                        mid = rec.get('ModeratorID', '')
                        if mid and not rec.get('ModeratorName', ''):
                            ids_missing_name.add(mid)
            except Exception:
                pass

        new_messages = [m for m in all_messages if m.get('id') not in existing_ids_set]

        # --- Collect moderator IDs from new messages -----------------------
        ids_from_new = set()
        for msg in new_messages:
            for emb in msg.get('embeds', []):
                for field in emb.get('fields', []):
                    if field.get('name') in ('Moderator', 'Referee'):
                        mid = field.get('value', '').strip().lstrip('<@').rstrip('>')
                        if mid:
                            ids_from_new.add(mid)

        ids_to_resolve = ids_missing_name | ids_from_new

        # --- Resolve names via the Discord Users API -----------------------
        # One call per unique ID per scrape; results are written directly
        # onto each record, so we never consult a shared name cache on the
        # read path. IDs that fail to resolve stay ID-only and get retried
        # on the next scrape.
        name_by_id = {}
        if ids_to_resolve:
            total = len(ids_to_resolve)
            pd_label.setText(f"Resolving moderator names (0/{total})...")
            QApplication.processEvents()

            for i, mid in enumerate(ids_to_resolve, start=1):
                u_req = urllib.request.Request(
                    f'https://discord.com/api/v10/users/{mid}',
                    headers=headers,
                )
                try:
                    with urllib.request.urlopen(u_req, timeout=10) as u_resp:
                        u_data = json.loads(u_resp.read().decode('utf-8'))
                        name = u_data.get('global_name') or u_data.get('username') or ''
                        if name:
                            name_by_id[mid] = name
                except urllib.error.HTTPError as ue:
                    if ue.code == 429:
                        try:
                            err_data = json.loads(ue.read().decode('utf-8'))
                            retry_after = float(err_data.get('retry_after', 1.0))
                        except Exception:
                            retry_after = 1.0
                        time.sleep(retry_after)
                        try:
                            with urllib.request.urlopen(u_req, timeout=10) as u_resp:
                                u_data = json.loads(u_resp.read().decode('utf-8'))
                                name = u_data.get('global_name') or u_data.get('username') or ''
                                if name:
                                    name_by_id[mid] = name
                        except Exception:
                            pass
                    # 404 / other: silently skip; next scrape can retry
                except Exception:
                    pass

                pd_label.setText(f"Resolving moderator names ({i}/{total})...")
                QApplication.processEvents()
                time.sleep(0.1)  # stays well below Discord's global rate limit

        # --- Enrich legacy records in memory -------------------------------
        legacy_changed = False
        if name_by_id:
            for rec in existing_records:
                if not isinstance(rec, dict):
                    continue  # malformed line preserved verbatim
                mid = rec.get('ModeratorID', '')
                if mid and not rec.get('ModeratorName', '') and mid in name_by_id:
                    rec['ModeratorName'] = name_by_id[mid]
                    legacy_changed = True

        # --- Append new records --------------------------------------------
        if new_messages:
            try:
                with open(DISCORD_LOG_FILE, 'a', encoding='utf-8') as f:
                    for msg in new_messages:
                        f.write(_serialize_discord_message(msg, name_by_id) + '\n')
            except Exception as e:
                progress_dialog.close()
                QMessageBox.critical(self, "Save Error", f"Could not write discordlogshistory:\n{str(e)}")
                return

        # --- Atomically rewrite log if legacy records were enriched --------
        if legacy_changed:
            pd_label.setText("Updating log file...")
            QApplication.processEvents()
            tmp_path = DISCORD_LOG_FILE + '.tmp'
            try:
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    for rec in existing_records:
                        if isinstance(rec, dict):
                            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
                        else:
                            f.write(rec + '\n')
                    # Append any newly-written records too, so the file stays
                    # consistent with what we just appended above.
                    for msg in new_messages:
                        f.write(_serialize_discord_message(msg, name_by_id) + '\n')
                os.replace(tmp_path, DISCORD_LOG_FILE)
            except Exception as e:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                progress_dialog.close()
                QMessageBox.warning(self, "Log Rewrite Failed",
                                    f"Could not rewrite discordlogshistory to enrich "
                                    f"legacy moderator names:\n{str(e)}\n\n"
                                    f"New records were still appended successfully.")
                return

        progress_dialog.close()

    def configure_console_key(self):
        """Prompt user to press the key used to open the in-game console and persist its VK code."""
        # Check if dialog already exists and is visible
        if self.console_key_dialog is not None and self.console_key_dialog.isVisible():
            # Dialog already exists, just bring it to front
            self.console_key_dialog.raise_()
            self.console_key_dialog.activateWindow()
            return

        # Load current value if any
        try:
            current_vk = get_persisted_value('console_vk', "")
        except Exception:
            current_vk = ""

        # Create new dialog
        self.console_key_dialog = ConsoleKeyDialog(current_vk=current_vk, parent=self)

        # Connect accepted signal to handle the action
        def on_accepted():
            if self.console_key_dialog.captured_vk is not None:
                # Save as integer string to localconfig via persisted storage
                set_persisted_value('console_vk', str(self.console_key_dialog.captured_vk))
                # Clear the cached console key to force re-detection with new value
                from core import inputLib
                inputLib.clearConsoleKeyCache()
                QMessageBox.information(self, "Console Key Saved", f"Console key saved as VK {self.console_key_dialog.captured_vk}.")

        self.console_key_dialog.accepted.connect(on_accepted)
        # Connect finished signal to clean up reference when dialog is closed
        self.console_key_dialog.finished.connect(lambda: setattr(self, 'console_key_dialog', None))

        # Show non-modal dialog
        self.console_key_dialog.show()
        self.console_key_dialog.raise_()
        self.console_key_dialog.activateWindow()

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
        # Non-modal main dialog
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
        tag_row.addWidget(_make_tip_badge("Brackets are added automatically"), 0, Qt.AlignRight)
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
        if self.ft_discord_notification.isChecked():
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

# ---- Discord log history (JSON Lines database) ----

DISCORD_LOG_FILE = "discordlogshistory"


def _load_discord_log_ids() -> set:
    """Read discordlogshistory and return the set of all stored message IDs."""
    ids = set()
    if not os.path.exists(DISCORD_LOG_FILE):
        return ids
    try:
        with open(DISCORD_LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        msg_id = record.get('id')
                        if msg_id:
                            ids.add(msg_id)
                    except Exception:
                        pass
    except Exception:
        pass
    return ids


def _serialize_discord_message(msg: dict, name_by_id: dict = None) -> str:
    """Serialize a single Discord webhook message to a flat JSON line.

    Stored fields: id, timestamp, action, PlayFabID, Username, Reason,
                   Duration, ModeratorID, ModeratorName

    Action is extracted from the bold word(s) in the embed description:
      "A **ban** has been executed"     -> ban
      "An **unban** has been executed"  -> unban
      "A **kick** has been executed"    -> kick
      "A **warning** has been issued"   -> warn
      "A **First To** match ..."        -> ft

    If `name_by_id` is provided and contains the extracted moderator ID,
    the corresponding display name is baked into the record as
    `ModeratorName` so the read path never needs a separate cache.
    """
    _ACTION_MAP = {
        'ban':      'ban',
        'unban':    'unban',
        'kick':     'kick',
        'warning':  'warn',
        'first to': 'ft',
    }

    record = {
        'id':            msg.get('id', ''),
        'timestamp':     msg.get('timestamp', ''),
        'action':        '',
        'PlayFabID':     '',
        'Username':      '',
        'Reason':        '',
        'Duration':      '',
        'ModeratorID':   '',
        'ModeratorName': '',
    }

    for emb in msg.get('embeds', []):
        # Derive action from embed description
        desc = emb.get('description', '')
        m = re.search(r'\*\*([^*]+)\*\*', desc)
        if m:
            bold = m.group(1).lower()
            for key, val in _ACTION_MAP.items():
                if key in bold:
                    record['action'] = val
                    break

        for field in emb.get('fields', []):
            fname  = field.get('name', '')
            fvalue = field.get('value', '')

            if fname in ('Information', 'Results'):
                for line in fvalue.split('\n'):
                    line = line.strip()
                    if ': ' in line:
                        key, _, val = line.partition(': ')
                        key = key.strip()
                        val = val.strip()
                        if key == 'PlayFabID':
                            record['PlayFabID'] = val
                        elif key == 'Username':
                            record['Username'] = val
                        elif key == 'Reason':
                            record['Reason'] = val
                        elif key == 'Duration':
                            record['Duration'] = val

            elif fname in ('Moderator', 'Referee'):
                mid = fvalue.strip().lstrip('<@').rstrip('>')
                record['ModeratorID'] = mid
                if name_by_id and mid in name_by_id:
                    record['ModeratorName'] = name_by_id[mid]

    return json.dumps(record, ensure_ascii=False)


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
# 20..22: admin message presets (3)
# 23..25: server message presets (3)
# 26: console virtual key code
# 27: discord bot token (for channel scraping)
# 28: discord channel id (for channel scraping)
PERSIST_INDEX = {
    'primary_webhook':   0,
    'secondary_webhook': 1,
    'discord_user_id':   2,
    'theme':             13,
    'last_ban_reason':   14,
    'last_ban_duration': 15,
    'last_kick_reason':  16,
    'last_admin_msg':    17,
    'last_server_msg':   18,
    'last_add_time':     19,
    'console_vk':        26,
    'discord_bot_token': 27,
    'discord_channel_id':28,
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


_theme_cache = None  # module-level cache: None | True (dark) | False (light)


def load_theme_preference():
    """Return True for dark, False for light. Defaults to dark.

    Result is cached so frequent callers (e.g. sanction card construction)
    avoid re-reading localconfig on every invocation. Invalidated
    automatically on save_theme_preference().
    """
    global _theme_cache
    if _theme_cache is None:
        val = (get_persisted_value('theme', 'dark') or 'dark').strip().lower()
        _theme_cache = (val != 'light')
    return _theme_cache


def save_theme_preference(is_dark_theme):
    """Persist theme and refresh the module-level cache."""
    global _theme_cache
    _theme_cache = bool(is_dark_theme)
    set_persisted_value('theme', 'dark' if is_dark_theme else 'light')
    _theme_bus.theme_changed.emit(_theme_cache)


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

# ═══════════════════════════════════════════════════════════════════════════
# ═══════════════════ PREVIEW MODE — DELETE BEFORE SHIPPING ═════════════════
# ═══════════════════════════════════════════════════════════════════════════
# Activated via `python interface.py --preview` (or `--preview` anywhere in
# sys.argv). Monkey-patches the data sources for PlayersWindow and its
# PlayerActionDialog so the UI can be exercised without Chivalry 2 running.
#
# To remove: delete this entire fenced block AND the matching
# `_install_preview_mode()` call down in main(). Nothing else references it.
# ═══════════════════════════════════════════════════════════════════════════

def _install_preview_mode():
    """Replace live data paths with fake fixtures for UI preview."""
    import datetime as _dt

    now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat()
    old_iso = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=90)).isoformat()
    warn_iso = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=5)).isoformat()

    # 12 fake players, status sprinkled across banned / cautioned / clean
    _FAKE_PLAYERS = [
        ("LadyAgathaKnight",   "1A2B3C4D5E6F7A8B"),
        ("SirMasonFootman",    "2B3C4D5E6F7A8B9C"),
        ("CrossbowEnthusiast", "3C4D5E6F7A8B9C0D"),
        ("TenosianArcher",     "4D5E6F7A8B9C0D1E"),
        ("ThePeasantKing",     "5E6F7A8B9C0D1E2F"),
        ("BrotherMaynard",     "6F7A8B9C0D1E2F3A"),
        ("DukeArgonIII",       "7A8B9C0D1E2F3A4B"),
        ("VanguardRusher",     "8B9C0D1E2F3A4B5C"),
        ("HeraldOfWar",        "9C0D1E2F3A4B5C6D"),
        ("ShieldmaidenHel",    "0D1E2F3A4B5C6D7E"),
        ("GrimwardFootman",    "1E2F3A4B5C6D7E8F"),
        ("BannermanOlaf",      "2F3A4B5C6D7E8F9A"),
    ]

    # Fake sanction history keyed by PlayFabID (uppercase)
    _FAKE_SANCTIONS = {
        # Banned player — active 72h ban
        "3C4D5E6F7A8B9C0D": [
            {"id": "fk-001", "timestamp": now_iso, "action": "ban",
             "PlayFabID": "3C4D5E6F7A8B9C0D", "Username": "CrossbowEnthusiast",
             "Reason": "Intentional teamdamage & harassment",
             "Duration": "72h", "ModeratorID": "1234567890"},
            {"id": "fk-002", "timestamp": old_iso, "action": "kick",
             "PlayFabID": "3C4D5E6F7A8B9C0D", "Username": "CrossbowEnthusiast",
             "Reason": "Excessive teamkilling (warning ignored)",
             "Duration": "", "ModeratorID": "1234567890"},
        ],
        # Cautioned — recent warning + historical kick
        "5E6F7A8B9C0D1E2F": [
            {"id": "fk-003", "timestamp": warn_iso, "action": "warn",
             "PlayFabID": "5E6F7A8B9C0D1E2F", "Username": "ThePeasantKing",
             "Reason": "Verbal abuse in chat — first warning",
             "Duration": "", "ModeratorID": "1234567890"},
            {"id": "fk-004", "timestamp": old_iso, "action": "kick",
             "PlayFabID": "5E6F7A8B9C0D1E2F", "Username": "ThePeasantKing",
             "Reason": "AFK in objective",
             "Duration": "", "ModeratorID": "9876543210"},
        ],
        # Cautioned — single recent kick
        "8B9C0D1E2F3A4B5C": [
            {"id": "fk-005", "timestamp": warn_iso, "action": "kick",
             "PlayFabID": "8B9C0D1E2F3A4B5C", "Username": "VanguardRusher",
             "Reason": "Griefing spawn area",
             "Duration": "", "ModeratorID": "1234567890"},
        ],
        # Rich history — multiple cards to check scroll behaviour
        "0D1E2F3A4B5C6D7E": [
            {"id": "fk-006", "timestamp": warn_iso, "action": "warn",
             "PlayFabID": "0D1E2F3A4B5C6D7E", "Username": "ShieldmaidenHel",
             "Reason": "Minor chat offence — friendly warning",
             "Duration": "", "ModeratorID": "1234567890"},
            {"id": "fk-007", "timestamp": old_iso, "action": "ban",
             "PlayFabID": "0D1E2F3A4B5C6D7E", "Username": "ShieldmaidenHel",
             "Reason": "Cheating (expired)",
             "Duration": "24h", "ModeratorID": "9876543210"},
            {"id": "fk-008", "timestamp": old_iso, "action": "unban",
             "PlayFabID": "0D1E2F3A4B5C6D7E", "Username": "ShieldmaidenHel",
             "Reason": "", "Duration": "", "ModeratorID": "1234567890"},
            {"id": "fk-009", "timestamp": old_iso, "action": "kick",
             "PlayFabID": "0D1E2F3A4B5C6D7E", "Username": "ShieldmaidenHel",
             "Reason": "Language filter", "Duration": "", "ModeratorID": "1234567890"},
        ],
    }

    # ── Patch sanction-history lookups ────────────────────────────────────
    _FAKE_ALL = [r for recs in _FAKE_SANCTIONS.values() for r in recs]
    globals()['_load_sanctions_for_player'] = (
        lambda pid: _FAKE_SANCTIONS.get(pid.upper(), [])
    )
    globals()['_load_all_sanctions'] = lambda: list(_FAKE_ALL)
    globals()['_compute_all_player_statuses'] = lambda: {
        "3C4D5E6F7A8B9C0D": "banned",
        "5E6F7A8B9C0D1E2F": "cautioned",
        "8B9C0D1E2F3A4B5C": "cautioned",
        "0D1E2F3A4B5C6D7E": "cautioned",
    }

    # ── Patch PlayersWindow to skip game calls and render fake players ────
    def _preview_refresh(self):
        self.players = list(_FAKE_PLAYERS)
        self.filtered_players = self.players.copy()
        self.populate_list()
        self.server_label.setText("Server: Preview Server (fake)")
        self.player_count_label.setText(f"Players: {len(self.players)}")

    PlayersWindow.refresh_player_list = _preview_refresh

    # PlayersWindow.__init__ only auto-refreshes when self.game is not None.
    # In preview mode GameChivalry() raises, so self.game stays None and the
    # auto-refresh gate blocks our fake data. Wrap __init__ to force it.
    _orig_players_init = PlayersWindow.__init__
    def _preview_players_init(self, parent=None):
        _orig_players_init(self, parent)
        self.refresh_player_list()
    PlayersWindow.__init__ = _preview_players_init

    # ── Also patch the game-connection poll so the status label reads OK ──
    def _preview_check_connection(self):
        self.chivalry_connected = True
        self.update_connection_status()

    AdminDashboard.check_game_connection = _preview_check_connection

    # ── Skip the "Waiting for Chivalry 2" dialog ──────────────────────────
    globals()['check_chivalry_window'] = lambda: True

    print("[PREVIEW] Preview mode active — data is fake, nothing is sent to the game.")


# ═══════════════════ END PREVIEW MODE BLOCK ════════════════════════════════


def _show_release_notes_dialog(parent, release_tag):
    """Fetch and display GitHub release notes for the given tag in a modal dialog.

    On fetch failure (offline, GitHub unreachable, 404), shows a minimal fallback
    dialog with a clickable link to the release page so the user can view notes
    manually when back online.
    """
    import urllib.request
    from PyQt5.QtWidgets import QTextBrowser

    try:
        from core.autoupdater import GITHUB_REPO
    except Exception:
        GITHUB_REPO = "Lionkjgame1219/Chiv2AdminDashboard"

    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/{release_tag}"
    web_url = f"https://github.com/{GITHUB_REPO}/releases/tag/{release_tag}"

    body = None
    title = release_tag
    try:
        req = urllib.request.Request(
            api_url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "Chiv2AdminDashboard",
            },
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        title = data.get("name") or data.get("tag_name") or release_tag
        body = (data.get("body") or "").strip()
    except Exception as e:
        print(f"[POST-UPDATE] Failed to fetch release notes for {release_tag}: {e}")

    dlg = QDialog(parent)
    dlg.setWindowTitle(f"What's new — {title}")
    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(15, 15, 15, 15)
    layout.setSpacing(10)

    header = QLabel(f"<h2 style='margin:0'>{title}</h2>")
    layout.addWidget(header)

    if body is None:
        dlg.resize(520, 200)
        msg = QLabel(
            f"Release <b>{release_tag}</b> has been installed.<br><br>"
            f"Release notes couldn't be fetched right now (you may be offline "
            f"or GitHub is unreachable).<br><br>"
            f"You can view them here once you're back online:<br>"
            f'<a href="{web_url}">{web_url}</a>'
        )
        msg.setWordWrap(True)
        msg.setOpenExternalLinks(True)
        msg.setTextInteractionFlags(Qt.TextBrowserInteraction)
        layout.addWidget(msg)
        layout.addStretch(1)
    else:
        dlg.resize(640, 500)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        text = body if body else "_No release notes provided for this release._"
        # setMarkdown requires Qt >= 5.14; fall back to plain text otherwise.
        try:
            browser.setMarkdown(text)
        except (AttributeError, TypeError):
            browser.setPlainText(text)
        layout.addWidget(browser)

    btns = QDialogButtonBox(QDialogButtonBox.Ok)
    btns.accepted.connect(dlg.accept)
    layout.addWidget(btns)

    dlg.exec_()


def main():
    # Parse (and strip) --post-update=<tag> before any update checks, so this
    # flag can never propagate into a subsequent update's passthrough argv.
    post_update_tag = None
    _filtered_argv = []
    for _a in sys.argv:
        if _a.startswith("--post-update="):
            _val = _a.split("=", 1)[1]
            if _val:
                post_update_tag = _val
        else:
            _filtered_argv.append(_a)
    sys.argv[:] = _filtered_argv

    # ---- Auto-update (Windows packaged .exe only) ----
    # If an update is available, a temporary updater copy of this executable is spawned,
    # this process exits, the updater replaces the old .exe, and then relaunches the app.
    #
    # NOTE: The updater process itself runs this same entrypoint with '--apply-update'.
    # In that mode we do NOT start the full dashboard UI.
    try:
        from core import autoupdater
        if "--apply-update" in sys.argv:
            if autoupdater.handle_update_flow():
                sys.exit(0)
    except Exception:
        # If updater mode fails, just exit to avoid launching the full UI while files may be changing.
        if "--apply-update" in sys.argv:
            sys.exit(0)

    app = QApplication(sys.argv)

    update_dialog = None
    update_label = None
    try:
        is_frozen = bool(getattr(sys, "frozen", False))
        if is_frozen and ("--skip-update" not in sys.argv):
            update_dialog = QDialog()
            update_dialog.setWindowTitle("AdminDashboard")
            update_dialog.setFixedSize(460, 130)

            layout = QVBoxLayout(update_dialog)
            update_label = QLabel("Checking for updates...")
            update_label.setWordWrap(True)
            bar = QProgressBar()
            bar.setRange(0, 0)
            layout.addWidget(update_label)
            layout.addWidget(bar)
            update_dialog.show()
            app.processEvents()

            def _update_status(msg: str) -> None:
                if update_label is not None:
                    update_label.setText(str(msg))
                app.processEvents()

            from core import autoupdater
            if autoupdater.handle_update_flow(status_callback=_update_status):
                try:
                    app.processEvents()
                except Exception:
                    pass
                sys.exit(0)
    except Exception as e:
        try:
            print(f"[UPDATE] Auto-update skipped/failed: {e}")
        except Exception:
            pass
    finally:
        try:
            if update_dialog is not None:
                update_dialog.close()
                app.processEvents()
        except Exception:
            pass

    app._instant_tt = InstantToolTipFilter(delay_ms=300)
    app.installEventFilter(app._instant_tt)

    # ---- PREVIEW MODE — DELETE WITH THE FENCED BLOCK ABOVE ----
    if "--preview" in sys.argv:
        _install_preview_mode()

    is_dark_theme = load_theme_preference()
    if is_dark_theme:
        apply_dark_theme(app)
    else:
        apply_light_theme(app)

    if "--no-wait" not in sys.argv and not check_chivalry_window():
        waiting_dialog = ChivalryWaitingDialog()
        result = waiting_dialog.exec_()
        # If dialog was rejected (closed with X or Esc), exit the application
        if result == QDialog.Rejected:
            sys.exit(0)

    # Initialize Discord webhooks at startup
    import core.wehbooks as wehbooks
    webhook_initialized = wehbooks.initialize_webhook()
    if webhook_initialized:
        print("[STARTUP] Discord webhook(s) initialized successfully")
    else:
        print("[STARTUP] Discord webhooks not configured or failed to initialize")

    # Check discord logs history file at startup
    if os.path.exists(DISCORD_LOG_FILE):
        known_ids = _load_discord_log_ids()
        print(f"[STARTUP] Discord logs history file found — {len(known_ids)} entries")
    else:
        print("[STARTUP] Discord logs history file not found — will be created on first scrape")

    window = AdminDashboard()
    window.show()

    # Post-update "What's new?" banner: fires only on the first launch after
    # the autoupdater applied a new release (the flag was already consumed at
    # the top of main() and removed from sys.argv).
    if post_update_tag:
        try:
            _show_release_notes_dialog(window, post_update_tag)
        except Exception as e:
            print(f"[POST-UPDATE] Release notes dialog failed: {e}")

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
