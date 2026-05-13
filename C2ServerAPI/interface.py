import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QDialog,
    QFormLayout, QLineEdit, QDialogButtonBox, QMessageBox, QListWidget, QHBoxLayout,
    QGroupBox, QSpacerItem, QSizePolicy, QInputDialog, QProgressBar, QCheckBox, QToolTip, QGridLayout,
    QScrollArea, QFrame, QListWidgetItem, QStyledItemDelegate, QStyle,
    QTableWidget, QTableWidgetItem, QComboBox, QHeaderView, QAbstractItemView,
    QStylePainter, QStyleOptionComboBox
)
from PyQt5.QtGui import QFont, QIntValidator, QCursor, QDesktopServices, QColor, QBrush
from PyQt5.QtCore import Qt, QTimer, QObject, QEvent, QUrl, pyqtSignal

import pyperclip
import os
import json
import datetime
import win32gui
import re
import threading
import random
from time import sleep


from core.C2ServerAPIExample import GameChivalry
import core.wehbooks as wehbooks


# Design tokens — single source of truth for spacing, radii and accent colours.

# Spacing scale — compose these rather than picking arbitrary ints.
UI_PAD_OUTER   = 18   # outer dialog margin
UI_PAD_SECTION = 12   # inside group boxes / between sections
UI_PAD_INNER   = 8    # between adjacent widgets in a row/column
UI_PAD_TIGHT   = 6    # header rows, badge rows

UI_SPACING_SECTION = 14   # between top-level sections in a dialog
UI_SPACING_INNER   = 8    # between adjacent widgets

UI_RADIUS       = 6
UI_RADIUS_SMALL = 4

UI_ACCENT            = '#4a6cf7'
UI_ACCENT_HOVER      = '#5a7cff'
UI_ACCENT_PRESSED    = '#3a5ce0'

# Action accents shared by buttons and sanction cards.
UI_COLOR_BAN    = '#e74c3c'
UI_COLOR_KICK   = '#f39c12'
UI_COLOR_WARN   = '#d4ac0d'
UI_COLOR_UNBAN  = '#2ecc71'
UI_COLOR_INFO   = '#3498db'
UI_COLOR_MUTED  = '#95a5a6'

# Status text colours, kept identical across themes so success/danger read the same in light and dark.
UI_STATUS_OK      = '#27ae60'
UI_STATUS_WARN    = '#d4901a'
UI_STATUS_DANGER  = '#c0392b'


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
    """Return True if the Chivalry 2 window is open."""
    try:
        hwnd = win32gui.FindWindow(None, "Chivalry 2  ")
        return hwnd != 0
    except Exception:
        return False

class ChivalryWaitingDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Waiting for Chivalry 2")
        self.setFixedSize(520, 360)

        layout = QVBoxLayout()
        layout.setSpacing(UI_SPACING_INNER)
        layout.setContentsMargins(UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER)

        title = QLabel("Waiting for Chivalry 2")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        instructions = QLabel(
            "Please launch your Chivalry 2 game.\n"
            "The admin tool will automatically continue once the game is detected."
        )
        instructions.setWordWrap(True)
        instructions.setAlignment(Qt.AlignCenter)
        layout.addWidget(instructions)

        layout.addSpacing(UI_PAD_TIGHT)

        self.status_label = QLabel("Searching for Chivalry 2 window...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setMinimumHeight(22)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        layout.addSpacing(UI_PAD_TIGHT)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(UI_SPACING_INNER)

        self.theme_button = QPushButton("Dark Mode")
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setMinimumHeight(34)
        button_layout.addWidget(self.theme_button)

        skip_button = QPushButton("Skip Waiting (Continue Anyway)")
        skip_button.clicked.connect(self.accept)
        skip_button.setMinimumHeight(34)
        button_layout.addWidget(skip_button, 1)

        layout.addLayout(button_layout)

        launch_layout = QHBoxLayout()
        launch_layout.setSpacing(UI_SPACING_INNER)

        steam_button = QPushButton("Launch via Steam")
        steam_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("steam://rungameid/1824220")))
        steam_button.setMinimumHeight(34)
        launch_layout.addWidget(steam_button)

        epic_button = QPushButton("Launch via Epic Games")
        epic_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("com.epicgames.launcher://apps/bd46d4ce259349e5bd8b3ded20274737%3A4c4a6c0767304c9d830f3f36f2b29018%3APeppermint?action=launch&silent=true")))
        epic_button.setMinimumHeight(34)
        launch_layout.addWidget(epic_button)

        xbox_button = QPushButton("Launch via Xbox")
        xbox_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("msxbox://game/?productId=9N7CJX93ZGWN")))
        xbox_button.setMinimumHeight(34)
        launch_layout.addWidget(xbox_button)

        layout.addLayout(launch_layout)

        self.setLayout(layout)

        layout.activate()
        self.adjustSize()

        self.timer = QTimer()
        self.timer.timeout.connect(self.check_window)
        self.timer.start(1000)

        self.update_theme_button()

        # Warm the discord log cache off the UI thread while the user waits for Chivalry.
        _warm_log_cache_async()

    def closeEvent(self, event):
        self.timer.stop()
        event.ignore()
        self.reject()

    def reject(self):
        self.timer.stop()
        super().reject()

    def toggle_theme(self):
        """Toggle between dark and light theme."""
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
        """Update the theme toggle button's label to reflect the current theme."""
        is_dark = load_theme_preference()
        if is_dark:
            self.theme_button.setText("Light Mode")
        else:
            self.theme_button.setText("Dark Mode")

    def check_window(self):

        if check_chivalry_window():
            self.status_label.setText("Chivalry 2 window Detected.")
            self.status_label.setStyleSheet(f"font-weight: bold; color: {UI_STATUS_OK};")
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
    """Standard '?' tooltip badge. Theme-agnostic — uses palette roles."""
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
    """Build a Load/Save/Clear column for a preset slot.

    Buttons are attached to the returned layout as _btn_load / _btn_save / _btn_clear
    so callers can restyle them later.
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
    """Respect per-item Background/Foreground brushes even when a stylesheet targets QListWidget::item.

    Qt 5 drops data-role colours as soon as any ::item rule exists, and overrides them again on
    hover/selection with the theme's colours. We paint the background manually, darken with a
    translucent overlay for hover/selection, then strip those flags so super() can't paint over us.
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
            # Drop state flags so super() doesn't repaint the theme selection on top.
            option.state &= ~QStyle.State_Selected
            option.state &= ~QStyle.State_MouseOver
            option.backgroundBrush = QBrush()

        if isinstance(fg, QBrush):
            option.palette.setBrush(option.palette.Text, fg)
            option.palette.setBrush(option.palette.HighlightedText, fg)

        super().paint(painter, option, index)


def _colored_button_qss(color: str) -> str:
    """QSS for a solid coloured QPushButton. `color` is #rrggbb; hover darkens ~15%, pressed ~30%."""
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
    """QSS for Load buttons whose slot has stored content — green tint with matching hover."""
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

    _notify_in_game_last = True

    @staticmethod
    def _remember_notify_in_game(checked: bool) -> None:
        ActionForm._notify_in_game_last = bool(checked)

    def __init__(self, action_name, player_id, player_name, parent=None):
        super().__init__(parent)
        if action_name.lower() == "note":
            self.setWindowTitle(f"Add a note to Player")
        else:
            self.setWindowTitle(f"{action_name} Player")
        self.resize(480, 420)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModal)

        self.game = None
        try:
            self.game = GameChivalry()
        except Exception as e:
            print(f"[ACTION FORM] Could not connect to Chivalry 2: {e}")

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER)
        main_layout.setSpacing(UI_SPACING_SECTION)

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form_layout.setHorizontalSpacing(UI_SPACING_INNER)
        form_layout.setVerticalSpacing(UI_PAD_TIGHT)
        self.player_id_input = QLineEdit(player_id)
        self.player_id_input.setReadOnly(True)
        self.player_name = QLineEdit(player_name)
        self.player_name.setReadOnly(True)
        form_layout.addRow("Player ID:", self.player_id_input)
        form_layout.addRow("Player Name:", self.player_name)
        default_reason_key = 'last_ban_reason' if action_name.lower() == 'ban' else 'last_kick_reason'
        self.reason_input = QLineEdit(get_persisted_value(default_reason_key, ""))
        self.reason_input.setPlaceholderText("Describe the reason for this action")
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
            quick_preset_layout.setContentsMargins(UI_PAD_SECTION, UI_PAD_TIGHT, UI_PAD_SECTION, UI_PAD_TIGHT)
            quick_preset_layout.setSpacing(UI_SPACING_INNER)

            btn_ffa_24h = QPushButton("FFA 24h")
            btn_ffa_24h.clicked.connect(self.apply_ffa_24h_preset)
            btn_ffa_24h.setStyleSheet(_colored_button_qss(UI_COLOR_INFO))
            quick_preset_layout.addWidget(btn_ffa_24h)

            btn_ffa_perma = QPushButton("FFA Permaban")
            btn_ffa_perma.clicked.connect(self.apply_ffa_perma_preset)
            btn_ffa_perma.setStyleSheet(_colored_button_qss('#e67e22'))
            quick_preset_layout.addWidget(btn_ffa_perma)

            btn_cheating = QPushButton("Cheating")
            btn_cheating.clicked.connect(self.apply_cheating_preset)
            btn_cheating.setStyleSheet(_colored_button_qss(UI_COLOR_BAN))
            quick_preset_layout.addWidget(btn_cheating)

            quick_preset_group.setLayout(quick_preset_layout)
            main_layout.addWidget(quick_preset_group)

        preset_group = QGroupBox("Reason Presets")
        preset_layout = QVBoxLayout()
        preset_layout.setContentsMargins(UI_PAD_SECTION, UI_PAD_TIGHT, UI_PAD_SECTION, UI_PAD_SECTION)
        preset_layout.setSpacing(UI_PAD_TIGHT)

        is_ban = (action_name.lower() == "ban")
        self.preset_slots = list(range(0, 5)) if is_ban else list(range(5, 10))

        # Warnings are Discord-only, so hide the in-game toggle for notes.
        if action_name.lower() != "note":
            self.notify_in_game = QCheckBox("Notify in-game")
            self.notify_in_game.setChecked(ActionForm._notify_in_game_last)
            self.notify_in_game.toggled.connect(ActionForm._remember_notify_in_game)
            main_layout.addWidget(self.notify_in_game)
        else:
            self.notify_in_game = None

        preset_layout.addWidget(
            _make_tip_badge("Hover a Load button to preview the saved reason"
                            + (" and duration" if is_ban else "")),
            0, Qt.AlignRight,
        )

        def _preset_row_label(text):
            lbl = QLabel(text)
            lbl.setProperty("role", "key")
            f = QFont('Segoe UI', 8, QFont.DemiBold)
            lbl.setFont(f)
            return lbl

        load_layout1 = QHBoxLayout()
        load_layout1.setSpacing(UI_PAD_TIGHT)
        self.load_buttons = []
        for idx, slot in enumerate(self.preset_slots):
            btn = QPushButton(f"Slot {idx}")
            btn.clicked.connect(lambda checked, s=slot: self.load_preset(s))
            btn.setMaximumWidth(80)
            self.load_buttons.append(btn)
            load_layout1.addWidget(btn)

        preset_layout.addWidget(_preset_row_label("Load presets"))
        preset_layout.addLayout(load_layout1)

        save_layout1 = QHBoxLayout()
        save_layout1.setSpacing(UI_PAD_TIGHT)
        self.save_buttons = []
        for idx, slot in enumerate(self.preset_slots):
            btn = QPushButton(f"Slot {idx}")
            btn.clicked.connect(lambda checked, s=slot: self.save_preset(s))
            btn.setMaximumWidth(80)
            self.save_buttons.append(btn)
            save_layout1.addWidget(btn)

        preset_layout.addWidget(_preset_row_label("Save / overwrite"))
        preset_layout.addLayout(save_layout1)

        clear_layout1 = QHBoxLayout()
        clear_layout1.setSpacing(UI_PAD_TIGHT)
        self.clear_buttons = []
        for idx, slot in enumerate(self.preset_slots):
            btn = QPushButton("Clear")
            btn.clicked.connect(lambda checked, s=slot: self.clear_preset(s))
            btn.setFixedWidth(80)
            self.clear_buttons.append(btn)
            clear_layout1.addWidget(btn)

        preset_layout.addWidget(_preset_row_label("Clear"))
        preset_layout.addLayout(clear_layout1)

        preset_group.setLayout(preset_layout)
        main_layout.addWidget(preset_group)

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
        """Load a preset's reason (and duration, if ban) into the inputs."""
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
        self.execute_quick_preset("FFA", 24)

    def apply_ffa_perma_preset(self):
        self.execute_quick_preset("FFA", 999999)

    def apply_cheating_preset(self):
        self.execute_quick_preset("Cheating", 999999)

    def execute_quick_preset(self, reason, duration_hours):
        """Run the action with a preset reason and duration, then restore the user's inputs."""
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
        """Save the current reason (and ban duration, if any) into a preset slot."""
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
        """Refresh load-button tooltips and tinting based on saved preset content."""
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
        """Wipe a preset slot."""
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
                    if self.notify_in_game is not None and self.notify_in_game.isChecked():
                        self.game.AdminSay(f"{player_name} has been banned from the server.")
                except Exception as e:
                    QMessageBox.warning(self, "Game Connection Error", f"Could not execute ban command:\n{str(e)}")

            if action_executed:
                set_persisted_value('last_ban_reason', reason)
                set_persisted_value('last_ban_duration', str(time_hour))
                wehbooks.MessageForAdmin(player_id, player_name, reason, time_hour, "ban")
                _schedule_silent_discord_scrape(self)

        elif self.action_name.lower() == "note":
            print(f"[NOTE] Player ID={player_id}, Reason={reason}")
            # Notes only go to Discord — no in-game command.
            wehbooks.MessageForAdmin(player_id, player_name, reason, None, "note")
            set_persisted_value('last_kick_reason', reason)
            _schedule_silent_discord_scrape(self)

        else:
            print(f"[KICK] Player ID={player_id}, Reason={reason}")

            action_executed = False
            if hasattr(self.game, 'kickbyid'):
                try:
                    self.game.kickbyid(player_id, reason)
                    action_executed = True
                    if self.notify_in_game is not None and self.notify_in_game.isChecked():
                        self.game.AdminSay(f"{player_name} has been kicked from the server.")
                except Exception as e:
                    QMessageBox.warning(self, "Game Connection Error", f"Could not execute kick command:\n{str(e)}")

            if action_executed:
                set_persisted_value('last_kick_reason', reason)
                wehbooks.MessageForAdmin(player_id, player_name, reason, None, "kick")
                _schedule_silent_discord_scrape(self)

        self.accept()

def _load_all_sanctions() -> list:
    """Return all discordlogshistory records oldest-first. Read-only — backed by the in-memory cache."""
    return _read_log_cached()[1]


def _load_sanctions_for_player(player_id: str) -> list:
    """Return all discordlogshistory records whose PlayFabID matches player_id."""
    if not player_id:
        return []
    _, _, _, by_pid = _read_log_cached()
    return list(by_pid.get(player_id.upper(), ()))


