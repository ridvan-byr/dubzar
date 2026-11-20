import sys

import psutil
import pytest

from dubzar.priority import lower_priority


@pytest.mark.skipif(sys.platform != "win32", reason="Windows priority classes")
def test_lower_priority_puts_this_process_below_normal_and_can_be_undone():
    me = psutil.Process()
    original = me.nice()
    try:
        assert lower_priority() is True
        assert me.nice() == psutil.BELOW_NORMAL_PRIORITY_CLASS
    finally:
        me.nice(original)


def test_lower_priority_never_raises_when_the_system_refuses(monkeypatch):
    class Refusing:
        def nice(self, *args):
            raise psutil.AccessDenied()

    monkeypatch.setattr(psutil, "Process", lambda *a, **k: Refusing())

    assert lower_priority() is False  # a refusal must not stop the app from starting
