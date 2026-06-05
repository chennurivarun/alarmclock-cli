"""Domain model: the ``Alarm`` and the pure parsing/formatting helpers around it.

This module has no I/O and depends only on the standard library, so everything in
it is trivially unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time

# Weekday indices follow ``datetime.weekday()``: Monday is 0, Sunday is 6.
WEEKDAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_NAME_TO_INDEX = {name: i for i, name in enumerate(WEEKDAY_NAMES)}

WEEKDAYS = frozenset({0, 1, 2, 3, 4})
WEEKENDS = frozenset({5, 6})
EVERY_DAY = frozenset(range(7))


def parse_time(value: str) -> time:
    """Parse ``H:MM`` or ``HH:MM`` (24-hour) into a ``datetime.time``.

    Raises ``ValueError`` with a friendly message on anything else.
    """
    value = value.strip()
    parts = value.split(":")
    if len(parts) != 2:
        raise ValueError(f"time must look like HH:MM, got {value!r}")
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except ValueError:
        raise ValueError(f"time must look like HH:MM, got {value!r}") from None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"time out of range (00:00–23:59), got {value!r}")
    return time(hour=hour, minute=minute)


def parse_repeat(spec: str) -> frozenset[int]:
    """Parse a ``--repeat`` spec into a set of weekday indices.

    An **empty set means "one-time"** — that single rule keeps one-shot and
    recurring alarms on the same code path everywhere downstream.

    Accepts: ``once`` | ``daily`` | ``weekdays`` | ``weekends`` | a comma list
    such as ``mon,wed,fri``. Raises ``ValueError`` on anything unrecognised.
    """
    spec = (spec or "").strip().lower()
    if spec in ("", "once", "one-time", "onetime"):
        return frozenset()
    if spec == "daily":
        return EVERY_DAY
    if spec == "weekdays":
        return WEEKDAYS
    if spec == "weekends":
        return WEEKENDS

    days = set()
    for token in spec.split(","):
        token = token.strip()
        if token not in _NAME_TO_INDEX:
            raise ValueError(
                f"unknown day {token!r}; use mon,tue,wed,thu,fri,sat,sun "
                f"or once/daily/weekdays/weekends"
            )
        days.add(_NAME_TO_INDEX[token])
    return frozenset(days)


def format_repeat(repeat_days: frozenset[int]) -> str:
    """Render a repeat set back to the most readable label for ``list`` output."""
    if not repeat_days:
        return "once"
    if repeat_days == EVERY_DAY:
        return "daily"
    if repeat_days == WEEKDAYS:
        return "weekdays"
    if repeat_days == WEEKENDS:
        return "weekends"
    return ",".join(WEEKDAY_NAMES[i] for i in sorted(repeat_days))


@dataclass
class Alarm:
    """A single alarm. ``repeat_days`` empty means it fires once then disables."""

    time: time
    label: str = ""
    repeat_days: frozenset[int] = field(default_factory=frozenset)
    enabled: bool = True
    id: str = ""

    @property
    def is_one_time(self) -> bool:
        return not self.repeat_days

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "time": self.time.strftime("%H:%M"),
            "repeat_days": sorted(self.repeat_days),
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Alarm":
        return cls(
            id=data["id"],
            label=data.get("label", ""),
            time=parse_time(data["time"]),
            repeat_days=frozenset(data.get("repeat_days", [])),
            enabled=data.get("enabled", True),
        )


def next_id(alarms: list[Alarm]) -> str:
    """Smallest positive integer id not already taken, as a string.

    Integer ids keep the CLI friendly (``alarm remove 2``); reusing freed ids
    keeps them short over time.
    """
    used = set()
    for alarm in alarms:
        try:
            used.add(int(alarm.id))
        except (TypeError, ValueError):
            continue
    candidate = 1
    while candidate in used:
        candidate += 1
    return str(candidate)