def _compute_all_player_statuses() -> dict:
    """Single-pass scan of discordlogshistory returning {playfab_id_upper: 'banned' | 'cautioned'}.

    'banned' wins over 'cautioned'. A ban only counts if it's still active *and* its timestamp
    is after the player's most recent unban.
    """
    now           = datetime.datetime.now(datetime.timezone.utc)
    one_week_ago  = now - datetime.timedelta(days=7)
    one_month_ago = now - datetime.timedelta(days=30)
    latest_active_ban = {}   # pid -> latest ts of a still-active ban
    latest_unban      = {}   # pid -> latest unban ts
    kicked            = set()
    cautioned         = set()

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
            dur = record.get('Duration', '') or ''
            if dur:
                try:
                    # Accepts "24h", "24 hours", " 24 ", "24hh", etc.
                    m = re.search(r'-?\d+(?:\.\d+)?', str(dur))
                    if m:
                        hours = float(m.group(0))
                        if ts + datetime.timedelta(hours=hours) > now:
                            prev = latest_active_ban.get(pid)
                            if prev is None or ts > prev:
                                latest_active_ban[pid] = ts
                except Exception:
                    pass
        elif action == 'unban':
            prev = latest_unban.get(pid)
            if prev is None or ts > prev:
                latest_unban[pid] = ts
        elif action in ('kick') and ts >= one_week_ago:
            kicked.add(pid)
        elif action in ('warn', 'note') and ts >= one_month_ago:
            cautioned.add(pid)

    banned = {
        pid for pid, ban_ts in latest_active_ban.items()
        if pid not in latest_unban or latest_unban[pid] < ban_ts
    }

    return {**{p: 'cautioned' for p in cautioned}, **{p: 'banned' for p in banned}}


class _ThemeBus(QObject):
    """Broadcasts theme toggles so live widgets can re-tint without being rebuilt."""
    theme_changed = pyqtSignal(bool)  # True = dark, False = light


_theme_bus = _ThemeBus()


def _format_sanction_timestamp(ts_raw: str) -> tuple:
    """Return (display, tooltip) for UTC timestamp on a sanction card.

    `display` is rendered in local time with a short timezone label (long Windows names
    like 'Eastern Standard Time' get condensed to 'EST'; falls back to 'UTC±HH:MM').
    `tooltip` is the original UTC time so reviewers can cross-reference against logs.
    Both fall back to the raw input on parse failure.
    """
    if not ts_raw:
        return '', ''
    try:
        dt_utc = datetime.datetime.fromisoformat(ts_raw.replace('Z', '+00:00'))
        dt_local = dt_utc.astimezone()
        tz_name = dt_local.strftime('%Z') or ''
        if tz_name and ' ' in tz_name:
            initials = ''.join(w[0] for w in tz_name.split() if w[:1].isupper())
            tz_label = initials or tz_name
        else:
            tz_label = tz_name
        if not tz_label:
            offset = dt_local.utcoffset() or datetime.timedelta(0)
            total_min = int(offset.total_seconds() // 60)
            sign = '+' if total_min >= 0 else '-'
            hh, mm = divmod(abs(total_min), 60)
            tz_label = f'UTC{sign}{hh:02d}:{mm:02d}'
        display = f"{dt_local.strftime('%Y-%m-%d')}  {dt_local.strftime('%H:%M')} {tz_label}"
        tooltip = f"{dt_utc.strftime('%Y-%m-%d %H:%M')} UTC"
        return display, tooltip
    except Exception:
        fallback = ts_raw[:10] + '  ' + ts_raw[11:16] + ' UTC' if len(ts_raw) >= 16 else ts_raw
        return fallback, ts_raw


def _build_sanction_card(record: dict, is_dark: bool = None,
                         embed_playfabid: bool = False) -> QFrame:
    """Build a card widget for one sanction record.

    Pass `is_dark` to avoid re-reading the theme preference when building many cards in a row.
    Pass `embed_playfabid=True` to include a PlayFabID row inside the card — used by the
    sanction search dialog where cards appear without a per-player header.

    Each card subscribes to `_theme_bus.theme_changed` to re-tint live, and unsubscribes on
    destruction so closed dialogs don't leak.
    """
    if is_dark is None:
        is_dark = load_theme_preference()

    action   = record.get('action',   '')
    duration = record.get('Duration', '')
    reason   = record.get('Reason',   '')
    username = record.get('Username', '')

    # Legacy records without an 'action' key are inferred from which fields are populated.
    if action == 'ban'   or (not action and duration):
        action_label, accent = 'BAN',     UI_COLOR_BAN
    elif action == 'kick' or (not action and reason and username):
        action_label, accent = 'KICK',    UI_COLOR_KICK
    elif action in ('warn', 'note'):
        action_label, accent = 'NOTE', UI_COLOR_WARN
    elif action == 'unban' or (not action and not reason):
        action_label, accent = 'UNBAN',   UI_COLOR_UNBAN
    else:
        action_label, accent = (action.upper() or '?'), UI_COLOR_MUTED

    ts_raw = record.get('timestamp', '')
    ts, ts_tooltip = _format_sanction_timestamp(ts_raw)

    frame = QFrame()
    frame.setObjectName("SanctionCard")

    layout = QVBoxLayout(frame)
    layout.setContentsMargins(12, 9, 12, 9)
    layout.setSpacing(5)

    # Header: badge + username + timestamp.
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
    if ts_tooltip:
        lbl_ts.setToolTip(ts_tooltip)
    header.addWidget(lbl_ts)
    layout.addLayout(header)

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

    # Release the closure ref on destruction so sanction dialogs don't leak cards.
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

    # Username lives in the header; only the PlayFabID needs a body row.
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
        self.resize(860, 500)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModal)
        self.player_id = player_id
        self.player_name = player_name

        root = QHBoxLayout(self)
        root.setSpacing(UI_SPACING_SECTION)
        root.setContentsMargins(UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER)

        # Left column: Actions group.
        actions_group = QGroupBox("Actions")
        left = QVBoxLayout(actions_group)
        left.setSpacing(UI_PAD_INNER)
        left.setContentsMargins(UI_PAD_SECTION, UI_PAD_SECTION, UI_PAD_SECTION, UI_PAD_SECTION)

        label = QLabel(
            f"<div align='center'><b>{player_name}</b>"
            f"<br/><small style='color:gray;'>{player_id}</small></div>"
        )
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        label.setMinimumHeight(44)
        left.addWidget(label)
        left.addSpacing(UI_PAD_INNER)

        def _action_btn(text, color, slot):
            b = QPushButton(text)
            b.setMinimumHeight(48)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            f = b.font()
            f.setPointSize(max(f.pointSize(), 10))
            f.setBold(True)
            b.setFont(f)
            b.setStyleSheet(_colored_button_qss(color))
            b.clicked.connect(slot)
            return b

        # Buttons share remaining vertical space evenly — no trailing stretch.
        left.addWidget(_action_btn("Ban",                    UI_COLOR_BAN,   self.ban_player),          1)
        left.addWidget(_action_btn("Kick",                   UI_COLOR_KICK,  self.kick_player),         1)
        left.addWidget(_action_btn("Add a note",                   UI_COLOR_WARN,  self.note_player),         1)
        left.addWidget(_action_btn("Chivalry2Stats Profile", UI_COLOR_INFO,  self.open_player_profile), 1)
        left.addWidget(_action_btn("Copy PlayFabID",         UI_COLOR_UNBAN, self.copy_player_id),      1)

        actions_group.setFixedWidth(250)
        root.addWidget(actions_group)

        # Right column: sanction history. Stored on self so a post-scrape signal can rebuild it.
        self._right_col = QVBoxLayout()
        self._right_col.setSpacing(UI_SPACING_INNER)
        self._rebuild_sanction_history()
        root.addLayout(self._right_col, 1)

        _get_sanctions_bus().sanctionsUpdated.connect(self._rebuild_sanction_history)

    def _rebuild_sanction_history(self):
        """Repopulate the right column with this player's sanctions. Re-runs when a scrape lands new records."""
        # deleteLater schedules cleanup on the next event-loop tick — safe even mid-paint.
        while self._right_col.count():
            item = self._right_col.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

        sanctions = _load_sanctions_for_player(self.player_id)
        now       = datetime.datetime.now(datetime.timezone.utc)
        month_ago = now - datetime.timedelta(days=30)

        # Pin the most recent note if it's within the last 30 days.
        pinned_note = None
        for record in reversed(sanctions):
            if record.get('action') in ('warn', 'note'):
                try:
                    ts = datetime.datetime.fromisoformat(
                        record['timestamp'].replace('Z', '+00:00'))
                    if ts >= month_ago:
                        pinned_note = record
                except Exception:
                    pass
                break

        is_dark = load_theme_preference()

        if pinned_note:
            pin_group = QGroupBox("Active Note (within the last 30 days)")
            pin_layout = QVBoxLayout(pin_group)
            pin_layout.setContentsMargins(UI_PAD_SECTION, UI_PAD_INNER, UI_PAD_SECTION, UI_PAD_INNER)
            pin_layout.addWidget(_build_sanction_card(pinned_note, is_dark))
            self._right_col.addWidget(pin_group)

        count = len(sanctions)
        history_group = QGroupBox(
            f"Sanction History — {count} record{'s' if count != 1 else ''}"
        )
        hist_layout = QVBoxLayout(history_group)
        hist_layout.setContentsMargins(UI_PAD_INNER, UI_PAD_INNER, UI_PAD_INNER, UI_PAD_INNER)

        pinned_id  = pinned_note.get('id') if pinned_note else None
        scrollable = [r for r in reversed(sanctions) if r.get('id') != pinned_id]

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        scroll_content = QWidget()
        scroll_layout  = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(UI_PAD_TIGHT)
        scroll_layout.setContentsMargins(2, 2, 2, 2)

        if scrollable:
            for record in scrollable:
                scroll_layout.addWidget(_build_sanction_card(record, is_dark))
        elif not pinned_note:
            empty = QLabel("No sanctions found in log history.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: gray; font-style: italic; padding: 28px;")
            scroll_layout.addWidget(empty)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        hist_layout.addWidget(scroll)

        self._right_col.addWidget(history_group, 1)

    def copy_player_id(self):
        pyperclip.copy(self.player_id)
        QMessageBox.information(self, "PlayFabID Copied", f"Player's PlayFabID {self.player_id} copied to clipboard.")

    def ban_player(self):
        form = ActionForm("Ban", self.player_id, self.player_name, parent=self)
        form.exec_()

    def kick_player(self):
        form = ActionForm("Kick", self.player_id, self.player_name, parent=self)
        form.exec_()

    def note_player(self):
        form = ActionForm("Note", self.player_id, self.player_name, parent=self)
        form.exec_()

    def open_player_profile(self):
        """Open the player's chivalry2stats.com profile in the browser."""
        profile_url = f"https://chivalry2stats.com/player?id={self.player_id}"

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

class _PlayerListResolveWorker(QObject):
    """Off-thread parser and status resolver for the player list.

    Parses `listplayers` clipboard text into (name, pid) pairs, resolves each player's
    sanction status, and emits one row at a time so the UI fills in progressively rather
    than landing in one batch.

    Pass `text=` for a fresh capture, or `pairs=` to re-resolve statuses for an existing
    roster (used when a scrape lands and only row colours need refreshing).

    Status resolution can be precomputed externally: pass `statuses_event` + `statuses_holder`
    to have the worker wait on a parallel precompute. If it doesn't finish in time, the worker
    computes statuses itself.
    """
    entry    = pyqtSignal(str, str, str)   # name, pid, status_or_empty
    finished = pyqtSignal()

    def __init__(self, text=None, pairs=None, statuses_event=None, statuses_holder=None):
        super().__init__()
        self._text  = text
        self._pairs = pairs
        self._statuses_event  = statuses_event
        self._statuses_holder = statuses_holder

    def run(self):
        try:
            if self._pairs is None:
                pairs = parse_player_list_from_clipboard(self._text or '')
            else:
                pairs = list(self._pairs)
            statuses = self._resolve_statuses()
            for name, pid in pairs:
                self.entry.emit(name, pid, statuses.get(pid.upper(), ''))
                # Yield so Qt can paint each row between emits — without this the queue
                # fills faster than the UI can repaint and rows land in bursts.
                sleep(0.005)
        except Exception as e:
            print(f"[PLAYERS] Resolve worker failed: {e}")
        finally:
            self.finished.emit()

    def _resolve_statuses(self):
        # Prefer a precomputed result from the parallel scan started at refresh time.
        if self._statuses_event is not None and self._statuses_holder is not None:
            if self._statuses_event.wait(timeout=2.0):
                result = self._statuses_holder()
                if result is not None:
                    return result
        return _compute_all_player_statuses()


class PlayersWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Players List")
        self.resize(640, 820)

        self.game = None
        try:
            self.game = GameChivalry()
        except Exception as e:
            print(f"[PLAYERS WINDOW] Could not connect to Chivalry 2: {e}")

        # `players` is the resolved roster (name, pid, status); `filtered_players` is
        # the subset currently shown under the search filter. Both fill incrementally.
        self.players = []
        self.filtered_players = []
        # Pin workers so the daemon thread can keep emitting until they finish.
        self._active_resolve_workers = []
        # Bump on each refresh; older workers' entries are ignored after a new one starts.
        self._resolve_gen = 0

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER)
        main_layout.setSpacing(UI_SPACING_INNER)

        title = QLabel("Players List")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setAlignment(Qt.AlignLeft)
        main_layout.addWidget(title)

        refresh_btn = QPushButton("Refresh Player List")
        refresh_btn.setMinimumHeight(36)
        refresh_btn.clicked.connect(self.refresh_player_list)
        refresh_btn.setStyleSheet(_colored_button_qss(UI_ACCENT))
        main_layout.addWidget(refresh_btn)

        info_row = QHBoxLayout()
        info_row.setSpacing(UI_SPACING_INNER)
        self.server_label = QLabel("Server: -")
        self.player_count_label = QLabel("Players: 0")
        self.server_label.setStyleSheet("font-weight: 600;")
        self.player_count_label.setStyleSheet("font-weight: 600;")
        info_row.addWidget(self.server_label)
        info_row.addStretch(1)
        info_row.addWidget(self.player_count_label)
        main_layout.addLayout(info_row)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search by ID or Player Name...")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.textChanged.connect(self.filter_players)
        main_layout.addWidget(self.search_bar)

        self.player_list = QListWidget()
        self.player_list.setItemDelegate(_SanctionedRowDelegate(self.player_list))
        main_layout.addWidget(self.player_list, 1)

        self.player_list.itemClicked.connect(self.open_player_actions)
        self.setLayout(main_layout)

        # Re-resolve row colours when a scrape lands. The roster itself comes from a
        # ListPlayers round-trip, so no new game query is needed.
        _get_sanctions_bus().sanctionsUpdated.connect(self._on_sanctions_updated)

        if self.game is not None:
            self.refresh_player_list()

    def _on_sanctions_updated(self):
        # Re-resolve against the cached roster so row colours pick up the new sanction state.
        if self.players:
            pairs = [(n, p) for (n, p, _s) in self.players]
            self._start_resolve_worker(pairs=pairs)

    def refresh_player_list(self):
        self.awaiting_player_list = True

        # Run the sanction-log scan in parallel with the game's listplayers round-trip,
        # so statuses are usually ready by the time we parse the clipboard.
        self._statuses_event  = threading.Event()
        self._statuses_result = None
        threading.Thread(
            target=self._precompute_statuses_bg,
            name="player-status-precompute",
            daemon=True,
        ).start()

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

        QTimer.singleShot(100, self._parse_player_list_from_clipboard)

    def _precompute_statuses_bg(self):
        """Run the sanction-log scan and stash the result for the resolve worker to pick up."""
        try:
            self._statuses_result = _compute_all_player_statuses()
        except Exception as e:
            print(f"[PLAYERS] Status precompute failed: {e}")
            self._statuses_result = {}
        finally:
            self._statuses_event.set()

    def _parse_player_list_from_clipboard(self):
        if not getattr(self, 'awaiting_player_list', False):
            return
        try:
            text = pyperclip.paste()
        except Exception:
            text = ""
        if " - " not in (text or ""):
            return
        # Update the server name + player count immediately for instant feedback.
        self._update_info_from_text(text)
        self._start_resolve_worker(text=text)
        self.awaiting_player_list = False

    def _start_resolve_worker(self, text=None, pairs=None):
        """Start a background resolve. Clears the list and fills it back in as the worker streams entries."""
        self._resolve_gen += 1
        gen = self._resolve_gen

        self.players = []
        self.filtered_players = []
        self.player_list.clear()

        # The fresh-refresh path hands off the precompute kicked off in refresh_player_list.
        # The sanctions-update path (pairs supplied) has no precompute, so the worker computes inline.
        if pairs is None:
            statuses_event  = getattr(self, '_statuses_event', None)
            statuses_holder = lambda: getattr(self, '_statuses_result', None)
        else:
            statuses_event  = None
            statuses_holder = None

        worker = _PlayerListResolveWorker(
            text=text,
            pairs=pairs,
            statuses_event=statuses_event,
            statuses_holder=statuses_holder,
        )
        self._active_resolve_workers.append(worker)
        # Force QueuedConnection: the worker is constructed on the UI thread but runs on a
        # plain daemon thread, so AutoConnection would pick DirectConnection and touch UI
        # widgets off-thread. Queued posts each emit to the UI event loop instead.
        worker.entry.connect(
            lambda name, pid, status, g=gen: self._on_resolve_entry(name, pid, status, g),
            Qt.QueuedConnection,
        )
        worker.finished.connect(
            lambda w=worker, g=gen: self._on_resolve_finished(w, g),
            Qt.QueuedConnection,
        )

        threading.Thread(
            target=worker.run,
            name="player-list-resolve",
            daemon=True,
        ).start()

    def _on_resolve_entry(self, name, pid, status, gen):
        # Drop entries from a worker that was superseded by a newer refresh.
        if gen != self._resolve_gen:
            return
        try:
            entry = (name, pid, status)
            self.players.append(entry)
            term = self.search_bar.text().strip().lower()
            if term and term not in name.lower() and term not in pid.lower():
                return
            self.filtered_players.append(entry)
            self._append_player_item(name, pid, status)
        except RuntimeError:
            # Dialog closed mid-stream — widgets are gone.
            pass

    def _on_resolve_finished(self, worker, gen):
        try:
            self._active_resolve_workers.remove(worker)
        except ValueError:
            pass
        if gen != self._resolve_gen:
            return
        # ListPlayers() typed into the game console, leaving Chivalry on top — take focus back.
        self._bring_to_foreground()

    def _bring_to_foreground(self):
        """Raise the admin tool above the game.

        raise_() + activateWindow() alone is unreliable when another process owns the
        foreground (Windows blocks unsolicited focus changes), so we fall back to win32.
        """
        try:
            self.raise_()
            self.activateWindow()
            parent = self.parent()
            if parent is not None:
                parent.raise_()
                parent.activateWindow()
                self.raise_()
                self.activateWindow()
        except Exception:
            pass
        try:
            hwnd = int(self.winId())
            win32gui.SetForegroundWindow(hwnd)
        except Exception as e:
            print(f"[FOCUS] Could not reclaim foreground: {e}")

    def _append_player_item(self, name, pid, status):
        item = QListWidgetItem(f"{name} - {pid}")
        if status == 'banned':
            item.setBackground(QBrush(QColor(UI_COLOR_BAN)))
            item.setForeground(QBrush(QColor('white')))
        elif status == 'kicked':
            item.setBackground(QBrush(QColor(UI_COLOR_KICK)))
            item.setForeground(QBrush(QColor('white')))
        elif status == 'cautioned':
            item.setBackground(QBrush(QColor(UI_COLOR_WARN)))
            item.setForeground(QBrush(QColor('white')))
        self.player_list.addItem(item)

    def populate_list(self):
        """Re-render the list from `self.filtered_players`. Pure UI — statuses are already attached."""
        self.player_list.clear()
        for name, pid, status in self.filtered_players:
            self._append_player_item(name, pid, status)

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
        # Filter the in-memory roster directly — statuses are already attached.
        term = text.strip().lower()
        if term:
            self.filtered_players = [
                (name, pid, status) for (name, pid, status) in self.players
                if term in name.lower() or term in pid.lower()
            ]
        else:
            self.filtered_players = list(self.players)
        self.populate_list()

    def open_player_actions(self, item):
        text = item.text()
        if " - " not in text:
            return
        name, pid = text.split(" - ", 1)
        dialog = PlayerActionDialog(pid, name, parent=self)
        dialog.exec_()

class AddTimeDialog(QDialog):
    """Dialog for adding minutes to the current map."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Time")
        self.setMinimumWidth(420)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(UI_SPACING_SECTION)
        main_layout.setContentsMargins(UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER)

        title_label = QLabel("Add time to the current map")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        main_layout.addWidget(title_label)

        desc_label = QLabel("Number of minutes to add:")
        desc_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(desc_label)

        self.time_input = QLineEdit()
        self.time_input.setPlaceholderText("e.g., 5")
        self.time_input.setAlignment(Qt.AlignCenter)
        self.time_input.setValidator(QIntValidator(1, 500, self))
        self.time_input.setMinimumHeight(34)
        main_layout.addWidget(self.time_input)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(UI_SPACING_INNER)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumHeight(34)
        self.cancel_button.clicked.connect(self.reject)

        self.ok_button = QPushButton("Add Time")
        self.ok_button.setMinimumHeight(34)
        self.ok_button.setDefault(True)
        self.ok_button.setStyleSheet(_colored_button_qss(UI_ACCENT))
        self.ok_button.clicked.connect(self.accept)

        button_layout.addStretch(1)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def get_time(self):
        return self.time_input.text().strip()

    def set_time(self, time_value):
        self.time_input.setText(time_value)

class UnbanPlayerDialog(QDialog):
    """Dialog for unbanning a player by PlayFabID."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Unban Player")
        self.setMinimumWidth(460)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(UI_SPACING_SECTION)
        main_layout.setContentsMargins(UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER)

        title_label = QLabel("Unban Player")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        main_layout.addWidget(title_label)

        desc_label = QLabel("Enter the player's PlayFabID:")
        desc_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(desc_label)

        self.playfabid_input = QLineEdit()
        self.playfabid_input.setPlaceholderText("e.g., 1234567890ABCDEF")
        self.playfabid_input.setAlignment(Qt.AlignCenter)
        self.playfabid_input.setStyleSheet("font-family: Consolas, 'Courier New', monospace; font-size: 11pt;")
        self.playfabid_input.setMaxLength(16)
        self.playfabid_input.setMinimumHeight(34)
        main_layout.addWidget(self.playfabid_input)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(UI_SPACING_INNER)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumHeight(34)
        self.cancel_button.clicked.connect(self.reject)

        self.ok_button = QPushButton("Unban Player")
        self.ok_button.setMinimumHeight(34)
        self.ok_button.setDefault(True)
        self.ok_button.setStyleSheet(_colored_button_qss(UI_COLOR_UNBAN))
        self.ok_button.clicked.connect(self.accept)

        button_layout.addStretch(1)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def get_playfabid(self):
        return self.playfabid_input.text().strip()

class ConsoleKeyDialog(QDialog):
    def __init__(self, current_vk: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Console Key")
        self.resize(460, 220)

        self.captured_vk = None

        layout = QVBoxLayout()
        layout.setContentsMargins(UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER)
        layout.setSpacing(UI_SPACING_SECTION)

        title = QLabel("Configure Console Key")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title)

        instructions = QLabel(
            "Press the key you use to open the in-game console.\n"
            "The key code will be saved and used for console operations."
        )
        instructions.setWordWrap(True)
        instructions.setAlignment(Qt.AlignCenter)
        layout.addWidget(instructions)

        self.status = QLabel("Waiting for key press...")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        layout.addWidget(self.status)

        if current_vk:
            try:
                vk_int = int(current_vk)
                self.status.setText(f"Current configured key: VK {vk_int}\n(press a key to change)")
            except Exception:
                pass

        layout.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ok_button = buttons.button(QDialogButtonBox.Ok)
        self.ok_button.setEnabled(False)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def keyPressEvent(self, event):
        try:
            vk = event.nativeVirtualKey() if hasattr(event, 'nativeVirtualKey') else None
        except Exception:
            vk = None
        if vk is None or vk == 0:
            # Fall back to the Qt key code for ASCII keys.
            vk = event.key()
        self.captured_vk = int(vk)
        self.status.setText(f"Captured key: VK {self.captured_vk}. Click OK to save or press another key.")
        self.ok_button.setEnabled(True)

class SanctionSearchDialog(QDialog):
    """Full-history sanctions search by Username and/or PlayFabID.

    Tuned for large histories: search is debounced and only the first
    `_RENDER_CAP_DEFAULT` cards are rendered up front, with a "Show all" button
    to lift the cap. Card construction dominates refresh latency.
    """

    _RENDER_CAP_DEFAULT = 50
    _SEARCH_DEBOUNCE_MS = 200

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sanction History Search")
        self.resize(760, 640)
        self.setModal(True)

        self._all_records = list(reversed(_load_all_sanctions()))  # most-recent first
        self._render_cap  = self._RENDER_CAP_DEFAULT

        root = QVBoxLayout()
        root.setContentsMargins(UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER)
        root.setSpacing(UI_SPACING_INNER)
        self.setLayout(root)

        # Search bar + inline count label.
        bar_row = QHBoxLayout()
        bar_row.setSpacing(UI_SPACING_INNER)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search by Username or PlayFabID…")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.textChanged.connect(lambda _: self._on_text_changed())
        bar_row.addWidget(self._search_input, 1)

        self._result_label = QLabel()
        self._result_label.setStyleSheet("color: gray; font-style: italic; font-size: 12pt; padding: 0px 10px 0px 0px;")
        self._result_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._result_label.setMinimumWidth(80)
        bar_row.addWidget(self._result_label, 0)

        root.addLayout(bar_row)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._refresh)

        # Reload from the cache when a scrape lands — otherwise new sanctions issued while
        # the dialog is open wouldn't appear.
        _get_sanctions_bus().sanctionsUpdated.connect(self._on_sanctions_updated)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.NoFrame)
        root.addWidget(self._scroll, 1)

        self._refresh()

    def _on_text_changed(self):
        # Reset the render cap so a new query doesn't inherit "Show all" from the previous one.
        self._render_cap = self._RENDER_CAP_DEFAULT
        self._search_timer.start(self._SEARCH_DEBOUNCE_MS)

    def _on_sanctions_updated(self):
        # Re-pull from the cache (the scrape invalidated it) and re-render with the current filter.
        self._all_records = list(reversed(_load_all_sanctions()))
        self._refresh()

    def _show_all(self, total: int):
        self._render_cap = total
        self._refresh()

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

        content = QWidget()
        layout  = QVBoxLayout(content)
        layout.setSpacing(6)
        layout.setContentsMargins(4, 4, 4, 4)

        if matches:
            visible  = matches[:self._render_cap]
            overflow = count - len(visible)
            is_dark  = load_theme_preference()
            for record in visible:
                layout.addWidget(_build_sanction_card(record, is_dark, embed_playfabid=True))
            if overflow > 0:
                more_btn = QPushButton(f"Show all {count} records ({overflow} more)… (Expect a few seconds freeze.)")
                more_btn.setMinimumHeight(34)
                more_btn.clicked.connect(lambda _=False, n=count: self._show_all(n))
                layout.addWidget(more_btn)
        else:
            empty = QLabel("No matching records found.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: gray; font-style: italic; padding: 24px;")
            layout.addWidget(empty)

        layout.addStretch()
        self._scroll.setWidget(content)


class _DiscordScrapeWorker(QObject):
    """Signal bridge for the Discord log scrape running on a daemon thread.

    Created on the UI thread so AutoConnection routes every emit back to UI slots.
    `finished` is always emitted last so the caller can close the progress dialog.
    """
    progress = pyqtSignal(str)         # progress dialog status text
    error    = pyqtSignal(str, str)    # title, body — fatal; UI closes dialog + critical
    warning  = pyqtSignal(str, str)    # title, body — non-fatal; UI closes dialog + warning
    finished = pyqtSignal()            # emitted last; UI closes dialog if still open


