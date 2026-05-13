"""Input system for Chivalry 2 console operations."""

from time import sleep
import ctypes
from ctypes import wintypes
import win32api, win32con
import pyperclip

KEY_PRESS_DURATION = 0.002
KEY_SEQUENCE_DELAY = 0.002
COMMAND_COMPLETION_DELAY = 0.0
CLIPBOARD_SETTLE_DELAY = 0.002
POST_PASTE_DELAY = 0.016

_console_key_cache = None

# SendInput delivers batches atomically; keybd_event can interleave with other injected input.

_INPUT_KEYBOARD = 1
_KEYEVENTF_KEYUP = 0x0002

ULONG_PTR = ctypes.c_size_t

class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", _KEYBDINPUT),
        ("mi", _MOUSEINPUT),
        ("hi", _HARDWAREINPUT),
    ]

class _INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", _INPUT_UNION),
    ]

_user32 = ctypes.WinDLL('user32', use_last_error=True)
_user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(_INPUT), ctypes.c_int)
_user32.SendInput.restype = wintypes.UINT

def _sendKeyEvent(vk_code, key_up):
    """Inject a single key down or up event."""
    return _sendKeyEvents([(vk_code, key_up)])

def _sendKeyEvents(events):
    """Inject a batch of (vk_code, key_up) events atomically."""
    n = len(events)
    if n == 0:
        return True
    InputArray = _INPUT * n
    arr = InputArray()
    for i, (vk_code, key_up) in enumerate(events):
        arr[i].type = _INPUT_KEYBOARD
        arr[i].ki = _KEYBDINPUT(
            wVk=vk_code,
            wScan=0,
            dwFlags=(_KEYEVENTF_KEYUP if key_up else 0),
            time=0,
            dwExtraInfo=0,
        )
    sent = _user32.SendInput(n, arr, ctypes.sizeof(_INPUT))
    if sent != n:
        err = ctypes.get_last_error()
        print(f"[INPUT] ERROR: SendInput delivered {sent}/{n} events (err={err})")
        return False
    return True

def sendKeyPress(vk_code):
    """Press and release a key."""
    _sendKeyEvents([(vk_code, False), (vk_code, True)])
    sleep(KEY_SEQUENCE_DELAY)

def sendShiftedKeyPress(vk_code):
    """Press a key while holding Shift."""
    _sendKeyEvents([
        (win32con.VK_LSHIFT, False),
        (vk_code, False),
        (vk_code, True),
        (win32con.VK_LSHIFT, True),
    ])
    sleep(KEY_SEQUENCE_DELAY)

def sendCtrlCombo(vk_code):
    """Press a key while holding Ctrl."""
    try:
        _sendKeyEvents([
            (win32con.VK_CONTROL, False),
            (vk_code, False),
            (vk_code, True),
            (win32con.VK_CONTROL, True),
        ])
        sleep(KEY_SEQUENCE_DELAY)
        return True
    except Exception as e:
        print(f"[INPUT] ERROR sending Ctrl+VK 0x{vk_code:02X}: {e}")
        return False

def clearInputLine():
    """Clear the current console input line."""
    sendCtrlCombo(0x41)
    sendKeyPress(win32con.VK_BACK)
    sendKeyPress(win32con.VK_BACK)
    sendKeyPress(win32con.VK_BACK)

def sendCharacter(char):
    """Send a single character, respecting the current keyboard layout."""
    try:
        vk_result = win32api.VkKeyScan(char)

        if vk_result == -1:
            print(f"[INPUT] ERROR: Character '{char}' not found on current layout")
            return False

        vk_code = vk_result & 0xFF
        shift_state = (vk_result >> 8) & 0xFF

        if shift_state & 1:
            sendShiftedKeyPress(vk_code)
        else:
            sendKeyPress(vk_code)

        return True

    except Exception as e:
        print(f"[INPUT] ERROR sending character '{char}': {e}")
        return False

def sendString(text):
    """Paste the text via clipboard and press Enter to submit.

    Faster and layout-agnostic vs. typing one character at a time. The Ctrl+V
    and Enter events are batched so the game receives them in one burst.
    """
    try:
        pyperclip.copy(text)
    except Exception as e:
        print(f"[INPUT] ERROR copying to clipboard: {e}")
        return False

    sleep(CLIPBOARD_SETTLE_DELAY)

    ok = _sendKeyEvents([
        (win32con.VK_CONTROL, False),
        (0x56, False),
        (0x56, True),
        (win32con.VK_CONTROL, True),
        (win32con.VK_RETURN, False),
        (win32con.VK_RETURN, True),
    ])
    if not ok:
        return False

    sleep(POST_PASTE_DELAY)

    if COMMAND_COMPLETION_DELAY > 0:
        sleep(COMMAND_COMPLETION_DELAY)

    return True

def getConsoleKey():
    """Return the configured console key, or detect one from the keyboard layout. Cached."""
    global _console_key_cache

    if _console_key_cache is not None:
        return _console_key_cache

    try:
        import os
        cfg_path = os.path.join(os.getcwd(), "localconfig")
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    lines = f.read().splitlines()
                if len(lines) > 26 and lines[26].strip():
                    vk_val = int(lines[26].strip())
                    result = (None, vk_val)
                    _console_key_cache = result
                    return result
            except Exception:
                pass

        layout_id = win32api.GetKeyboardLayout(0)
        lang_id = layout_id & 0xFFFF

        french_layouts = [0x040C, 0x080C, 0x0C0C, 0x100C, 0x140C, 0x180C]

        if lang_id in french_layouts:
            print(f"[CONSOLE] Detected French layout (0x{lang_id:04X}), using '²'")
            result = ('²', None)
        else:
            print(f"[CONSOLE] Detected layout (0x{lang_id:04X}), using '`'")
            result = ('`', None)

        _console_key_cache = result
        return result

    except Exception as e:
        print(f"[CONSOLE] Layout detection failed: {e}, using '`'")
        result = ('`', None)
        _console_key_cache = result
        return result

def clearConsoleKeyCache():
    """Clear the cached console key to force re-detection."""
    global _console_key_cache
    _console_key_cache = None


def sendConsoleKey():
    """Send the appropriate console key."""
    console_char, configured_vk = getConsoleKey()
    if configured_vk is not None:
        print(f"[CONSOLE] Sending configured console VK: 0x{configured_vk:02X}")
        sendKeyPress(configured_vk)
        return True
    else:
        print(f"[CONSOLE] Sending console key: '{console_char}'")
        return sendCharacter(console_char)
