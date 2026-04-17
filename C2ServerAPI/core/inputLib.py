"""Clean, reliable input system for Chivalry 2 console operations (Dispatcher)."""

import sys

if sys.platform == 'win32':
    from .windows.inputLib import *
else:
    from .linux.inputLib import *