class AdminDashboard(QWidget):
    def __init__(self):
        super().__init__()

        # Try to connect to Chivalry 2, but it's OK if it's not running yet.
        self.game = None
        self.chivalry_connected = False

        self.setWindowTitle("Admin Dashboard")
        self.resize(1400, 520)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(UI_PAD_OUTER + 6, UI_PAD_OUTER - 2, UI_PAD_OUTER + 6, UI_PAD_OUTER - 2)
        main_layout.setSpacing(UI_SPACING_SECTION)
        title = QLabel("Admin Dashboard")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        status_group = QGroupBox("Server Status")
        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(UI_PAD_SECTION, UI_PAD_INNER, UI_PAD_SECTION, UI_PAD_INNER)
        status_layout.setSpacing(UI_PAD_TIGHT)

        self.status_label = QLabel("Checking connection...")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.status_label)

        self.webhook_status_label = QLabel()
        self.webhook_status_label.setAlignment(Qt.AlignCenter)
        self.update_webhook_status()
        status_layout.addWidget(self.webhook_status_label)

        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)

        admin_message_group = QGroupBox("Admin Message")
        admin_message_layout = QVBoxLayout()
        admin_message_layout.setContentsMargins(UI_PAD_SECTION, UI_PAD_INNER, UI_PAD_SECTION, UI_PAD_INNER)
        admin_message_layout.setSpacing(UI_PAD_INNER)

        admin_input_row = QHBoxLayout()
        admin_input_row.setSpacing(UI_SPACING_INNER)
        self.admin_message_input = QLineEdit()
        self.admin_message_input.setPlaceholderText("Type the admin message to send...")
        self.admin_message_input.setText(get_persisted_value('last_admin_msg', ""))
        self.admin_message_input.editingFinished.connect(lambda: set_persisted_value('last_admin_msg', self.admin_message_input.text().strip()))
        admin_input_row.addWidget(self.admin_message_input, 1)
        btn_send_admin_message = QPushButton("Send Admin Message")
        btn_send_admin_message.setMinimumWidth(170)
        btn_send_admin_message.setStyleSheet(_colored_button_qss(UI_ACCENT))
        btn_send_admin_message.clicked.connect(self.send_admin_message)
        admin_input_row.addWidget(btn_send_admin_message)
        admin_message_layout.addLayout(admin_input_row)

        admin_preset_layout = QVBoxLayout()
        admin_preset_layout.setSpacing(UI_PAD_TIGHT)
        self.admin_load_buttons = []
        self.admin_save_buttons = []
        self.admin_clear_buttons = []

        admin_preset_layout.addWidget(
            _make_tip_badge("Hover a Load button to preview the saved message"),
            0, Qt.AlignRight,
        )

        admin_columns_row = QHBoxLayout()
        admin_columns_row.setSpacing(UI_SPACING_INNER)
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
        server_message_layout.setContentsMargins(UI_PAD_SECTION, UI_PAD_INNER, UI_PAD_SECTION, UI_PAD_INNER)
        server_message_layout.setSpacing(UI_PAD_INNER)

        server_input_row = QHBoxLayout()
        server_input_row.setSpacing(UI_SPACING_INNER)
        self.server_message_input = QLineEdit()
        self.server_message_input.setPlaceholderText("Type the server message to send...")
        self.server_message_input.setText(get_persisted_value('last_server_msg', ""))
        self.server_message_input.editingFinished.connect(lambda: set_persisted_value('last_server_msg', self.server_message_input.text().strip()))
        server_input_row.addWidget(self.server_message_input, 1)
        btn_send_server_message = QPushButton("Send Server Message")
        btn_send_server_message.setMinimumWidth(170)
        btn_send_server_message.setStyleSheet(_colored_button_qss(UI_ACCENT))
        btn_send_server_message.clicked.connect(self.send_server_message)
        server_input_row.addWidget(btn_send_server_message)
        server_message_layout.addLayout(server_input_row)

        server_preset_layout = QVBoxLayout()
        server_preset_layout.setSpacing(UI_PAD_TIGHT)
        self.server_load_buttons = []
        self.server_save_buttons = []
        self.server_clear_buttons = []

        server_preset_layout.addWidget(
            _make_tip_badge("Hover a Load button to preview the saved message"),
            0, Qt.AlignRight,
        )

        server_columns_row = QHBoxLayout()
        server_columns_row.setSpacing(UI_SPACING_INNER)
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
        commands_layout.setContentsMargins(UI_PAD_SECTION, UI_PAD_INNER, UI_PAD_SECTION, UI_PAD_INNER)
        commands_layout.setSpacing(UI_SPACING_INNER)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(UI_SPACING_INNER)
        btn_players = QPushButton("Players List")
        btn_players.setMinimumHeight(34)
        btn_players.clicked.connect(self.open_players_window)
        actions_row.addWidget(btn_players)

        btn_add_time = QPushButton("Add Time")
        btn_add_time.setMinimumHeight(34)
        btn_add_time.clicked.connect(self.open_add_time_dialog)
        actions_row.addWidget(btn_add_time)

        btn_unban = QPushButton("Unban Player")
        btn_unban.setMinimumHeight(34)
        btn_unban.clicked.connect(self.open_unban_dialog)
        actions_row.addWidget(btn_unban)

        commands_layout.addLayout(actions_row)

        arb_group = QGroupBox("Arbitration")
        arb_layout = QVBoxLayout()
        arb_layout.setContentsMargins(UI_PAD_SECTION, UI_PAD_INNER, UI_PAD_SECTION, UI_PAD_INNER)
        arb_layout.setSpacing(UI_PAD_INNER)

        btn_first_to = QPushButton("Match Arbitration (First To)")
        btn_first_to.setMinimumHeight(34)
        btn_first_to.clicked.connect(self.open_first_to_window)
        arb_layout.addWidget(btn_first_to)

        btn_random_pick = QPushButton("Random Pick")
        btn_random_pick.setMinimumHeight(34)
        btn_random_pick.clicked.connect(self.open_random_pick_dialog)
        arb_layout.addWidget(btn_random_pick)

        arb_group.setLayout(arb_layout)
        commands_layout.addWidget(arb_group)

        admin_server_row = QHBoxLayout()
        admin_server_row.setSpacing(UI_SPACING_SECTION)
        admin_message_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        server_message_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        admin_server_row.addWidget(admin_message_group, 1)
        admin_server_row.addWidget(server_message_group, 1)
        commands_layout.addLayout(admin_server_row)

        commands_group.setLayout(commands_layout)
        main_layout.addWidget(commands_group)

        btn_sanction_search = QPushButton("Sanction History")
        btn_sanction_search.setMinimumHeight(34)
        btn_sanction_search.clicked.connect(lambda: SanctionSearchDialog(self).exec_())
        main_layout.addWidget(btn_sanction_search)

        settings_group = QGroupBox("Settings")
        settings_layout = QVBoxLayout()
        settings_layout.setContentsMargins(UI_PAD_SECTION, UI_PAD_INNER, UI_PAD_SECTION, UI_PAD_INNER)
        settings_layout.setSpacing(UI_PAD_TIGHT)

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

        self.fetch_discord_channel_messages(silent=True)

        self.players_window = None
        self.first_to_window = None
        self.add_time_dialog = None
        self.unban_player_dialog = None
        self.console_key_dialog = None
        self.random_pick_dialog = None

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
        """Poll for the Chivalry window and (re)connect or disconnect accordingly."""
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
        if self.chivalry_connected:
            self.status_label.setText("● Chivalry 2 Connected")
            self.status_label.setStyleSheet(f"color: {UI_STATUS_OK}; font-weight: bold;")
        else:
            self.status_label.setText("● Chivalry 2 Not Connected")
            self.status_label.setStyleSheet(f"color: {UI_STATUS_DANGER}; font-weight: bold;")

    def update_webhook_status(self):
        status = wehbooks.get_webhook_status()

        ok_style = f"color: {UI_STATUS_OK}; font-weight: 600;"
        warn_style = f"color: {UI_STATUS_WARN}; font-weight: 600;"

        if status['primary_active'] and status['secondary_active']:
            self.webhook_status_label.setText("Discord: Primary + Secondary Active")
            self.webhook_status_label.setStyleSheet(ok_style)
        elif status['primary_active']:
            self.webhook_status_label.setText("Discord: Primary Active")
            self.webhook_status_label.setStyleSheet(ok_style)
        elif status['secondary_active']:
            self.webhook_status_label.setText("Discord: Secondary Active")
            self.webhook_status_label.setStyleSheet(ok_style)
        else:
            self.webhook_status_label.setText("Discord: Not Configured")
            self.webhook_status_label.setStyleSheet(warn_style)

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
        if self.add_time_dialog is not None and self.add_time_dialog.isVisible():
            self.add_time_dialog.raise_()
            self.add_time_dialog.activateWindow()
            return

        self.add_time_dialog = AddTimeDialog(parent=self)
        self.add_time_dialog.set_time(get_persisted_value('last_add_time', ""))

        def on_accepted():
            added_time = self.add_time_dialog.get_time()
            print(f" +{added_time}min")

            time_added = False
            if self.chivalry_connected and hasattr(self.game, 'AddTime'):
                try:
                    self.game.AddTime(added_time)
                    time_added = True
                except Exception as e:
                    QMessageBox.warning(self, "Game Error", f"Failed to add time to game:\n{str(e)}")

            if time_added:
                set_persisted_value('last_add_time', str(added_time))
        self.add_time_dialog.accepted.connect(on_accepted)
        self.add_time_dialog.finished.connect(lambda: setattr(self, 'add_time_dialog', None))

        self.add_time_dialog.show()
        self.add_time_dialog.raise_()
        self.add_time_dialog.activateWindow()

    def open_unban_dialog(self):
        """Open the dialog to unban a player by PlayFabID."""
        if self.unban_player_dialog is not None and self.unban_player_dialog.isVisible():
            self.unban_player_dialog.raise_()
            self.unban_player_dialog.activateWindow()
            return

        self.unban_player_dialog = UnbanPlayerDialog(parent=self)

        def on_accepted():
            player_id = self.unban_player_dialog.get_playfabid()

            # PlayFabIDs are exactly 16 uppercase alphanumeric characters.
            if not player_id or len(player_id) != 16 or not player_id.isupper() or not player_id.isalnum():
                QMessageBox.warning(
                    self,
                    "Invalid PlayFabID",
                    "PlayFabID must be exactly 16 characters long and contain only uppercase letters and numbers."
                )
                return

            print(f"[UNBAN] Player ID={player_id}")

            if self.chivalry_connected and hasattr(self.game, 'unbanbyid'):
                try:
                    self.game.unbanbyid(player_id)

                    if hasattr(self.game, 'ServerSay'):
                        try:
                            self.game.ServerSay(f"{player_id} unban successful.")
                        except Exception as e:
                            print(f"[UNBAN] Could not send ServerSay message: {e}")

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
                            # Only notify Discord once the user confirms the unban actually went through.
                            wehbooks.MessageForAdmin(player_id, "N/A", None, None, "unban")
                            _schedule_silent_discord_scrape(self)
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

                    # Wait for the ServerSay message to reach the game before asking the user.
                    QTimer.singleShot(2000, ask_confirmation)

                except Exception as e:
                    QMessageBox.warning(self, "Game Connection Error", f"Could not execute unban command:\n{str(e)}")
            else:
                QMessageBox.warning(self, "Not Connected", "Cannot unban player - Chivalry 2 is not connected.\n\nPlease ensure Chivalry 2 is running.")

        self.unban_player_dialog.accepted.connect(on_accepted)
        self.unban_player_dialog.finished.connect(lambda: setattr(self, 'unban_player_dialog', None))

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
        self.first_to_window.show()
        self.first_to_window.raise_()
        self.first_to_window.activateWindow()

    def open_random_pick_dialog(self):
        if self.random_pick_dialog is not None and self.random_pick_dialog.isVisible():
            self.random_pick_dialog.raise_()
            self.random_pick_dialog.activateWindow()
            return
        self.random_pick_dialog = RandomPickDialog(parent=self)
        self.random_pick_dialog.setAttribute(Qt.WA_DeleteOnClose, True)
        self.random_pick_dialog.finished.connect(lambda: setattr(self, 'random_pick_dialog', None))
        self.random_pick_dialog.show()
        self.random_pick_dialog.raise_()
        self.random_pick_dialog.activateWindow()

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
        """Prompt the user for the Discord webhook URLs and persist them."""
        current_primary_url   = get_persisted_value('primary_webhook', '')
        current_secondary_url = get_persisted_value('secondary_webhook', '')
        if current_primary_url   == 'None': current_primary_url   = ''
        if current_secondary_url == 'None': current_secondary_url = ''

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

        # Only prompt for a secondary URL if the primary one is set.
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

            webhook_initialized = wehbooks.initialize_webhook()
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
        """Prompt the user for their Discord user ID and persist it."""
        current_discord_user_id = get_persisted_value('discord_user_id', '')
        if current_discord_user_id == 'None':
            current_discord_user_id = ''

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
        """Prompt for the Discord Bot Token used to scrape the log channel."""
        current_token = get_persisted_value('discord_bot_token', '')
        if current_token == 'None':
            current_token = ''

        token, ok = self.prompt_wide_text(
            "Discord Bot Token",
            "Enter your Discord Bot Token:\n"
            "(Leave empty to clear)",
            current_token
        )
        if not ok:
            return

        token = token.strip()
        set_persisted_value('discord_bot_token', token if token else 'None')

    def configure_discord_channel_id(self):
        """Prompt for the Discord channel ID to scrape."""
        current_channel = get_persisted_value('discord_channel_id', '')
        if current_channel == 'None':
            current_channel = ''

        channel_id, ok = QInputDialog.getText(
            self,
            "Discord Channel ID",
            "Enter the Discord Channel ID to scrape:\n(Leave empty to clear)",
            text=current_channel
        )
        if not ok:
            return

        channel_id = channel_id.strip()
        if channel_id and not channel_id.isdigit():
            QMessageBox.warning(self, "Invalid Channel ID", "Channel ID must be a numeric value.")
            return

        set_persisted_value('discord_channel_id', channel_id if channel_id else 'None')

    def fetch_discord_channel_messages(self, silent: bool = False):
        """Fetch webhook messages from the configured Discord channel into discordlogshistory.

        Runs on a daemon worker thread. Manual scrapes mount a non-blocking progress dialog
        driven by worker signals; silent scrapes print to stdout instead.

        `silent=True` is used by auto-scrapes (post-action follow-up, startup). A non-blocking
        lock dedupes back-to-back silent triggers.
        """
        if silent:
            if not _silent_scrape_lock.acquire(blocking=False):
                # Another silent scrape is in flight — the next event will retrigger.
                return

        def _release_lock():
            if silent:
                try:
                    _silent_scrape_lock.release()
                except RuntimeError:
                    pass

        token = get_persisted_value('discord_bot_token', '')
        channel_id = get_persisted_value('discord_channel_id', '')

        if not token or token == 'None':
            _release_lock()
            if not silent:
                QMessageBox.warning(
                    self, "Not Configured",
                    "No Discord Bot Token configured.\n"
                    "Please use 'Set Discord Bot Token' first."
                )
            else:
                print("[SCRAPE] Skipped auto-scrape: bot token not configured")
            return
        if not channel_id or channel_id == 'None':
            _release_lock()
            if not silent:
                QMessageBox.warning(
                    self, "Not Configured",
                    "No Discord Channel ID configured.\n"
                    "Please use 'Set Discord Channel ID' first."
                )
            else:
                print("[SCRAPE] Skipped auto-scrape: channel id not configured")
            return

        worker = _DiscordScrapeWorker()
        # Pin the worker to the dashboard so it isn't GC'd mid-emit.
        self._active_scrape_workers = getattr(self, '_active_scrape_workers', [])
        self._active_scrape_workers.append(worker)

        if silent:
            set_text_cb = lambda txt: print(f"[SCRAPE] {txt}")
            err_cb      = lambda t, b: print(f"[SCRAPE] {t}: {b}")
            warn_cb     = lambda t, b: print(f"[SCRAPE] {t}: {b}")
        else:
            progress_dialog = QDialog(self)
            progress_dialog.setWindowTitle("Fetching Messages...")
            progress_dialog.setModal(True)
            pd_layout = QVBoxLayout()
            pd_layout.setContentsMargins(UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER)
            pd_layout.setSpacing(UI_SPACING_INNER)
            pd_label = QLabel("Connecting to Discord API, please wait...")
            pd_label.setAlignment(Qt.AlignCenter)
            pd_layout.addWidget(pd_label)
            pd_progress = QProgressBar()
            pd_progress.setRange(0, 0)
            pd_progress.setTextVisible(False)
            pd_layout.addWidget(pd_progress)
            progress_dialog.setLayout(pd_layout)
            progress_dialog.resize(420, 120)
            progress_dialog.show()

            def _close_dialog():
                try:
                    progress_dialog.close()
                except Exception:
                    pass

            def _on_error(title, body):
                _close_dialog()
                QMessageBox.critical(self, title, body)

            def _on_warning(title, body):
                _close_dialog()
                QMessageBox.warning(self, title, body)

            worker.progress.connect(pd_label.setText)
            worker.error.connect(_on_error)
            worker.warning.connect(_on_warning)
            worker.finished.connect(_close_dialog)

            set_text_cb = worker.progress.emit
            err_cb      = worker.error.emit
            warn_cb     = worker.warning.emit

        def _on_done():
            try:
                self._active_scrape_workers.remove(worker)
            except (ValueError, AttributeError):
                pass
        worker.finished.connect(_on_done)

        def _run():
            try:
                try:
                    self._fetch_discord_channel_messages_impl(
                        token, channel_id, set_text_cb, err_cb, warn_cb
                    )
                except Exception as e:
                    err_cb("Error", f"An unexpected error occurred:\n{str(e)}")
            finally:
                worker.finished.emit()
                _release_lock()

        threading.Thread(
            target=_run,
            name=f"discord-scrape-{'silent' if silent else 'manual'}",
            daemon=True,
        ).start()

    def _fetch_discord_channel_messages_impl(self, token, channel_id,
                                              set_text_cb, err_cb, warn_cb):
        """Body of the scrape. Runs on a daemon worker thread, never touches Qt directly.

        All UI updates flow through the callbacks (worker signals for manual scrapes,
        stdout for silent ones). The wrapping `fetch_discord_channel_messages` handles
        config validation and progress-dialog lifecycle.
        """
        import urllib.request
        import urllib.error
        import json
        import time

        _pd_set_text = set_text_cb
        _err = err_cb
        def _pd_close():
            pass

        # Read the existing log up front so we can early-stop once incoming messages
        # match cached records. Dicts here are the cache's own references — legacy name
        # enrichment below mutates them in place, then we invalidate the cache.
        all_records_view, _, by_id_view, _ = _read_log_cached()
        existing_records = list(all_records_view)
        existing_ids_set = set(by_id_view.keys())
        ids_missing_name = set()
        for rec in existing_records:
            if not isinstance(rec, dict):
                continue
            raw_mid = rec.get('ModeratorID', '')
            if raw_mid and not rec.get('ModeratorName', ''):
                # Handles raw mentions like "<@!123>" or buggy "!123" values from older versions.
                mid = _extract_mention_id(raw_mid)
                if mid:
                    ids_missing_name.add(mid)

        all_messages = []
        before = None
        headers = {
            'Authorization': f'Bot {token}',
            'Content-Type': 'application/json',
            'User-Agent': 'OVAAdminTool/1.0'
        }

        # Cap Discord's retry_after so a pathological response can't lock the UI.
        MAX_RETRY_AFTER = 60.0

        # Stop paginating once this many consecutive incoming messages already exist on disk.
        # Non-webhook messages don't reset the counter, so they don't break early-stop in
        # mixed channels.
        EARLY_STOP_THRESHOLD = 10
        consecutive_matches = 0
        early_stop          = False

        try:
            while True:
                url = f'https://discord.com/api/v10/channels/{channel_id}/messages?limit=100'
                if before:
                    url += f'&before={before}'

                req = urllib.request.Request(url, headers=headers)

                try:
                    with urllib.request.urlopen(req, timeout=15) as response:
                        raw = response.read()
                    try:
                        data = json.loads(raw.decode('utf-8', errors='replace'))
                    except Exception:
                        _pd_close()
                        _err("Invalid Response",
                             "Discord returned a response that could not be decoded as JSON.")
                        return
                except urllib.error.HTTPError as e:
                    if e.code == 429:
                        try:
                            error_data = json.loads(e.read().decode('utf-8', errors='replace'))
                            retry_after = float(error_data.get('retry_after', 1.0))
                        except Exception:
                            retry_after = 1.0
                        retry_after = max(0.0, min(retry_after, MAX_RETRY_AFTER))
                        _pd_set_text(f"Rate limited — retrying in {retry_after:.1f}s...")
                        time.sleep(retry_after)
                        continue
                    elif e.code == 401:
                        _pd_close()
                        _err("Authentication Failed",
                             "Invalid Bot Token. Please reconfigure the Discord Bot Scraper.")
                        return
                    elif e.code == 403:
                        _pd_close()
                        _err("Access Denied",
                             "The bot does not have permission to read this channel.\n"
                             "Make sure it has the 'Read Message History' permission.")
                        return
                    elif e.code == 404:
                        _pd_close()
                        _err("Channel Not Found",
                             "Channel ID not found. Please verify the Channel ID is correct.")
                        return
                    else:
                        _pd_close()
                        _err("HTTP Error", f"Discord API returned HTTP {e.code}.")
                        return
                except urllib.error.URLError as e:
                    _pd_close()
                    _err("Network Error",
                         f"Could not reach Discord:\n{str(getattr(e, 'reason', e))}")
                    return

                # An object response usually means an error envelope — bail out cleanly.
                if not isinstance(data, list):
                    break
                if not data:
                    break

                # Walk newest-first within the page, tallying cache matches for early-stop.
                for m in data:
                    if not isinstance(m, dict):
                        continue
                    if not m.get('webhook_id'):
                        continue
                    all_messages.append(m)

                    mid = m.get('id')
                    cached = by_id_view.get(mid) if mid else None
                    if cached is not None and _scrape_record_matches(m, cached):
                        consecutive_matches += 1
                        if consecutive_matches >= EARLY_STOP_THRESHOLD:
                            early_stop = True
                            break
                    else:
                        consecutive_matches = 0

                if early_stop:
                    _pd_set_text(
                        f"Reached cached history ({EARLY_STOP_THRESHOLD} "
                        f"consecutive matches) — stopping."
                    )
                    break

                # Skip entries without an id rather than crashing on KeyError.
                last_id = ''
                for m in reversed(data):
                    if isinstance(m, dict) and m.get('id'):
                        last_id = m['id']
                        break
                if not last_id:
                    break
                before = last_id

                _pd_set_text(f"Fetched {len(all_messages)} webhook messages so far...")

                if len(data) < 100:
                    break

                time.sleep(0.25)

        except Exception as e:
            _pd_close()
            _err("Error", f"An unexpected error occurred:\n{str(e)}")
            return

        if not all_messages:
            _pd_close()
            return

        # Snowflake IDs are chronological. Missing IDs sort to the top instead of crashing.
        all_messages.sort(key=lambda m: str(m.get('id', '')) if isinstance(m, dict) else '')

        new_messages = [
            m for m in all_messages
            if isinstance(m, dict) and m.get('id') and m.get('id') not in existing_ids_set
        ]

        # Collect moderator IDs that appear in any new message's embeds.
        ids_from_new = set()
        for msg in new_messages:
            embeds = msg.get('embeds') or []
            if not isinstance(embeds, list):
                continue
            for emb in embeds:
                if not isinstance(emb, dict):
                    continue
                fields = emb.get('fields') or []
                if not isinstance(fields, list):
                    continue
                for field in fields:
                    if not isinstance(field, dict):
                        continue
                    fname = (field.get('name') or '').strip().lower()
                    if fname in ('moderator', 'referee'):
                        mid = _extract_mention_id(field.get('value'))
                        if mid:
                            ids_from_new.add(mid)

        # Only resolve plausible numeric IDs — avoids spamming /users/Unknown.
        ids_to_resolve = {
            mid for mid in (ids_missing_name | ids_from_new)
            if mid and str(mid).isdigit()
        }

        # Resolve names via the Discord Users API. One call per unique ID per scrape;
        # unresolved IDs stay ID-only and get retried on the next scrape.
        name_by_id = {}
        if ids_to_resolve:
            total = len(ids_to_resolve)
            _pd_set_text(f"Resolving moderator names (0/{total})...")

            def _fetch_user_name(mid_: str):
                u_req = urllib.request.Request(
                    f'https://discord.com/api/v10/users/{mid_}',
                    headers=headers,
                )
                with urllib.request.urlopen(u_req, timeout=10) as u_resp:
                    raw = u_resp.read().decode('utf-8', errors='replace')
                u_data = json.loads(raw)
                if not isinstance(u_data, dict):
                    return ''
                return u_data.get('global_name') or u_data.get('username') or ''

            for i, mid in enumerate(ids_to_resolve, start=1):
                try:
                    name = _fetch_user_name(mid)
                    if name:
                        name_by_id[mid] = name
                except urllib.error.HTTPError as ue:
                    if ue.code == 429:
                        try:
                            err_data = json.loads(ue.read().decode('utf-8', errors='replace'))
                            retry_after = float(err_data.get('retry_after', 1.0))
                        except Exception:
                            retry_after = 1.0
                        retry_after = max(0.0, min(retry_after, MAX_RETRY_AFTER))
                        time.sleep(retry_after)
                        try:
                            name = _fetch_user_name(mid)
                            if name:
                                name_by_id[mid] = name
                        except Exception:
                            pass
                    # 404 / other — silently skip, the next scrape can retry.
                except Exception:
                    pass

                _pd_set_text(f"Resolving moderator names ({i}/{total})...")
                time.sleep(0.1)  # stay below Discord's global rate limit

        legacy_changed = False
        if name_by_id:
            for rec in existing_records:
                if not isinstance(rec, dict):
                    continue  # preserve malformed lines verbatim
                raw_mid = rec.get('ModeratorID', '')
                if not raw_mid or rec.get('ModeratorName', ''):
                    continue
                mid = _extract_mention_id(raw_mid)
                if mid and mid in name_by_id:
                    rec['ModeratorName'] = name_by_id[mid]
                    legacy_changed = True

        if new_messages:
            try:
                with open(DISCORD_LOG_FILE, 'a', encoding='utf-8') as f:
                    for msg in new_messages:
                        f.write(_serialize_discord_message(msg, name_by_id) + '\n')
                _invalidate_log_cache()
            except Exception as e:
                _pd_close()
                _err("Save Error", f"Could not write discordlogshistory:\n{str(e)}")
                return

        # Atomically rewrite the log if legacy records were enriched.
        if legacy_changed:
            _pd_set_text("Updating log file...")
            tmp_path = DISCORD_LOG_FILE + '.tmp'
            try:
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    for rec in existing_records:
                        if isinstance(rec, dict):
                            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
                        else:
                            f.write(rec + '\n')
                    # Re-append the new records so the rewrite stays consistent with the append above.
                    for msg in new_messages:
                        f.write(_serialize_discord_message(msg, name_by_id) + '\n')
                os.replace(tmp_path, DISCORD_LOG_FILE)
                _invalidate_log_cache()
            except Exception as e:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                warn_cb("Log Rewrite Failed",
                        f"Could not rewrite discordlogshistory to enrich "
                        f"legacy moderator names:\n{str(e)}\n\n"
                        f"New records were still appended successfully.")
                # New records were still appended above — let dialogs refresh.
                if new_messages:
                    _emit_sanctions_updated()
                return

        _pd_close()

        # Only notify the UI if the on-disk log actually changed.
        if new_messages or legacy_changed:
            _emit_sanctions_updated()

    def configure_console_key(self):
        """Prompt the user to press their console key and persist its VK code."""
        if self.console_key_dialog is not None and self.console_key_dialog.isVisible():
            self.console_key_dialog.raise_()
            self.console_key_dialog.activateWindow()
            return

        try:
            current_vk = get_persisted_value('console_vk', "")
        except Exception:
            current_vk = ""

        self.console_key_dialog = ConsoleKeyDialog(current_vk=current_vk, parent=self)

        def on_accepted():
            if self.console_key_dialog.captured_vk is not None:
                set_persisted_value('console_vk', str(self.console_key_dialog.captured_vk))
                # Drop the cached value so the next read picks up the new VK.
                from core import inputLib
                inputLib.clearConsoleKeyCache()
                QMessageBox.information(self, "Console Key Saved", f"Console key saved as VK {self.console_key_dialog.captured_vk}.")

        self.console_key_dialog.accepted.connect(on_accepted)
        self.console_key_dialog.finished.connect(lambda: setattr(self, 'console_key_dialog', None))
        self.console_key_dialog.show()
        self.console_key_dialog.raise_()
        self.console_key_dialog.activateWindow()

    def toggle_theme(self):
        """Toggle between dark and light theme."""
        app = QApplication.instance()
        current_is_dark = load_theme_preference()
        new_is_dark = not current_is_dark

        if new_is_dark:
            apply_dark_theme(app)
        else:
            apply_light_theme(app)

        save_theme_preference(new_is_dark)
        self.update_theme_button()

        if hasattr(self, 'update_preset_tooltips'):
            self.update_preset_tooltips()

        if hasattr(self, 'update_admin_preset_tooltips'):
            self.update_admin_preset_tooltips()
        if hasattr(self, 'update_server_preset_tooltips'):
            self.update_server_preset_tooltips()

        # Force a repaint with the new theme applied.
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def update_theme_button(self):
        is_dark = load_theme_preference()
        if is_dark:
            self.theme_button.setText("Light Mode")
        else:
            self.theme_button.setText("Dark Mode")

class FirstToScoreboardWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Match Arbitration (First To)")
        self.resize(1100, 700)
        self.setSizeGripEnabled(True)

        self.game = None
        self.chivalry_connected = False
        self.p1_score = 0
        self.p2_score = 0

        main = QVBoxLayout(self)
        main.setContentsMargins(UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER)
        main.setSpacing(UI_SPACING_SECTION)

        ttl = QLabel("Match Arbitration (First To)")
        ttl.setFont(QFont("Segoe UI", 18, QFont.Bold))
        ttl.setAlignment(Qt.AlignCenter)
        main.addWidget(ttl)

        settings = QGroupBox("Match Settings")
        settings_l = QFormLayout()
        settings_l.setLabelAlignment(Qt.AlignRight)
        settings_l.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        settings_l.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        settings_l.setHorizontalSpacing(UI_SPACING_INNER)
        settings_l.setVerticalSpacing(UI_PAD_TIGHT)

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
        settings.layout().setContentsMargins(UI_PAD_SECTION, UI_PAD_INNER, UI_PAD_SECTION, UI_PAD_INNER)
        main.addWidget(settings)

        broadcast = QGroupBox("Broadcast")
        b_l = QVBoxLayout()
        b_l.setContentsMargins(UI_PAD_SECTION, UI_PAD_INNER, UI_PAD_SECTION, UI_PAD_INNER)
        b_l.setSpacing(UI_PAD_INNER)

        notification_row = QHBoxLayout()

        self.ft_discord_notification = QCheckBox("Broadcast match results to Discord")
        self.ft_discord_notification.setChecked(False)

        tag_row = QHBoxLayout()
        tag_row.setSpacing(UI_PAD_TIGHT)
        tag_row.addWidget(QLabel("Tag prefix (optional):"))
        self.broadcast_tag_input = QLineEdit()
        self.broadcast_tag_input.setPlaceholderText("Tournament")
        tag_row.addWidget(_make_tip_badge("Brackets are added automatically"), 0, Qt.AlignRight)
        tag_row.addWidget(self.broadcast_tag_input, 1)
        b_l.addLayout(tag_row)

        self.announce_start_btn = QPushButton("Announce the start of the match")
        self.announce_start_btn.setMinimumHeight(38)
        self.announce_start_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.announce_start_btn.setStyleSheet(_colored_button_qss(UI_ACCENT))
        self.announce_start_btn.clicked.connect(self.announce_start)
        b_l.addWidget(self.announce_start_btn)

        notification_row.addWidget(self.ft_discord_notification)
        notification_row.setAlignment(Qt.AlignCenter)
        b_l.addLayout(notification_row)

        broadcast.setLayout(b_l)
        main.addWidget(broadcast)

        players_grid = QGridLayout()
        players_grid.setColumnStretch(0, 1)
        players_grid.setColumnStretch(1, 1)
        players_grid.setHorizontalSpacing(UI_SPACING_SECTION)

        def build_player(label_text: str):
            box = QGroupBox(label_text)
            v = QVBoxLayout()
            v.setContentsMargins(UI_PAD_SECTION, UI_PAD_INNER, UI_PAD_SECTION, UI_PAD_INNER)
            v.setSpacing(UI_PAD_INNER)
            name_row = QHBoxLayout()
            name_row.setSpacing(UI_PAD_TIGHT)
            name_row.addWidget(QLabel("Name:"))
            name_edit = QLineEdit()
            name_edit.setPlaceholderText(label_text)
            name_row.addWidget(name_edit, 1)
            v.addLayout(name_row)

            btn_row = QHBoxLayout()
            btn_row.setSpacing(UI_PAD_TIGHT)
            add = QPushButton("Add 1 Point"); add.setMinimumHeight(38)
            add.setStyleSheet(_colored_button_qss(UI_COLOR_UNBAN))
            rem = QPushButton("Remove 1 Point"); rem.setMinimumHeight(38)
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

        self.scoreboard_label = QLabel()
        self.scoreboard_label.setAlignment(Qt.AlignCenter)
        self.scoreboard_label.setFont(QFont("Segoe UI", 64, QFont.DemiBold))
        self.scoreboard_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main.addWidget(self.scoreboard_label, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(UI_SPACING_INNER)
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

        result = f"{self.display_name(self.player1_input.text(), "")} wins {self.p1_score} to {self.p2_score}"  if winner == 1 else f"{self.display_name(self.player2_input.text(), "")} wins {self.p2_score} to {self.p1_score}"
        
        discord_result = ""
        discord_result = result
        discord_result += f" against {self.display_name(self.player2_input.text(), "")}." if winner == 1 else f" against {self.display_name(self.player1_input.text(), "")}."
        result += "."
        
        win_msg = (self.win_msg_input.text() or "").strip()
        self._send_server_message(result)
        if win_msg:
            self._send_server_message(win_msg)

        if self.ft_discord_notification.isChecked():
            wehbooks.MessageForAdmin("N/A", "N/A", discord_result, None, "ft")

        # Lock the +1 buttons until the user resets the score.
        self.add_p1_btn.setEnabled(False)
        self.add_p2_btn.setEnabled(False)

    def reset_score(self):
        self.p1_score = 0
        self.p2_score = 0
        self.add_p1_btn.setEnabled(True)
        self.add_p2_btn.setEnabled(True)
        self.update_scoreboard_label()

    def reset_board(self):
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

class _CenteredComboBox(QComboBox):
    """QComboBox that paints the displayed text centered within the field area.

    The default style paints text left-aligned. The popup list is centered via
    `_CenteredItemDelegate`.
    """

    def paintEvent(self, _event):
        painter = QStylePainter(self)
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        # Draw the frame + arrow without the (left-aligned) label.
        opt.currentText = ""
        painter.drawComplexControl(QStyle.CC_ComboBox, opt)
        field_rect = self.style().subControlRect(
            QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxEditField, self
        )
        painter.drawItemText(
            field_rect, Qt.AlignCenter, self.palette(),
            self.isEnabled(), self.currentText()
        )


class _CenteredItemDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignCenter


class RandomPickDialog(QDialog):
    """Dialog for randomly picking one weapon and one player from cached lists.

    Weapons carry a 1H/2H attribute and per-row exclude flags; players carry per-row
    exclude flags. Global filters can restrict the weapon pool to one-handed or
    two-handed only. The result is announced via ServerSay on demand.
    """

    HAND_OPTIONS = ("2H", "1H")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Random Pick")
        self.resize(820, 620)
        self.setSizeGripEnabled(True)

        self._suspend_persist = True

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER, UI_PAD_OUTER)
        main_layout.setSpacing(UI_SPACING_SECTION)

        title_label = QLabel("Random Pick")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        main_layout.addWidget(title_label)

        tables_row = QHBoxLayout()
        tables_row.setSpacing(UI_SPACING_SECTION)
        tables_row.addWidget(self._build_weapons_group(), 1)
        tables_row.addWidget(self._build_players_group(), 1)
        main_layout.addLayout(tables_row)

        filters_group = QGroupBox("Weapon Filters")
        filters_layout = QHBoxLayout()
        filters_layout.setContentsMargins(UI_PAD_SECTION, UI_PAD_INNER, UI_PAD_SECTION, UI_PAD_INNER)
        filters_layout.setSpacing(UI_SPACING_SECTION)

        self.one_handed_only_cb = QCheckBox("One-handed only")
        self.two_handed_only_cb = QCheckBox("Two-handed only")
        self.one_handed_only_cb.toggled.connect(self._on_one_handed_toggled)
        self.two_handed_only_cb.toggled.connect(self._on_two_handed_toggled)

        filters_layout.addWidget(self.one_handed_only_cb)
        filters_layout.addWidget(self.two_handed_only_cb)
        filters_layout.addStretch(1)
        filters_group.setLayout(filters_layout)
        main_layout.addWidget(filters_group)

        self.result_label = QLabel("No pick yet.")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setWordWrap(True)
        self.result_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.result_label.setMinimumHeight(48)
        main_layout.addWidget(self.result_label)

        action_row = QHBoxLayout()
        action_row.setSpacing(UI_SPACING_INNER)

        self.pick_button = QPushButton("Assign weapon (1 Player)")
        self.pick_button.setMinimumHeight(38)
        self.pick_button.setStyleSheet(_colored_button_qss(UI_ACCENT))
        self.pick_button.clicked.connect(self._do_pick_single)

        self.pick_pair_button = QPushButton("Assign weapons (2 Players)")
        self.pick_pair_button.setMinimumHeight(38)
        self.pick_pair_button.setStyleSheet(_colored_button_qss(UI_COLOR_INFO))
        self.pick_pair_button.clicked.connect(self._do_pick_pair)

        self.close_button = QPushButton("Close")
        self.close_button.setMinimumHeight(38)
        self.close_button.clicked.connect(self.accept)

        for btn in (self.pick_button, self.pick_pair_button, self.close_button):
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        action_row.addWidget(self.pick_button, 1)
        action_row.addWidget(self.pick_pair_button, 1)
        action_row.addWidget(self.close_button, 1)
        main_layout.addLayout(action_row)

        self._load_persisted_state()
        self._suspend_persist = False

        self._apply_table_selection_theme(load_theme_preference())
        _theme_bus.theme_changed.connect(self._apply_table_selection_theme)
        self.finished.connect(self._disconnect_theme_bus)

    def _apply_table_selection_theme(self, is_dark: bool):
        if is_dark:
            sel_bg = "#454545"
            sel_fg = "#ececec"
        else:
            sel_bg = "#e3e8f0"
            sel_fg = "#2c2f33"
        qss = (
            "QTableWidget::item:selected {"
            f" background-color: {sel_bg}; color: {sel_fg};"
            "}"
            "QTableWidget::item:selected:!active {"
            f" background-color: {sel_bg}; color: {sel_fg};"
            "}"
        )
        if hasattr(self, "weapons_table"):
            self.weapons_table.setStyleSheet(qss)
        if hasattr(self, "players_table"):
            self.players_table.setStyleSheet(qss)

    def _disconnect_theme_bus(self):
        try:
            _theme_bus.theme_changed.disconnect(self._apply_table_selection_theme)
        except Exception:
            pass

    # ---- table builders ----

    def _build_weapons_group(self) -> QGroupBox:
        group = QGroupBox("Weapons")
        v = QVBoxLayout()
        v.setContentsMargins(UI_PAD_SECTION, UI_PAD_INNER, UI_PAD_SECTION, UI_PAD_INNER)
        v.setSpacing(UI_PAD_INNER)

        self.weapons_table = QTableWidget(0, 3)
        self.weapons_table.setHorizontalHeaderLabels(["Weapon Name", "Hand", "Exclude"])
        self.weapons_table.verticalHeader().setVisible(False)
        self.weapons_table.verticalHeader().setDefaultSectionSize(44)
        self.weapons_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.weapons_table.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed
        )
        header = self.weapons_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.weapons_table.setColumnWidth(1, 80)
        self.weapons_table.setColumnWidth(2, 70)
        self.weapons_table.itemChanged.connect(self._on_weapon_item_changed)
        v.addWidget(self.weapons_table, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(UI_PAD_TIGHT)
        add_btn = QPushButton("Add Weapon")
        add_btn.clicked.connect(lambda: self._add_weapon_row("", "1H", False, focus=True))
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(lambda: self._remove_selected_rows(self.weapons_table))
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch(1)
        v.addLayout(btn_row)

        group.setLayout(v)
        return group

    def _build_players_group(self) -> QGroupBox:
        group = QGroupBox("Players")
        v = QVBoxLayout()
        v.setContentsMargins(UI_PAD_SECTION, UI_PAD_INNER, UI_PAD_SECTION, UI_PAD_INNER)
        v.setSpacing(UI_PAD_INNER)

        self.players_table = QTableWidget(0, 2)
        self.players_table.setHorizontalHeaderLabels(["Username", "Exclude"])
        self.players_table.verticalHeader().setVisible(False)
        self.players_table.verticalHeader().setDefaultSectionSize(44)
        self.players_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.players_table.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed
        )
        header = self.players_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.players_table.setColumnWidth(1, 70)
        self.players_table.itemChanged.connect(self._on_player_item_changed)
        v.addWidget(self.players_table, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(UI_PAD_TIGHT)
        add_btn = QPushButton("Add Player")
        add_btn.clicked.connect(lambda: self._add_player_row("", False, focus=True))
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(lambda: self._remove_selected_rows(self.players_table))
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch(1)
        v.addLayout(btn_row)

        group.setLayout(v)
        return group

    # ---- row management ----

    def _add_weapon_row(self, name: str, hand: str, exclude: bool, focus: bool = False):
        table = self.weapons_table
        row = table.rowCount()
        table.insertRow(row)

        name_item = QTableWidgetItem(name)
        table.setItem(row, 0, name_item)

        combo = _CenteredComboBox()
        combo.addItems(self.HAND_OPTIONS)
        combo.setCurrentText(hand if hand in self.HAND_OPTIONS else "2H")
        combo.setMinimumWidth(40)
        combo.setItemDelegate(_CenteredItemDelegate(combo))
        combo.view().setTextElideMode(Qt.ElideNone)
        combo.currentTextChanged.connect(lambda _t: self._persist_weapons())

        combo_wrapper = QWidget()
        cw_layout = QHBoxLayout(combo_wrapper)
        cw_layout.setContentsMargins(UI_PAD_TIGHT, 2, UI_PAD_TIGHT, 2)
        cw_layout.addWidget(combo)
        table.setCellWidget(row, 1, combo_wrapper)

        cb_widget, cb = self._make_centered_checkbox(exclude)
        cb.toggled.connect(lambda _v: self._persist_weapons())
        table.setCellWidget(row, 2, cb_widget)

        if focus:
            table.editItem(name_item)

    def _add_player_row(self, name: str, exclude: bool, focus: bool = False):
        table = self.players_table
        row = table.rowCount()
        table.insertRow(row)

        name_item = QTableWidgetItem(name)
        table.setItem(row, 0, name_item)

        cb_widget, cb = self._make_centered_checkbox(exclude)
        cb.toggled.connect(lambda _v: self._persist_players())
        table.setCellWidget(row, 1, cb_widget)

        if focus:
            table.editItem(name_item)

    def _remove_selected_rows(self, table: QTableWidget):
        rows = sorted({idx.row() for idx in table.selectionModel().selectedRows()}, reverse=True)
        if not rows:
            return
        for r in rows:
            table.removeRow(r)
        if table is self.weapons_table:
            self._persist_weapons()
        else:
            self._persist_players()

    @staticmethod
    def _make_centered_checkbox(checked: bool):
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignCenter)
        cb = QCheckBox()
        cb.setChecked(checked)
        cb.setStyleSheet("QCheckBox { spacing: 0px; margin: 0px; padding: 2px; } QCheckBox::indicator { width: 16px; height: 16px; }")
        cb.setFixedSize(20, 20)
        layout.addWidget(cb)
        return wrapper, cb

    def _checkbox_at(self, table: QTableWidget, row: int, col: int) -> QCheckBox:
        wrapper = table.cellWidget(row, col)
        if wrapper is None:
            return None
        return wrapper.findChild(QCheckBox)

    # ---- filter handling ----

    def _on_one_handed_toggled(self, checked: bool):
        if checked and self.two_handed_only_cb.isChecked():
            self.two_handed_only_cb.blockSignals(True)
            self.two_handed_only_cb.setChecked(False)
            self.two_handed_only_cb.blockSignals(False)
        self._persist_filters()

    def _on_two_handed_toggled(self, checked: bool):
        if checked and self.one_handed_only_cb.isChecked():
            self.one_handed_only_cb.blockSignals(True)
            self.one_handed_only_cb.setChecked(False)
            self.one_handed_only_cb.blockSignals(False)
        self._persist_filters()

    # ---- change handlers ----

    def _on_weapon_item_changed(self, _item):
        if self._suspend_persist:
            return
        self._persist_weapons()

    def _on_player_item_changed(self, _item):
        if self._suspend_persist:
            return
        self._persist_players()

    # ---- pick logic ----

    def _collect_weapons(self) -> list:
        out = []
        for row in range(self.weapons_table.rowCount()):
            name_item = self.weapons_table.item(row, 0)
            name = name_item.text().strip() if name_item else ""
            wrapper = self.weapons_table.cellWidget(row, 1)
            combo = wrapper.findChild(QComboBox) if wrapper is not None else None
            hand = combo.currentText() if combo is not None else "1H"
            cb = self._checkbox_at(self.weapons_table, row, 2)
            exclude = cb.isChecked() if cb is not None else False
            out.append({"name": name, "hand": hand, "exclude": exclude})
        return out

    def _collect_players(self) -> list:
        out = []
        for row in range(self.players_table.rowCount()):
            name_item = self.players_table.item(row, 0)
            name = name_item.text().strip() if name_item else ""
            cb = self._checkbox_at(self.players_table, row, 1)
            exclude = cb.isChecked() if cb is not None else False
            out.append({"name": name, "exclude": exclude})
        return out

    def _selected_player(self) -> dict:
        selected_rows = self.players_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        name_item = self.players_table.item(row, 0)
        name = name_item.text().strip() if name_item else ""
        if not name:
            return None
        return {"name": name, "exclude": False}

    def _eligible_weapons(self) -> list:
        one_only = self.one_handed_only_cb.isChecked()
        two_only = self.two_handed_only_cb.isChecked()
        out = []
        for w in self._collect_weapons():
            if not w["name"] or w["exclude"]:
                continue
            if one_only and w["hand"] != "1H":
                continue
            if two_only and w["hand"] != "2H":
                continue
            out.append(w)
        return out

    def _eligible_players(self) -> list:
        return [p for p in self._collect_players() if p["name"] and not p["exclude"]]

    def _do_pick_single(self):
        weapons = self._eligible_weapons()
        if not weapons:
            QMessageBox.warning(self, "No Weapons", "No eligible weapons available with current filters/exclusions.")
            return

        player = self._selected_player()
        if player is None:
            players = self._eligible_players()
            if not players:
                QMessageBox.warning(self, "No Players", "No eligible players available with current exclusions.")
                return
            player = random.choice(players)

        weapon = random.choice(weapons)
        message = f"{player['name']} got assigned to {weapon['name']} !"

        self.result_label.setText(message)
        self._send_serversay([message])

    def _do_pick_pair(self):
        weapons = self._eligible_weapons()
        players = self._eligible_players()

        if len(players) < 2:
            QMessageBox.warning(
                self, "Not Enough Players",
                "Need at least 2 eligible players to pick a pair."
            )
            return
        if len(weapons) < 2:
            QMessageBox.warning(
                self, "Not Enough Weapons",
                "Need at least 2 eligible weapons (with current filters/exclusions) to pick a pair."
            )
            return

        chosen_players = random.sample(players, 2)
        chosen_weapons = random.sample(weapons, 2)

        messages = [
            f"{chosen_players[i]['name']} got assigned to {chosen_weapons[i]['name']} !"
            for i in range(2)
        ]

        self.result_label.setText(" | ".join(messages))
        self._send_serversay(messages)

    def _send_serversay(self, messages: list):
        parent = self.parent()
        game = getattr(parent, 'game', None)
        connected = bool(getattr(parent, 'chivalry_connected', False))

        if not connected or game is None or not hasattr(game, 'ServerSay'):
            QMessageBox.warning(
                self,
                "Not Connected",
                "Result picked, but cannot announce - Chivalry 2 is not connected.\n\nPlease ensure Chivalry 2 is running."
            )
            return

        for msg in messages:
            try:
                game.ServerSay(msg)
            except Exception as e:
                QMessageBox.warning(self, "Game Error", f"Failed to send message to game:\n{str(e)}")
                return

    # ---- persistence ----

    def _persist_weapons(self):
        if self._suspend_persist:
            return
        try:
            set_persisted_value('random_pick_weapons', json.dumps(self._collect_weapons(), ensure_ascii=False))
        except Exception:
            pass

    def _persist_players(self):
        if self._suspend_persist:
            return
        try:
            set_persisted_value('random_pick_players', json.dumps(self._collect_players(), ensure_ascii=False))
        except Exception:
            pass

    def _persist_filters(self):
        if self._suspend_persist:
            return
        payload = {
            "one_handed_only": self.one_handed_only_cb.isChecked(),
            "two_handed_only": self.two_handed_only_cb.isChecked(),
        }
        try:
            set_persisted_value('random_pick_filters', json.dumps(payload))
        except Exception:
            pass

    def _load_persisted_state(self):
        try:
            weapons_raw = get_persisted_value('random_pick_weapons', '')
            weapons = json.loads(weapons_raw) if weapons_raw else []
        except Exception:
            weapons = []
        for w in weapons:
            if isinstance(w, dict):
                self._add_weapon_row(
                    str(w.get("name", "")),
                    str(w.get("hand", "1H")),
                    bool(w.get("exclude", False)),
                )

        try:
            players_raw = get_persisted_value('random_pick_players', '')
            players = json.loads(players_raw) if players_raw else []
        except Exception:
            players = []
        for p in players:
            if isinstance(p, dict):
                self._add_player_row(
                    str(p.get("name", "")),
                    bool(p.get("exclude", False)),
                )

        try:
            filters_raw = get_persisted_value('random_pick_filters', '')
            filters = json.loads(filters_raw) if filters_raw else {}
        except Exception:
            filters = {}
        if isinstance(filters, dict):
            self.one_handed_only_cb.blockSignals(True)
            self.two_handed_only_cb.blockSignals(True)
            self.one_handed_only_cb.setChecked(bool(filters.get("one_handed_only", False)))
            self.two_handed_only_cb.setChecked(bool(filters.get("two_handed_only", False)))
            self.one_handed_only_cb.blockSignals(False)
            self.two_handed_only_cb.blockSignals(False)


