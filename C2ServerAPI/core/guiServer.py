"""Wrapper around a running Chivalry 2 instance."""

import win32gui, win32process, win32api
from time import sleep
from . import inputLib
from . import localconfig

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
        return localconfig.set_value(localconfig.preset_key(slot), payload)

    def LoadPreset(self, slot):
        """Load the preset payload from slot 0-9, or None if empty."""
        payload = localconfig.get_value(localconfig.preset_key(slot))
        return payload if payload.strip() else None

    def GetAllPresets(self):
        """Return all saved presets as {slot_str: payload}."""
        settings = localconfig.load_all()
        presets = {}
        for i in range(localconfig.PRESET_COUNT):
            payload = settings.get(localconfig.preset_key(i), '')
            if payload.strip():
                presets[str(i)] = payload
        return presets