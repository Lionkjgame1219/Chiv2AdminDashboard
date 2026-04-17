"""Provides a class encapsulating a chivalry 2 instance (Linux/X11)"""

import subprocess
from time import sleep
from . import inputLib

def check_chivalry_window():
    """Check if Chivalry 2 window is available"""
    try:
        result = subprocess.run(['xdotool', 'search', '--name', 'Chivalry 2'], capture_output=True, text=True)
        return bool(result.stdout.strip())
    except Exception:
        return False

class Chivalry:
    def __init__(self):
        self.__windowHandle = -1
        if self.getChivalryWindowHandle() == 0:
            raise RuntimeError("The Chivalry 2 window could not be found. Ensure that chivalry 2 is running")

    def getChivalryWindowHandle(self):
        """Obtains and returns the X11 window ID of a chivalry 2 process."""
        if self.__windowHandle != -1:
            return self.__windowHandle
        else:
            try:
                result = subprocess.run(['xdotool', 'search', '--name', 'Chivalry 2'], capture_output=True, text=True)
                ids = result.stdout.strip().splitlines()
                if ids:
                    self.__windowHandle = ids[0]
                    sleep(0.1)
                    return self.__windowHandle
            except Exception:
                pass
            return 0

    def getFocus(self, hwnd):
        """Give the chivalry 2 window user focus."""
        try:
            subprocess.run(['xdotool', 'windowactivate', '--sync', str(hwnd)])
        except Exception:
            pass

    def consoleSend(self, message):
        """Send a command to the chivalry console."""
        hwnd = self.getChivalryWindowHandle()
        print(f"[CONSOLESEND] Game window handle: {hwnd}")
        self.getFocus(hwnd)

        try:
            # Wait until it is active
            for _ in range(40):
                result = subprocess.run(['xdotool', 'getactivewindow'], capture_output=True, text=True)
                active = result.stdout.strip()
                if active == str(hwnd):
                    break
                sleep(0.005)
        except Exception:
            pass

        try:
            inputLib.clearInputLine()
        except Exception:
            pass

        print(f"[CONSOLESEND] Sending command: '{message}'")
        success = inputLib.sendString(message)

        if success:
            print("[CONSOLESEND] Command sent successfully")
        else:
            print("[CONSOLESEND] ERROR: Command sending failed")

    def openConsole(self):
        """Open the chivalry console into extended mode."""
        print("[OPENCONSOLE] Opening console...")
        hwnd = self.getChivalryWindowHandle()
        print(f"[OPENCONSOLE] Game window handle: {hwnd}")
        self.getFocus(hwnd)

        try:
            for _ in range(40):
                result = subprocess.run(['xdotool', 'getactivewindow'], capture_output=True, text=True)
                active = result.stdout.strip()
                if active == str(hwnd):
                    break
                sleep(0.005)
        except Exception:
            pass

        print("[OPENCONSOLE] Sending console key...")
        success = inputLib.sendConsoleKey()

        if success:
            print("[OPENCONSOLE] Console opened successfully")
            sleep(0.08)
        else:
            print("[OPENCONSOLE] ERROR: Console opening failed")

    def SavePreset(self, slot, payload):
        """Save a preset to a slot."""
        import os
        localconfig = "localconfig"
        lines = []
        if os.path.exists(localconfig):
            try:
                with open(localconfig, 'r', encoding='utf-8') as f:
                    lines = f.read().splitlines()
            except Exception:
                lines = []
        min_len = 13
        if len(lines) < min_len:
            lines += [""] * (min_len - len(lines))
        preset_index = 3 + int(slot)
        if len(lines) <= preset_index:
            lines += [""] * (preset_index + 1 - len(lines))
        lines[preset_index] = payload if payload is not None else ""
        try:
            with open(localconfig, 'w', encoding='utf-8') as f:
                for line in lines:
                    f.write(line + "\n")
            return True
        except Exception:
            return False

    def LoadPreset(self, slot):
        """Load the preset payload from a slot."""
        import os
        localconfig = "localconfig"
        if not os.path.exists(localconfig):
            return None
        try:
            with open(localconfig, 'r', encoding='utf-8') as f:
                lines = f.read().strip().split('\n')
                preset_line_index = 3 + slot
                if len(lines) > preset_line_index and lines[preset_line_index].strip():
                    return lines[preset_line_index]
                return None
        except Exception:
            return None

    def GetAllPresets(self):
        """Get all saved presets as a dictionary."""
        import os
        localconfig = "localconfig"
        presets = {}
        if not os.path.exists(localconfig):
            return presets
        try:
            with open(localconfig, 'r', encoding='utf-8') as f:
                lines = f.read().strip().split('\n')
                for i in range(10):
                    preset_line_index = 3 + i
                    if len(lines) > preset_line_index and lines[preset_line_index].strip():
                        presets[str(i)] = lines[preset_line_index]
        except Exception:
            pass
        return presets