# ---- Discord log history (JSON Lines database) ----

DISCORD_LOG_FILE = "discordlogshistory"

# Module-level cache of the parsed log. Invalidated by (mtime, size). Every sanction reader
# goes through `_read_log_cached()` so the file is parsed at most once per external mutation.
# Index views (`by_id`, `by_pid`) share dict references with `dicts` — they are not copies.
# Parsing is serialized by `_log_cache_lock`; the cache-hit fast path is lock-free.
_log_cache_lock     = threading.Lock()
# Held by an in-flight silent scrape so repeat triggers coalesce into one run.
_silent_scrape_lock = threading.Lock()


class _SanctionsBus(QObject):
    """Signal hub for log-changed notifications so dialogs can re-pull and rebuild."""
    sanctionsUpdated = pyqtSignal()


_sanctions_bus = None


def _get_sanctions_bus() -> _SanctionsBus:
    """Return the global sanctions bus, creating it on first use.

    Must be called from the UI thread the first time so the QObject is affined there;
    cross-thread emits from worker threads then queue back to the UI thread automatically.
    """
    global _sanctions_bus
    if _sanctions_bus is None:
        _sanctions_bus = _SanctionsBus()
    return _sanctions_bus


def _emit_sanctions_updated() -> None:
    """Notify subscribers that the sanctions log changed. Thread-safe; no-op if no bus exists yet."""
    bus = _sanctions_bus
    if bus is not None:
        bus.sanctionsUpdated.emit()
