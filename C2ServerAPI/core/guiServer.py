"""Wrapper around a running Chivalry 2 instance."""

import win32gui, win32process, win32api
from time import sleep
from . import inputLib

class Chivalry:
    """A running Chivalry 2 game, driven via Windows input emulation.

    Heavy use of this class can make the computer hard to use for anything else
    while it's running — sometimes even hard to close. Use with caution.
    """
    def __init__(self):
        if self.getChivalryWindowHandle() == 0:
            raise RuntimeError("The Chivalry 2 window could not be found. Ensure that chivalry 2 is running\
                               on this machine.")


    __windowHandle = -1
    def getChivalryWindowHandle(self):
        """Return the cached win32 handle of the Chivalry 2 window, looking it up on first call."""
        if self.__windowHandle != -1:
            return self.__windowHandle
        else:
            # The trailing spaces in the window title are intentional.
            hwnd = win32gui.FindWindow(None, "Chivalry 2  ")
            self.__windowHandle = hwnd
            sleep(0.1)  # handle isn't reliably valid until after a brief warmup
            return hwnd

    def getFocus(self, hwnd):
        """Bring the Chivalry 2 window to the foreground.

        We only attach the thread input queue for the SetFocus/SetForegroundWindow
        calls and detach immediately after. Staying attached makes the dashboard
        and game share an input queue, which causes injected keystrokes to drain
        in a batch instead of arriving at the game one by one.
        """
        remote_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
        own_thread = win32api.GetCurrentThreadId()
        attached = False
        try:
            win32process.AttachThreadInput(own_thread, remote_thread, True)
            attached = True
            win32gui.SetFocus(hwnd)
            win32gui.SetForegroundWindow(hwnd)
        finally:
            if attached:
                try:
                    win32process.AttachThreadInput(own_thread, remote_thread, False)
                except Exception:
                    pass
        sleep(0.5)  # focus needs a warmup before short commands (e.g. listplayers) won't race



    def consoleSend(self, message):
        """Send a command to the Chivalry console."""
        hwnd = self.getChivalryWindowHandle()
        print(f"[CONSOLESEND] Game window handle: {hwnd}")
        self.getFocus(hwnd)

        try:
            import win32gui
            for _ in range(40):
                if win32gui.GetForegroundWindow() == hwnd:
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
        """Open the Chivalry console in extended mode. Assumes the console is currently closed."""
        print("[OPENCONSOLE] Opening console...")
        hwnd = self.getChivalryWindowHandle()
        print(f"[OPENCONSOLE] Game window handle: {hwnd}")
        self.getFocus(hwnd)

        try:
            import win32gui
            for _ in range(40):
                if win32gui.GetForegroundWindow() == hwnd:
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
        """Save a preset payload to slot 0-9."""
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
        """Load the preset payload from slot 0-9, or None if empty."""
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
        """Return all saved presets as {slot_str: payload}."""
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