"""Provides a class encapsulating a chivalry 2 instance (Dispatcher)"""

import sys

if sys.platform == 'win32':
    from .windows.guiServer import *
else:
    from .linux.guiServer import *

