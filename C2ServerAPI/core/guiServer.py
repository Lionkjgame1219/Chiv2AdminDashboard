"""Provides a class encapsulating a chivalry 2 instance"""

import win32gui, win32process, win32api
from time import sleep
from . import inputLib

class Chivalry:
    """Class representing a running instance of the Chivalry 2 game.

    This class provides methods for interacting with the Chivalry 2 game programatically
        using windows input emulation. Using this class may cause difficulties using the
        computer for anything other than chivalry, and may even make it difficult for the
        user to close it depending on how it's used. USE WITH CAUTION!
    """
    def __init__(self):
        if self.getChivalryWindowHandle() == 0:
            raise RuntimeError("The Chivalry 2 window could not be found. Ensure that chivalry 2 is running\
                               on this machine.")


    __windowHandle = -1
    def getChivalryWindowHandle(self):
        """Obtains and returns the win32 window handle of a chivalry 2 process running on this computer.
        
        This function will only make the associated syscalls once. After that, the cached window handle from the
            first call will be returned instead, regardless of it's validity.
        """
        if self.__windowHandle != -1:
            return self.__windowHandle
        else:
            hwnd = win32gui.FindWindow(None, "Chivalry 2  ") #note the spaces after the 2 here. They're important.
            self.__windowHandle = hwnd
            sleep(0.1) #window handle doesn't seem to be valid until after a warmup period
            return hwnd

    def getFocus(self, hwnd):
        """Give the chivalry 2 window user focus."""
        remote_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
        win32process.AttachThreadInput(win32api.GetCurrentThreadId(), remote_thread, True)
        win32gui.SetFocus(hwnd)
        win32gui.SetForegroundWindow(hwnd)



    def consoleSend(self, message):
        """Send a command to the chivalry console.

        @param message: Command string to send to console
        """
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
        """Open the chivalry console into extended mode.

        PRECONDITION: The chivalry console is currently closed
        """
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
        """Save a preset to a slot.

        @param slot: The slot to save to (0-9)
        @param payload: The reason text or combined reason/duration to save
        """
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
        """Load the preset payload from a slot.

        @param slot: The slot to load from (0-9)
        @returns: The stored payload (string) or None if not found
        """
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
        """Get all saved presets as a dictionary.

        @returns: Dictionary with slot numbers as keys and payload strings as values
        """
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