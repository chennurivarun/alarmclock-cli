"""How an alarm makes itself known, behind a protocol so tests stay silent.

``ConsoleNotifier`` rings the terminal bell and, on macOS, plays a system sound
best-effort. Anywhere that has no ``afplay`` simply falls back to the bell.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from typing import List, Protocol

from .models import Alarm

_MACOS_SOUND = "/System/Library/Sounds/Glass.aiff"


class Notifier(Protocol):
    def notify(self, alarm: Alarm) -> None: ...


class ConsoleNotifier:
    """Print a banner, ring the terminal bell, and play a sound if we can."""

    def __init__(self, out=None, play_sound: bool = True):
        self._out = out if out is not None else sys.stdout
        self._play_sound = play_sound

    def notify(self, alarm: Alarm) -> None:
        label = alarm.label or "Alarm"
        when = alarm.time.strftime("%H:%M")
        # \a is the terminal bell — works in any terminal, no dependencies.
        self._out.write(f"\a\n⏰  {when}  {label}\n")
        self._out.flush()
        if self._play_sound:
            self._ring()

    def _ring(self) -> None:
        afplay = shutil.which("afplay")
        if afplay is None:
            return  # no system sound available; the bell already fired
        try:
            subprocess.Popen(
                [afplay, _MACOS_SOUND],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            pass  # sound is a nice-to-have, never fatal


class FakeNotifier:
    """Records what it was asked to ring, for assertions in tests."""

    def __init__(self):
        self.fired: List[Alarm] = []

    def notify(self, alarm: Alarm) -> None:
        self.fired.append(alarm)
