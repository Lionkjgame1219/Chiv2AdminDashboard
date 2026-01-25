"""Provides a class encapsulating a chivalry 2 instance"""

import win32gui, win32process, win32api
from time import sleep
from . import inputLib

class Chivalry:
    """Class representing a running instance of the Chivalry 2 game.

    This class provides numerous methods for interacting with the Chivalry 2 game programatically.
        Functionality is implemented using a combination of OCR and windows input emulation. Using
        this class may cause difficulties using the computer for anything other than chivalry, and may even
        make it difficult for the user to close it depending on how it's used. USE WITH CAUTION!
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

    def checkInGameConsoleOpen(self):
        """Returns true or false, indicating if the in-game console is currently open in extended mode."""
        screenshot = self.getChivScreenshot()
        width, height = screenshot.size
        screenshot = screenshot.crop((0, height*(47/64)+2, width*0.02, height*(49/64)-2))
        try:
            screenshot = screenshot.quantize(colors=256).convert(mode="1").convert(mode="RGB")
        except Exception:
            pass
        try:
            import pytesseract
            print(pytesseract.image_to_string(screenshot))
        except Exception:
            print("[OCR] pytesseract not available; skipping OCR in checkInGameConsoleOpen")
        
    def getChivScreenshot(self, tabDown=False):
        """Returns a PIL image of the entire chivalry 2 window."""
        hwnd = self.getChivalryWindowHandle()
        self.getFocus(hwnd)
        sleep(0.1)
        if tabDown:
            inputLib.tabDown()
            sleep(0.1)

        windowRect = win32gui.GetWindowRect(hwnd)
        try:
            from PIL import ImageGrab
            image = ImageGrab.grab(windowRect)
        except Exception as e:
            raise RuntimeError("Pillow (PIL) is required for screenshot operations but is not installed.") from e
        if tabDown:
            inputLib.tabUp()
            sleep(0.1)

        return image

    def getConsoleOutput(self):
        """Returns the currently displayed output of the chivalry console window as a string using OCR.

        PRECONDITION: The chivalry console must be opened and visible in extended mode.
        """
        screenshot = self.getChivScreenshot()
        width, height = screenshot.size
        screenshot = screenshot.crop((0, 0, width, height*(47/64)-2))
        screenshot = screenshot.quantize(colors=256).convert(mode="1").convert(mode="RGB")
        try:
            import pytesseract
            text = pytesseract.image_to_string(screenshot)
        except Exception as e:
            raise RuntimeError("pytesseract is required for OCR operations but is not installed.") from e
        return [s for s in text.splitlines() if s]

    def getTimeRemaining(self):
        """Return the time remaining in the game as a string using OCR.

        NOTE: The in-game console should not be open in extended mode when this function is called.
        """
        screenshot = self.getChivScreenshot()
        width, height = screenshot.size
        screenshot = screenshot.crop((0.45*width, 0.08*height, 0.55*width, 0.13*height))
        screenshot = screenshot.quantize(colors=128).convert(mode="RGB")
        try:
            import pytesseract
            return pytesseract.image_to_string(screenshot)
        except Exception as e:
            raise RuntimeError("pytesseract is required for OCR operations but is not installed.") from e
    
    def getPlayerCount(self):
        return 0
    def getPlayerList(self):
        screenshot = self.getChivScreenshot(tabDown=True)
        width, height = screenshot.size

        left = int(width * 0.75)
        top = int(height * 0.15)
        right = int(width * 0.95)
        bottom = int(height * 0.70)

        player_list_img = screenshot.crop((left, top, right, bottom))
        player_list_img = player_list_img.convert("L")
        player_list_img = player_list_img.point(lambda x: 0 if x < 128 else 255, '1')

        try:
            import pytesseract
            text = pytesseract.image_to_string(player_list_img)
        except Exception as e:
            raise RuntimeError("pytesseract is required for OCR operations but is not installed.") from e

        lines = text.splitlines()
        players = [line.strip() for line in lines if line.strip() != ""]

        return players

    def isGameEnd(self):
        """Returns true or false, indicating whether or not the game is currently in a game-end state.

        PRECONDITION: The game client is in spectator mode

        NOTE: The UI elements used to detect this are the "GAME END" and "VICTOR" in-game overlays.
            These assume that the client is in spectator mode at game end to get these specific messages.
        """
        screenshot = self.getChivScreenshot()
        width, height = screenshot.size
        #crop to location of game end notification on screen
        screenshot = screenshot.crop((0.3*width, 0.75*height, 0.7*width, 0.9*height))

        screenshot = screenshot.quantize(colors=128).convert(mode="1").convert(mode="RGB")
        try:
            import pytesseract
            result = pytesseract.image_to_string(screenshot)
        except Exception as e:
            raise RuntimeError("pytesseract is required for OCR operations but is not installed.") from e
        if "GAME END" in result or "VICTOR" in result:
            return True
        else:
            return False
        
    def isMainMenu(self):
        """Returns true or false, indicating if the client is currently at the chivalry main menu.
        """
        screenshot = self.getChivScreenshot()
        width, height = screenshot.size
        #crop to location of exit game button on main menu on screen
        screenshot = screenshot.crop((0.072*width, 0.94*height, 0.13*width, 0.97*height))

        screenshot = screenshot.quantize(colors=128).convert(mode="RGB")
        try:
            import pytesseract
            result = pytesseract.image_to_string(screenshot)
        except Exception as e:
            raise RuntimeError("pytesseract is required for OCR operations but is not installed.") from e
        #print(result)
        if "EXIT GAME" in result:
            return True
        else:
            return False

    def getRecentCommandOutput(self, command, lines):
        """Returns the output of a command that was recently run.

        PRECONDITION: The extended view of the console is open in chivalry

        @param command: A string containing the command that was run
        @param lines: How many lines of output to return
        @returns The output of the run command as a string, or None
        """
        console = self.getConsoleOutput()
        strippedConsole = [
            (index, s.replace(" ", ""))
            for index,s in enumerate(console)
            if ">>" in s and "<<" in s
        ]
        for i, s in reversed(strippedConsole):
            if command.replace(" ", "") in s:
                if i < len(console)-1:
                    n = lines+1
                    return console[i+1:i+n] if i+n < len(console) else console[i+1:]
                else:
                    return None
        return None

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