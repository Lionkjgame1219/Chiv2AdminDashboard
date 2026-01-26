from time import sleep
import sys
import os

from .guiServer import Chivalry

class GameChivalry():
    def __init__(self):
        self.game = Chivalry()

    def ListPlayers(self):
        from time import sleep
        self.game.openConsole()
        self.game.consoleSend("listplayers")
        sleep(0.5)

    def banbyid(self, id, time, reason):
        self.game.openConsole()
        hours_text = f"{time} hour{'s' if time != 1 else ''}"

        if time > 24:
            days = time // 24
            days_text = f" ({'Nearly ' if time % 24 else ''}{days} day{'s' if days != 1 else ''})"
        else:
            days_text = ""

        self.game.consoleSend(f'banbyid {id} {time} "{reason}. Ban duration: {hours_text}{days_text}."')

    def unbanbyid(self, id):
        self.game.openConsole()
        self.game.consoleSend(f'unbanbyid {id}')
        
    def kickbyid(self, id, reason):
        self.game.openConsole()
        self.game.consoleSend(f'kickbyid {id} "{reason}"')

    def AddTime(self, time):
        self.game.openConsole()
        self.game.consoleSend(f'tbsaddstagetime {time}')

    def AdminSay(self, text):
        self.game.openConsole()
        self.game.consoleSend(f'adminsay {text}')

    def ServerSay(self, text):
        self.game.openConsole()
        self.game.consoleSend(f'serversay {text}')