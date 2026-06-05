"""Pure scheduling logic — the heart of the alarm clock.

No clock, no sleeping, no I/O. Every function takes ``now`` as an argument, which
is what lets the tests drive time deterministically with a fake clock.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .models import Alarm


def next_fire_at(alarm: Alarm, now: datetime) -> datetime | None:
    """Return the next datetime ``alarm`` should fire at, at or after ``now``.

    Returns ``None`` for a disabled alarm. Alarm times have minute precision, so
    candidates always land on a ``:00`` second.

    - One-time alarm (empty ``repeat_days``): today's occurrence if it is still
      ahead of ``now``, otherwise tomorrow's.
    - Recurring alarm: the soonest day whose weekday is in ``repeat_days`` and
      whose time matches — scanning forward up to a week, which is guaranteed to
      contain a match.
    """
    if not alarm.enabled:
        return None

    if alarm.is_one_time:
        today = datetime.combine(now.date(), alarm.time)
        return today if today >= now else today + timedelta(days=1)

    # Recurring: scan up to 8 days so we always find a qualifying weekday >= now.
    for offset in range(8):
        day = now.date() + timedelta(days=offset)
        if day.weekday() in alarm.repeat_days:
            candidate = datetime.combine(day, alarm.time)
            if candidate >= now:
                return candidate
    return None  # unreachable for a non-empty repeat set, but keeps types honest


def upcoming(alarms: list[Alarm], now: datetime) -> list[tuple[datetime, Alarm]]:
    """All enabled alarms paired with their next fire time, soonest first."""
    scheduled = []
    for alarm in alarms:
        fire_at = next_fire_at(alarm, now)
        if fire_at is not None:
            scheduled.append((fire_at, alarm))
    scheduled.sort(key=lambda pair: pair[0])
    return scheduled
