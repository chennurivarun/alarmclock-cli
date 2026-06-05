"""Tests for the pure scheduling core, driven by fixed datetimes.

Reference week: 2024-01-01 is a Monday, so weekday indices line up as
Mon=Jan1 .. Sun=Jan7, Mon=Jan8.
"""

from datetime import datetime, time

from alarmclock.models import WEEKDAYS, Alarm
from alarmclock.scheduling import next_fire_at, upcoming


def alarm(t, repeat=frozenset(), enabled=True, id="1"):
    return Alarm(time=t, repeat_days=repeat, enabled=enabled, id=id)


def test_one_time_fires_today_when_still_ahead():
    now = datetime(2024, 1, 1, 6, 0)  # Mon 06:00
    assert next_fire_at(alarm(time(7, 30)), now) == datetime(2024, 1, 1, 7, 30)


def test_one_time_rolls_to_tomorrow_when_passed():
    now = datetime(2024, 1, 1, 8, 0)  # Mon 08:00, 07:30 already gone
    assert next_fire_at(alarm(time(7, 30)), now) == datetime(2024, 1, 2, 7, 30)


def test_one_time_at_exact_minute_fires_now():
    now = datetime(2024, 1, 1, 7, 30)
    assert next_fire_at(alarm(time(7, 30)), now) == datetime(2024, 1, 1, 7, 30)


def test_daily_today_then_tomorrow():
    a = alarm(time(7, 30), repeat=frozenset(range(7)))
    assert next_fire_at(a, datetime(2024, 1, 1, 6, 0)) == datetime(2024, 1, 1, 7, 30)
    assert next_fire_at(a, datetime(2024, 1, 1, 9, 0)) == datetime(2024, 1, 2, 7, 30)


def test_weekdays_skips_the_weekend():
    a = alarm(time(7, 30), repeat=WEEKDAYS)
    now = datetime(2024, 1, 5, 9, 0)  # Fri after the alarm -> next is Monday
    assert next_fire_at(a, now) == datetime(2024, 1, 8, 7, 30)


def test_disabled_alarm_never_fires():
    assert next_fire_at(alarm(time(7, 30), enabled=False), datetime(2024, 1, 1, 6, 0)) is None


def test_upcoming_is_sorted_and_drops_disabled():
    a1 = alarm(time(9, 0), id="1")
    a2 = alarm(time(7, 0), id="2")
    off = alarm(time(6, 0), enabled=False, id="3")
    result = upcoming([a1, a2, off], datetime(2024, 1, 1, 5, 0))
    assert [a.id for _, a in result] == ["2", "1"]
