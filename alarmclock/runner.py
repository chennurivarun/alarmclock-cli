"""The blocking ``run`` loop: wait for the soonest alarm, ring it, handle the reply.

Everything fragile is injected — the clock (waiting + time), the notifier (sound),
and the prompt (the user's dismiss/snooze/quit answer) — so the loop itself is a
plain, deterministic state machine that tests drive end to end without real time,
real sound, or real keyboard input.
"""

from __future__ import annotations

import sys
from datetime import timedelta
from typing import Callable, List, Tuple

from .clock import Clock
from .models import Alarm
from .notifier import Notifier
from .scheduling import upcoming
from .storage import JsonAlarmStore

# A prompt answers a ringing alarm with one of these actions.
Action = Tuple[str, int]  # ("dismiss", 0) | ("snooze", minutes) | ("quit", 0)
Prompt = Callable[[Alarm], Action]


class ConsolePrompt:
    """Reads the user's reply to a ringing alarm from a stream."""

    def __init__(self, default_snooze: int = 9, in_=None, out=None):
        self._default_snooze = default_snooze
        self._in = in_ if in_ is not None else sys.stdin
        self._out = out if out is not None else sys.stdout

    def __call__(self, alarm: Alarm) -> Action:
        self._out.write("  [d]ismiss / [s]nooze / [q]uit? ")
        self._out.flush()
        line = self._in.readline()
        if not line:  # EOF (e.g. piped/no tty) — treat as dismiss
            return ("dismiss", 0)
        choice = line.strip().lower()
        if choice in ("q", "quit"):
            return ("quit", 0)
        if choice in ("s", "snooze"):
            return ("snooze", self._default_snooze)
        if choice.isdigit():
            return ("snooze", int(choice))
        return ("dismiss", 0)


class AlarmRunner:
    def __init__(
        self,
        store: JsonAlarmStore,
        clock: Clock,
        notifier: Notifier,
        prompt: Prompt,
        out=None,
    ):
        self._store = store
        self._clock = clock
        self._notifier = notifier
        self._prompt = prompt
        self._out = out if out is not None else sys.stdout

    def run(self) -> None:
        """Loop until there is nothing left to ring (or the user quits)."""
        cursor = self._clock.now()
        snoozes: List[Tuple] = []  # (fire_dt, Alarm) entries, separate from the store

        while True:
            alarms = self._store.load()  # reload so a dismissed one-time drops out
            schedule = upcoming(alarms, cursor)
            schedule += [(t, a) for (t, a) in snoozes if t >= cursor]
            if not schedule:
                self._out.write("No upcoming alarms.\n")
                self._out.flush()
                return

            schedule.sort(key=lambda pair: pair[0])
            soonest = schedule[0][0]
            due = [alarm for (fire_at, alarm) in schedule if fire_at == soonest]

            self._clock.sleep_until(
                soonest,
                lambda now, a=due[0]: self._render_countdown(now, soonest, a),
            )
            self._clear_countdown()

            # Any snooze scheduled for this instant is now consumed.
            snoozes = [(t, a) for (t, a) in snoozes if t != soonest]

            for alarm in due:
                self._notifier.notify(alarm)
                action, minutes = self._prompt(alarm)
                if action == "quit":
                    return
                if action == "snooze":
                    when = self._clock.now() + timedelta(minutes=minutes)
                    snoozes.append((when, alarm))
                    self._out.write(f"  snoozed {minutes} min.\n")
                else:  # dismiss
                    if alarm.is_one_time:
                        self._disable(alarm.id)

            cursor = soonest + timedelta(seconds=1)

    def _disable(self, alarm_id: str) -> None:
        alarms = self._store.load()
        for alarm in alarms:
            if alarm.id == alarm_id:
                alarm.enabled = False
        self._store.save(alarms)

    def _render_countdown(self, now, target, alarm: Alarm) -> None:
        secs = max(0, int((target - now).total_seconds()))
        hours, rem = divmod(secs, 3600)
        minutes, seconds = divmod(rem, 60)
        label = alarm.label or "alarm"
        self._out.write(
            f"\r⏳ next {alarm.time.strftime('%H:%M')} {label} "
            f"in {hours:02d}:{minutes:02d}:{seconds:02d}   "
        )
        self._out.flush()

    def _clear_countdown(self) -> None:
        self._out.write("\r" + " " * 60 + "\r")
        self._out.flush()
