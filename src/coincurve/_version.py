# This file is imported from __init__.py and exec'd from setup.py

MAJOR = 19
MINOR = 0
MICRO = 1
RELEASE = True

__version__ = '%d.%d.%d' % (MAJOR, MINOR, MICRO)

if not RELEASE:
    __version__ += '.dev0'
