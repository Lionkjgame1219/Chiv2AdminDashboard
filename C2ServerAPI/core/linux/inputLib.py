"""Clean, reliable input system for Chivalry 2 console operations (Linux)."""

from time import sleep
import subprocess
import os

KEY_PRESS_DURATION = 0.01
KEY_SEQUENCE_DELAY = 0.01
COMMAND_COMPLETION_DELAY = 0.0

_console_key_cache = None

def get_xdotool_available():
    try:
        subprocess.run(['xdotool', '--version'], capture_output=True)
        return True
    except Exception:
        return False

def sendKeyPress(key_name):
    """Send a single key press with reliable timing."""
    subprocess.run(['xdotool', 'key', key_name])
    sleep(KEY_SEQUENCE_DELAY)

def sendShiftedKeyPress(key_name):
    """Send a key press with shift modifier."""
    subprocess.run(['xdotool', 'key', f'shift+{key_name}'])
    sleep(KEY_SEQUENCE_DELAY)

def sendCtrlCombo(key_name):
    """Send a Ctrl+<key> combo."""
    try:
        subprocess.run(['xdotool', 'key', f'ctrl+{key_name}'])
        sleep(KEY_SEQUENCE_DELAY)
        return True
    except Exception as e:
        print(f"[INPUT] ERROR sending Ctrl+{key_name}: {e}")
        return False

def clearInputLine():
    """Clear the current console input line."""
    sendCtrlCombo('a')
    sendKeyPress('BackSpace')
    sendKeyPress('BackSpace')
    sendKeyPress('BackSpace')

def sendCharacter(char):
    """Send a single character."""
    try:
        subprocess.run(['xdotool', 'type', '--clearmodifiers', char])
        return True
    except Exception as e:
        print(f"[INPUT] ERROR sending character '{char}': {e}")
        return False

def sendString(text):
    """Send a string of characters."""
    try:
        subprocess.run(['xdotool', 'type', '--clearmodifiers', '--delay', '10', text])
        sendKeyPress('Return')
        if COMMAND_COMPLETION_DELAY > 0:
            sleep(COMMAND_COMPLETION_DELAY)
        return True
    except Exception as e:
        print(f"[INPUT] ERROR sending string: {e}")
        return False

def getConsoleKey():
    """Return configured console key if present, else detect by layout."""
    global _console_key_cache

    if _console_key_cache is not None:
        return _console_key_cache

    try:
        cfg_path = os.path.join(os.getcwd(), "localconfig")
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    lines = f.read().splitlines()
                if len(lines) > 26 and lines[26].strip():
                    vk_val = int(lines[26].strip())
                    result = (None, None) 
                    _console_key_cache = result
                    return result
            except Exception:
                pass

        try:
            res = subprocess.run(['setxkbmap', '-query'], capture_output=True, text=True)
            layout = "us"
            for line in res.stdout.splitlines():
                if line.startswith("layout:"):
                    layout = line.split(":")[1].strip()
                    break
            
            if layout == "fr":
                print(f"[CONSOLE] Detected French layout, using 'twosuperior'")
                result = ('twosuperior', None)
            else:
                print(f"[CONSOLE] Detected layout {layout}, using 'grave'")
                result = ('grave', None)
        except Exception:
            result = ('grave', None)

        _console_key_cache = result
        return result

    except Exception as e:
        print(f"[CONSOLE] Layout detection failed: {e}, using 'grave'")
        result = ('grave', None)
        _console_key_cache = result
        return result

def clearConsoleKeyCache():
    """Clear the cached console key to force re-detection."""
    global _console_key_cache
    _console_key_cache = None

def sendConsoleKey():
    """Send the appropriate console key."""
    console_char, configured_vk = getConsoleKey()
    print(f"[CONSOLE] Sending console key: '{console_char}'")
    return sendKeyPress(console_char)
