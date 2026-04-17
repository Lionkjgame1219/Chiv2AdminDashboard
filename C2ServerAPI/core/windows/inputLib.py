"""Clean, reliable input system for Chivalry 2 console operations."""

from time import sleep
import win32api, win32con

KEY_PRESS_DURATION = 0.01
KEY_SEQUENCE_DELAY = 0.01
COMMAND_COMPLETION_DELAY = 0.0

_console_key_cache = None

def sendKeyPress(vk_code):
    """Send a single key press with reliable timing.

    @param vk_code: Virtual key code to press
    """
    win32api.keybd_event(vk_code, 0, 0)
    sleep(KEY_PRESS_DURATION)
    win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP)
    sleep(KEY_SEQUENCE_DELAY)

def sendShiftedKeyPress(vk_code):
    """Send a key press with shift modifier.

    @param vk_code: Virtual key code to press with shift
    """
    win32api.keybd_event(win32con.VK_LSHIFT, 0, 0)
    sleep(KEY_PRESS_DURATION / 2)
    win32api.keybd_event(vk_code, 0, 0)
    sleep(KEY_PRESS_DURATION)
    win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP)
    sleep(KEY_PRESS_DURATION / 2)
    win32api.keybd_event(win32con.VK_LSHIFT, 0, win32con.KEYEVENTF_KEYUP)
    sleep(KEY_SEQUENCE_DELAY)

def sendCtrlCombo(vk_code):
    """Send a Ctrl+<key> combo.

    @param vk_code: Virtual key code to press with Ctrl
    """
    try:
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0)
        sleep(KEY_PRESS_DURATION / 2)
        win32api.keybd_event(vk_code, 0, 0)
        sleep(KEY_PRESS_DURATION)
        win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP)
        sleep(KEY_PRESS_DURATION / 2)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP)
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
    """Send a single character using layout-aware mapping.

    @param char: Single character to send
    """
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
    """Send a string of characters.

    @param text: String to type
    """
    success = True
    for char in text:
        if not sendCharacter(char):
            success = False

    sendKeyPress(win32con.VK_RETURN)

    if COMMAND_COMPLETION_DELAY > 0:
        sleep(COMMAND_COMPLETION_DELAY)

    return success

def getConsoleKey():
    """Return configured console key if present, else detect by layout.

    Results are cached to avoid repeated disk I/O.
    """
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
