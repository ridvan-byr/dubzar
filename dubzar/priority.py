"""Keep the app out of the game's way."""

import sys

import psutil


def lower_priority() -> bool:
    """Run this process below normal priority so the game always wins when cores are scarce.

    Returns False (and carries on) when the system refuses: a refusal must never stop the app.
    """
    try:
        me = psutil.Process()
        me.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS if sys.platform == "win32" else 10)
        return True
    except (psutil.Error, OSError):
        return False