_log_cache_key      = None   # (mtime, size) tuple, or None when unloaded
_log_cache_records  = []     # list[dict | str]  — str preserves malformed lines verbatim
_log_cache_dicts    = []     # list[dict]        — subset of _records (no malformed lines)
_log_cache_by_id    = {}     # dict[id] -> record
_log_cache_by_pid   = {}     # dict[playfab_upper] -> list[record]
_log_warm_thread    = None   # daemon Thread currently warming the cache, or None


def _read_log_cached():
    """Return (records, dicts, by_id, by_pid) for discordlogshistory.

    Re-parses from disk only when (mtime, size) changes. Returned containers are the
    cache itself — treat them as read-only. Thread-safe.
    """
    global _log_cache_key, _log_cache_records, _log_cache_dicts
    global _log_cache_by_id, _log_cache_by_pid

    with _log_cache_lock:
        if not os.path.exists(DISCORD_LOG_FILE):
            if _log_cache_key is not None:
                _log_cache_key     = None
                _log_cache_records = []
                _log_cache_dicts   = []
                _log_cache_by_id   = {}
                _log_cache_by_pid  = {}
            return _log_cache_records, _log_cache_dicts, _log_cache_by_id, _log_cache_by_pid

        try:
            st = os.stat(DISCORD_LOG_FILE)
        except OSError:
            return _log_cache_records, _log_cache_dicts, _log_cache_by_id, _log_cache_by_pid

        key = (st.st_mtime, st.st_size)
        if key == _log_cache_key:
            return _log_cache_records, _log_cache_dicts, _log_cache_by_id, _log_cache_by_pid

        records = []
        dicts   = []
        by_id   = {}
        by_pid  = {}
        try:
            with open(DISCORD_LOG_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        records.append(line)
                        continue
                    if not isinstance(rec, dict):
                        records.append(line)
                        continue
                    # Intern keys so all records share one copy of each key string.
                    rec = {sys.intern(k) if isinstance(k, str) else k: v for k, v in rec.items()}
                    records.append(rec)
                    dicts.append(rec)
                    rid = rec.get('id')
                    if rid:
                        by_id[rid] = rec
                    pid = rec.get('PlayFabID', '')
                    if pid:
                        by_pid.setdefault(pid.upper(), []).append(rec)
        except Exception:
            # Keep the previous cache on transient read failure.
            return _log_cache_records, _log_cache_dicts, _log_cache_by_id, _log_cache_by_pid

        _log_cache_key     = key
        _log_cache_records = records
        _log_cache_dicts   = dicts
        _log_cache_by_id   = by_id
        _log_cache_by_pid  = by_pid
        return records, dicts, by_id, by_pid


def _invalidate_log_cache() -> None:
    """Force the next _read_log_cached() call to re-parse from disk.

    Called after we mutate the log ourselves so we don't depend on filesystem timestamp resolution.
    """
    global _log_cache_key
    with _log_cache_lock:
        _log_cache_key = None


def _warm_log_cache_async() -> None:
    """Warm the discord log cache on a daemon thread. Idempotent — re-entry while in flight is a no-op."""
    global _log_warm_thread
    t = _log_warm_thread
    if t is not None and t.is_alive():
        return

    def _run():
        try:
            _read_log_cached()
        except Exception as e:
            # Don't let a warmup crash propagate — the synchronous fallback on first access still works.
            print(f"[CACHE] Warmup failed: {e}")

    t = threading.Thread(target=_run, name="discord-log-cache-warmup", daemon=True)
    _log_warm_thread = t
    t.start()


def _schedule_silent_discord_scrape(origin_widget, delay_ms: int = 2000) -> None:
    """Fire a silent log scrape after a webhook-triggered action.

    Delayed so the webhook has time to actually land in Discord before we scrape. No-op if no
    AdminDashboard is reachable — the manual "Fetch Discord Channel Messages" button is the fallback.
    """
    dashboard = None
    w = origin_widget
    while w is not None:
        if isinstance(w, AdminDashboard):
            dashboard = w
            break
        w = w.parent() if hasattr(w, 'parent') and callable(w.parent) else None

    if dashboard is None:
        for tlw in QApplication.topLevelWidgets():
            if isinstance(tlw, AdminDashboard):
                dashboard = tlw
                break

    if dashboard is None:
        return

    QTimer.singleShot(
        max(0, int(delay_ms)),
        lambda d=dashboard: d.fetch_discord_channel_messages(silent=True),
    )


_MENTION_ID_RE = re.compile(r'<@[!&]?(\d+)>')
_DIGITS_RE = re.compile(r'\d+')
_BOLD_RE = re.compile(r'(?:\*\*|__)([^*_]+?)(?:\*\*|__)')
# Strips surrounding markdown (**, __, *, _) from a "Key" token.
_MD_STRIP_RE = re.compile(r'^[\*_]+|[\*_]+$')


def _extract_mention_id(raw) -> str:
    """Return the numeric user id from a Discord mention, or '' if none found.

    Accepts <@id>, <@!id>, <@&id>, or a bare numeric id. Anything else (including 'Unknown', empty, None) yields ''.
    """
    if not raw:
        return ''
    s = str(raw).strip()
    m = _MENTION_ID_RE.search(s)
    if m:
        return m.group(1)
    if s.isdigit():
        return s
    m = _DIGITS_RE.search(s)
    return m.group(0) if m else ''


# Fields used to decide whether a fresh Discord message matches a cached record.
# `ModeratorName` is excluded because it's filled in by a separate /users/{id} call,
# so a cached record may have it while a fresh one (without `name_by_id`) won't.
_SCRAPE_DUP_FIELDS = (
    'id', 'timestamp', 'action', 'PlayFabID', 'Username',
    'Reason', 'Duration', 'ModeratorID',
)


def _scrape_record_matches(msg: dict, cached: dict) -> bool:
    """Whether a fresh Discord message would yield the same record as one already cached.

    Used by the scrape's early-stop check to find the boundary between new and stored history
    without going through JSON.
    """
    if not isinstance(cached, dict):
        return False
    fresh = _discord_message_to_record(msg)
    for k in _SCRAPE_DUP_FIELDS:
        if fresh.get(k, '') != cached.get(k, ''):
            return False
    return True


def _discord_message_to_record(msg: dict, name_by_id: dict = None) -> dict:
    """Extract the flat sanction record from a Discord webhook message.

    See `_serialize_discord_message` for the field reference. Split out so the scrape's
    early-stop check can compare messages without a JSON round-trip.
    """
    _ACTION_MAP = [
        ('unban',    'unban'),     # must come before 'ban' so it doesn't match the substring
        ('ban',      'ban'),
        ('kick',     'kick'),
        ('note',     'note'),
        ('warning',  'note'),      # legacy embeds said "warning"
        ('warn',     'note'),      # legacy embeds said "warn"
        ('first to', 'ft'),
    ]

    record = {
        'id':            '',
        'timestamp':     '',
        'action':        '',
        'PlayFabID':     '',
        'Username':      '',
        'Reason':        '',
        'Duration':      '',
        'ModeratorID':   '',
        'ModeratorName': '',
    }

    try:
        if not isinstance(msg, dict):
            return record

        record['id']        = str(msg.get('id', '') or '')
        record['timestamp'] = str(msg.get('timestamp', '') or '')

        embeds = msg.get('embeds') or []
        if not isinstance(embeds, list):
            embeds = []

        def _parse_info_value(fvalue: str):
            """Parse newline-delimited 'Key: Value' pairs into record fields."""
            if not fvalue:
                return
            for line in str(fvalue).split('\n'):
                line = line.strip()
                if ':' not in line:
                    continue
                key, _, val = line.partition(':')
                key = _MD_STRIP_RE.sub('', key.strip()).strip().lower()
                val = val.strip().strip('`').strip()
                # Strip surrounding markdown like "** ABC **".
                val = _MD_STRIP_RE.sub('', val).strip()
                if not key:
                    continue
                if key == 'playfabid' and not record['PlayFabID']:
                    record['PlayFabID'] = val
                elif key == 'username' and not record['Username']:
                    record['Username'] = val
                elif key == 'reason' and not record['Reason']:
                    record['Reason'] = val
                elif key == 'duration' and not record['Duration']:
                    record['Duration'] = val

        for emb in embeds:
            if not isinstance(emb, dict):
                continue

            # Derive action from the embed description, falling back to the title.
            desc = (emb.get('description') or '') + ' ' + (emb.get('title') or '')
            if desc.strip() and not record['action']:
                # Prefer bold-delimited tokens; fall back to scanning the raw text.
                bold_tokens = [m.group(1).lower() for m in _BOLD_RE.finditer(desc)]
                scan_sources = bold_tokens + [desc.lower()]
                for source in scan_sources:
                    matched = False
                    for key, val in _ACTION_MAP:
                        if key in source:
                            record['action'] = val
                            matched = True
                            break
                    if matched:
                        break

            fields = emb.get('fields') or []
            if not isinstance(fields, list):
                continue

            for field in fields:
                if not isinstance(field, dict):
                    continue
                fname = (field.get('name') or '').strip().lower()
                fvalue = field.get('value')
                if fvalue is None:
                    fvalue = ''

                if fname in ('information', 'results'):
                    _parse_info_value(fvalue)
                elif fname in ('moderator', 'referee'):
                    mid = _extract_mention_id(fvalue)
                    if mid:
                        record['ModeratorID'] = mid
                        if name_by_id and mid in name_by_id:
                            record['ModeratorName'] = name_by_id[mid]
                else:
                    # Field name was unexpected but the value still looks like key/value pairs.
                    if ':' in str(fvalue) and any(
                        k in str(fvalue).lower()
                        for k in ('playfabid', 'username', 'reason', 'duration')
                    ):
                        _parse_info_value(fvalue)
    except Exception:
        # One malformed message shouldn't break the whole scrape.
        pass

    return record


def _serialize_discord_message(msg: dict, name_by_id: dict = None) -> str:
    """Serialize a Discord webhook message into one flat JSON line.

    Stored fields: id, timestamp, action, PlayFabID, Username, Reason, Duration, ModeratorID, ModeratorName.

    Action is parsed from the bold token in the embed description ("**ban**", "**unban**", ...).
    If `name_by_id` contains the extracted moderator id, `ModeratorName` is baked in so the read path
    never needs a separate cache.

    Tolerant of minor format drift: case-insensitive field names, ** or __ bold markers, surrounding
    markdown on key/value lines. Unexpected structure yields empty fields rather than raising.
    """
    return json.dumps(_discord_message_to_record(msg, name_by_id), ensure_ascii=False)


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
# 29: random pick weapons (JSON)
# 30: random pick players (JSON)
# 31: random pick filters (JSON)
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
    'random_pick_weapons': 29,
    'random_pick_players': 30,
    'random_pick_filters': 31,
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
    max_idx = max(PERSIST_INDEX.values())
    if len(lines) <= max_idx:
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
    """Return True for dark, False for light. Defaults to dark. Cached; save_theme_preference() invalidates."""
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


def _build_stylesheet(palette: dict) -> str:
    """Build the app-wide QSS from a palette. Both themes share the same structure — only colours differ."""
    p = palette
    return f"""
    /* Base */
    QWidget {{
        background-color: {p['bg']};
        color: {p['fg']};
        selection-background-color: {p['accent']};
        selection-color: #ffffff;
    }}
    QDialog, QMessageBox, QInputDialog {{
        background-color: {p['bg']};
        color: {p['fg']};
    }}

    /* Group boxes */
    QGroupBox {{
        background-color: {p['surface']};
        border: 1px solid {p['border']};
        border-radius: {UI_RADIUS}px;
        margin-top: 14px;
        padding: 14px 10px 10px 10px;
        font-weight: 600;
        color: {p['fg']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 6px;
        color: {p['fg_muted']};
        background-color: {p['surface']};
    }}

    /* Buttons */
    QPushButton {{
        background-color: {p['btn_bg']};
        border: 1px solid {p['btn_border']};
        border-radius: {UI_RADIUS_SMALL}px;
        padding: 7px 14px;
        color: {p['fg']};
        font-weight: 600;
        min-height: 20px;
    }}
    QPushButton:hover {{
        background-color: {p['btn_bg_hover']};
        border: 1px solid {p['btn_border_hover']};
    }}
    QPushButton:pressed {{
        background-color: {p['btn_bg_pressed']};
    }}
    QPushButton:focus {{
        outline: none;
        border: 1px solid {p['accent']};
    }}
    QPushButton:disabled {{
        background-color: {p['btn_bg_disabled']};
        color: {p['fg_disabled']};
        border: 1px solid {p['border']};
    }}

    /* Inputs */
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {p['input_bg']};
        border: 1px solid {p['border']};
        border-radius: {UI_RADIUS_SMALL}px;
        padding: 6px 8px;
        color: {p['fg']};
        selection-background-color: {p['accent']};
        selection-color: #ffffff;
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border: 1px solid {p['accent']};
    }}
    QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
        background-color: {p['input_bg_disabled']};
        color: {p['fg_disabled']};
    }}
    QLineEdit[readOnly="true"] {{
        background-color: {p['input_bg_readonly']};
        color: {p['fg_muted']};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {p['surface']};
        border: 1px solid {p['border']};
        selection-background-color: {p['accent']};
        selection-color: #ffffff;
    }}

    /* Check boxes */
    QCheckBox {{
        spacing: 8px;
        color: {p['fg']};
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {p['border']};
        border-radius: 3px;
        background-color: {p['input_bg']};
    }}
    QCheckBox::indicator:hover {{
        border: 1px solid {p['accent']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {p['accent']};
        border: 1px solid {p['accent']};
        image: none;
    }}
    QCheckBox::indicator:disabled {{
        background-color: {p['input_bg_disabled']};
        border: 1px solid {p['border']};
    }}

    /* Labels */
    QLabel {{
        color: {p['fg']};
        background-color: transparent;
    }}

    /* List widgets */
    QListWidget {{
        background-color: {p['surface']};
        border: 1px solid {p['border']};
        border-radius: {UI_RADIUS_SMALL}px;
        color: {p['fg']};
        selection-background-color: {p['accent']};
        selection-color: #ffffff;
        alternate-background-color: {p['surface_alt']};
        outline: 0;
    }}
    QListWidget::item {{
        padding: 7px 8px;
        border-bottom: 1px solid {p['row_sep']};
    }}
    QListWidget::item:selected {{
        background-color: {p['accent']};
        color: #ffffff;
    }}
    QListWidget::item:hover {{
        background-color: {p['row_hover']};
    }}

    /* Table widgets */
    QTableView, QTableWidget {{
        background-color: {p['surface']};
        alternate-background-color: {p['surface_alt']};
        border: 1px solid {p['border']};
        border-radius: {UI_RADIUS_SMALL}px;
        color: {p['fg']};
        gridline-color: {p['row_sep']};
        selection-background-color: {p['accent']};
        selection-color: #ffffff;
        outline: 0;
    }}
    QTableView::item, QTableWidget::item {{
        padding: 4px 6px;
        border: none;
    }}
    QTableView::item:selected, QTableWidget::item:selected {{
        background-color: {p['accent']};
        color: #ffffff;
    }}
    QTableView::item:hover, QTableWidget::item:hover {{
        background-color: {p['row_hover']};
    }}
    QHeaderView {{
        background-color: {p['surface_alt']};
        border: none;
    }}
    QHeaderView::section {{
        background-color: {p['surface_alt']};
        color: {p['fg_muted']};
        padding: 6px 8px;
        border: none;
        border-right: 1px solid {p['row_sep']};
        border-bottom: 1px solid {p['border']};
        font-weight: 600;
    }}
    QHeaderView::section:last {{
        border-right: none;
    }}
    QHeaderView::section:hover {{
        background-color: {p['row_hover']};
        color: {p['fg']};
    }}
    QTableCornerButton::section {{
        background-color: {p['surface_alt']};
        border: none;
        border-right: 1px solid {p['row_sep']};
        border-bottom: 1px solid {p['border']};
    }}

    /* Progress bars */
    QProgressBar {{
        background-color: {p['surface']};
        border: 1px solid {p['border']};
        border-radius: {UI_RADIUS_SMALL}px;
        text-align: center;
        color: {p['fg']};
        min-height: 18px;
    }}
    QProgressBar::chunk {{
        background-color: {p['accent']};
        border-radius: 3px;
    }}

    /* Dialog button box */
    QDialogButtonBox {{
        button-layout: 2;
    }}
    QDialogButtonBox QPushButton {{
        min-width: 96px;
    }}
    QMessageBox QPushButton {{
        min-width: 80px;
        min-height: 26px;
    }}

    /* Tool tips */
    QToolTip {{
        background-color: {p['tooltip_bg']};
        color: {p['tooltip_fg']};
        border: 1px solid {p['border']};
        border-radius: {UI_RADIUS_SMALL}px;
        padding: 5px 8px;
    }}

    /* Scroll bars */
    QScrollBar:vertical {{
        background-color: {p['scroll_track']};
        width: 11px;
        border-radius: 5px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background-color: {p['scroll_handle']};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {p['scroll_handle_hover']};
    }}
    QScrollBar:horizontal {{
        background-color: {p['scroll_track']};
        height: 11px;
        border-radius: 5px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {p['scroll_handle']};
        border-radius: 5px;
        min-width: 24px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {p['scroll_handle_hover']};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        border: none;
        background: none;
        width: 0;
        height: 0;
    }}
    QScrollBar::add-page, QScrollBar::sub-page {{
        background: none;
    }}

    /* Scroll area */
    QScrollArea {{
        background-color: transparent;
        border: none;
    }}
    """


def apply_dark_theme(app):
    """Apply the dark theme to the whole app."""
    palette = {
        'bg':                   '#262626',
        'surface':              '#2f2f2f',
        'surface_alt':          '#383838',
        'border':               '#4a4a4a',
        'row_sep':              '#3d3d3d',
        'row_hover':            '#3a3a3a',
        'fg':                   '#ececec',
        'fg_muted':             '#b8b8b8',
        'fg_disabled':          '#6a6a6a',
        'accent':               UI_ACCENT,
        'btn_bg':               '#3a3a3a',
        'btn_bg_hover':         '#464646',
        'btn_bg_pressed':       '#2e2e2e',
        'btn_bg_disabled':      '#2a2a2a',
        'btn_border':           '#555555',
        'btn_border_hover':     '#6a6a6a',
        'input_bg':             '#383838',
        'input_bg_disabled':    '#2e2e2e',
        'input_bg_readonly':    '#333333',
        'tooltip_bg':           '#1f1f1f',
        'tooltip_fg':           '#ececec',
        'scroll_track':         '#2f2f2f',
        'scroll_handle':        '#5a5a5a',
        'scroll_handle_hover':  '#707070',
    }
    app.setStyleSheet(_build_stylesheet(palette))

def apply_light_theme(app):
    """Apply the light theme to the whole app."""
    palette = {
        'bg':                   '#f4f5f7',
        'surface':              '#ffffff',
        'surface_alt':          '#f7f8fa',
        'border':               '#d0d4d9',
        'row_sep':              '#ececec',
        'row_hover':            '#eff2f6',
        'fg':                   '#2c2f33',
        'fg_muted':             '#6a6f75',
        'fg_disabled':          '#a8acb0',
        'accent':               UI_ACCENT,
        'btn_bg':               '#ffffff',
        'btn_bg_hover':         '#f1f3f6',
        'btn_bg_pressed':       '#e6e9ed',
        'btn_bg_disabled':      '#f6f7f8',
        'btn_border':           '#c5cad0',
        'btn_border_hover':     '#a8aeb5',
        'input_bg':             '#ffffff',
        'input_bg_disabled':    '#f1f2f4',
        'input_bg_readonly':    '#f7f8fa',
        'tooltip_bg':           '#2c2f33',
        'tooltip_fg':           '#ffffff',
        'scroll_track':         '#ececec',
        'scroll_handle':        '#c2c7cc',
        'scroll_handle_hover':  '#9ea4ab',
    }
    app.setStyleSheet(_build_stylesheet(palette))

class _ReleaseNotesFetchBridge(QObject):
    # `object` lets the second arg carry either str or None across threads.
    fetched = pyqtSignal(str, object)


def _should_show_post_update_notes() -> bool:
    """True if the autoupdater installed this exe and we haven't shown its release notes yet.

    Detection uses two markers in the autoupdater state file: `installed_local_file_version`
    (written by every updater back to v4.5.4) and `notes_shown_for_local_version` (we write
    this when the dialog is dismissed). We can't use the old `--post-update=` argv flag
    because older updaters don't set it.
    """
    if not getattr(sys, "frozen", False):
        return False
    try:
        from core.autoupdater import _load_state
        st = _load_state()
        installed_v = st.get("installed_local_file_version")
        if not installed_v:
            return False
        return st.get("notes_shown_for_local_version") != installed_v
    except Exception as e:
        print(f"[POST-UPDATE] State check failed: {e}")
        return False


def _mark_post_update_notes_shown() -> None:
    """Persist `notes_shown_for_local_version` so the dialog doesn't appear again for this version."""
    try:
        from core.autoupdater import _load_state, _save_state
        st = _load_state()
        installed_v = st.get("installed_local_file_version")
        if installed_v:
            st["notes_shown_for_local_version"] = installed_v
            _save_state(st)
    except Exception as e:
        print(f"[POST-UPDATE] Failed to persist notes-shown marker: {e}")


def _show_release_notes_dialog(parent):
    """Fetch and show the latest GitHub release notes in a modal dialog.

    Fetch runs on a daemon thread; the dialog is built on the main thread when the bridge
    emits `fetched`. Targets `/releases/latest` since the user was just autoupdated to it.
    On fetch failure, falls back to a minimal dialog with a clickable releases-page link.
    """
    import urllib.request
    from PyQt5.QtWidgets import QTextBrowser

    try:
        from core.autoupdater import GITHUB_REPO
    except Exception:
        GITHUB_REPO = "Lionkjgame1219/Chiv2AdminDashboard"

    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    web_url = f"https://github.com/{GITHUB_REPO}/releases/latest"

    # Parent it to `parent` so the bridge dies with the dashboard.
    bridge = _ReleaseNotesFetchBridge(parent)

    def _build_and_show(title, body):
        dlg = QDialog(parent)
        dlg.setWindowTitle(f"What's new — {title}")
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.setContentsMargins(15, 15, 15, 15)
        dlg_layout.setSpacing(10)

        header = QLabel(f"<h2 style='margin:0'>{title}</h2>")
        dlg_layout.addWidget(header)

        if body is None:
            msg = QLabel(
                "A new version has been installed.<br><br>"
                "Release notes couldn't be fetched right now (you may be offline "
                "or GitHub is unreachable).<br><br>"
                f"You can view them here once you're back online:<br>"
                f'<a href="{web_url}">{web_url}</a>'
            )
            msg.setWordWrap(True)
            msg.setOpenExternalLinks(True)
            msg.setTextInteractionFlags(Qt.TextBrowserInteraction)
            msg.setMinimumWidth(460)
            dlg_layout.addWidget(msg)
        else:
            browser = QTextBrowser()
            browser.setOpenExternalLinks(True)
            text = body if body else "_No release notes provided for this release._"
            # setMarkdown requires Qt >= 5.14; fall back to plain text otherwise.
            try:
                browser.setMarkdown(text)
            except (AttributeError, TypeError):
                browser.setPlainText(text)

            # Set the document's text width before measuring so .size() reflects the
            # wrapped layout at the width we'll actually display. Cap by screen height.
            content_width = 640
            doc = browser.document()
            doc.setDocumentMargin(8)
            doc.setTextWidth(content_width)
            doc_height = int(doc.size().height())

            screen = QApplication.primaryScreen()
            max_h = (screen.availableGeometry().height() - 240) if screen else 700
            height = max(160, min(doc_height + 24, max_h))

            browser.setMinimumWidth(content_width + 24)
            browser.setMinimumHeight(height)
            dlg_layout.addWidget(browser)

        btns = QDialogButtonBox(QDialogButtonBox.Ok)
        btns.accepted.connect(dlg.accept)
        dlg_layout.addWidget(btns)

        dlg.adjustSize()
        dlg.exec_()
        # Persist only after the user actually saw the dialog — a crash before this
        # leaves the marker unwritten so we'll show it again next launch.
        _mark_post_update_notes_shown()
        bridge.deleteLater()

    # Force QueuedConnection so the dialog is always built on the GUI thread,
    # not on the fetch worker.
    bridge.fetched.connect(_build_and_show, Qt.QueuedConnection)

    def _fetch():
        body = None
        title = "Latest release"
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
            title = data.get("name") or data.get("tag_name") or title
            body = (data.get("body") or "").strip()
        except Exception as e:
            print(f"[POST-UPDATE] Failed to fetch release notes: {e}")
        bridge.fetched.emit(str(title), body)

    threading.Thread(target=_fetch, name="release-notes-fetch", daemon=True).start()


def main():
    # Auto-update for the packaged Windows .exe. If an update is available a temporary updater
    # copy of this exe spawns, this process exits, and the updater replaces the original and
    # relaunches. The updater process runs this same entrypoint with '--apply-update' — in that
    # mode we never start the full UI.
    try:
        from core import autoupdater
        if "--apply-update" in sys.argv:
            if autoupdater.handle_update_flow():
                sys.exit(0)
    except Exception:
        # Bail in updater mode rather than launching the UI while files may be changing.
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

    is_dark_theme = load_theme_preference()
    if is_dark_theme:
        apply_dark_theme(app)
    else:
        apply_light_theme(app)

    # Warm the discord log cache early so it overlaps with theme setup, the waiting dialog,
    # webhook init, and dashboard construction.
    _warm_log_cache_async()

    if "--no-wait" not in sys.argv and not check_chivalry_window():
        waiting_dialog = ChivalryWaitingDialog()
        result = waiting_dialog.exec_()
        if result == QDialog.Rejected:
            sys.exit(0)

    import core.wehbooks as wehbooks
    webhook_initialized = wehbooks.initialize_webhook()
    if webhook_initialized:
        print("[STARTUP] Discord webhook(s) initialized successfully")
    else:
        print("[STARTUP] Discord webhooks not configured or failed to initialize")

    # Only check that the log file exists — the entry count comes from the cache once warmup completes.
    if os.path.exists(DISCORD_LOG_FILE):
        print("[STARTUP] Discord logs history file found — parsing in background")
    else:
        print("[STARTUP] Discord logs history file not found — will be created on first scrape")

    window = AdminDashboard()
    window.show()

    # Refresh the local sanction history once the dashboard is up.
    _schedule_silent_discord_scrape(window)

    # Show "What's new?" on the first launch after an autoupdate. The fetch runs in the
    # background and the dialog opens when it finishes.
    if _should_show_post_update_notes():
        try:
            _show_release_notes_dialog(window)
        except Exception as e:
            print(f"[POST-UPDATE] Release notes dialog failed: {e}")

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
