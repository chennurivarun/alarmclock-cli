from datetime import time

import pytest

from alarmclock.models import (
    EVERY_DAY,
    WEEKDAYS,
    WEEKENDS,
    Alarm,
    format_repeat,
    next_id,
    parse_repeat,
    parse_time,
)


def test_parse_time_accepts_padded_and_unpadded():
    assert parse_time("7:30") == time(7, 30)
    assert parse_time("07:05") == time(7, 5)
    assert parse_time("23:59") == time(23, 59)


@pytest.mark.parametrize("bad", ["7", "7:60", "24:00", "abc", "7:30:00", "-1:00", ""])
def test_parse_time_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse_time(bad)


def test_parse_repeat_aliases():
    assert parse_repeat("once") == frozenset()
    assert parse_repeat("") == frozenset()
    assert parse_repeat("daily") == EVERY_DAY
    assert parse_repeat("weekdays") == WEEKDAYS
    assert parse_repeat("weekends") == WEEKENDS


def test_parse_repeat_comma_list_is_order_insensitive():
    assert parse_repeat("mon,wed,fri") == frozenset({0, 2, 4})
    assert parse_repeat("SUN, mon") == frozenset({6, 0})


def test_parse_repeat_rejects_unknown_day():
    with pytest.raises(ValueError):
        parse_repeat("funday")


@pytest.mark.parametrize("spec", ["once", "daily", "weekdays", "weekends", "mon,wed,fri"])
def test_format_repeat_round_trips(spec):
    assert format_repeat(parse_repeat(spec)) == spec


def test_alarm_survives_a_dict_round_trip():
    a = Alarm(time=time(7, 30), label="Wake", repeat_days=WEEKDAYS, enabled=False, id="3")
    assert Alarm.from_dict(a.to_dict()) == a


def test_next_id_starts_at_one_and_fills_gaps():
    mk = lambda i: Alarm(time=time(7, 0), id=i)
    assert next_id([]) == "1"
    assert next_id([mk("1"), mk("3")]) == "2"
    assert next_id([mk("1"), mk("2")]) == "3"
