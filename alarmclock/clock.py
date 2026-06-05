"""The time authority, behind a small protocol so tests can replace it.

``now()`` answers "what time is it" and ``sleep_until()`` owns the waiting. Putting
the wait here (rather than in the runner) means the fake clock can jump straight to
the target in one step, so runner tests are instant instead of looping per second.
"""

from __future__ import annotations

import time as _time
from datetime import datetime
from typing import Callable, Optional, Protocol

OnTick = Optional[Callable[[datetime], None]]


class Clock(Protocol):
    def now(self) -> datetime: ...

    def sleep_until(self, target: datetime, on_tick: OnTick = None) -> None: ...


class SystemClock:
    """Real wall-clock time. Sleeps in 1-second ticks so a countdown can render."""

    def now(self) -> datetime:
        return datetime.now()

    def sleep_until(self, target: datetime, on_tick: OnTick = None) -> None:
        while True:
            now = self.now()
            remaining = (target - now).total_seconds()
            if remaining <= 0:
                return
            if on_tick is not None:
                on_tick(now)
            _time.sleep(min(1.0, remaining))


class FakeClock:
    """Deterministic clock for tests. ``sleep_until`` jumps straight to the target."""

    def __init__(self, now: datetime):
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs) -> None:
        from datetime import timedelta

        self._now += timedelta(**kwargs)

    def sleep_until(self, target: datetime, on_tick: OnTick = None) -> None:
        if on_tick is not None:
            on_tick(self._now)
        if target > self._now:
            self._now = target
