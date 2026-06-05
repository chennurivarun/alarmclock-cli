"""End-to-end runner tests with everything faked: no real time, sound, or input."""

import io
from datetime import datetime, time

from alarmclock.clock import FakeClock
from alarmclock.models import Alarm
from alarmclock.notifier import FakeNotifier
from alarmclock.runner import AlarmRunner
from alarmclock.storage import JsonAlarmStore


def _store(tmp_path, alarms):
    store = JsonAlarmStore(tmp_path / "a.json")
    store.save(alarms)
    return store


def _runner(store, clock, notifier, prompt):
    return AlarmRunner(store, clock, notifier, prompt=prompt, out=io.StringIO())


def test_one_time_fires_once_then_loop_ends(tmp_path):
    store = _store(tmp_path, [Alarm(time=time(7, 30), id="1")])
    notifier = FakeNotifier()
    _runner(store, FakeClock(datetime(2024, 1, 1, 7, 29)), notifier,
            prompt=lambda a: ("dismiss", 0)).run()

    assert len(notifier.fired) == 1
    assert store.load()[0].enabled is False  # one-time auto-disables


def test_snooze_then_dismiss_rings_twice(tmp_path):
    store = _store(tmp_path, [Alarm(time=time(7, 30), id="1")])
    notifier = FakeNotifier()
    replies = iter([("snooze", 1), ("dismiss", 0)])
    _runner(store, FakeClock(datetime(2024, 1, 1, 7, 29)), notifier,
            prompt=lambda a: next(replies)).run()

    assert len(notifier.fired) == 2


def test_quit_stops_after_current_alarm(tmp_path):
    store = _store(tmp_path, [Alarm(time=time(7, 30), id="1"), Alarm(time=time(8, 0), id="2")])
    notifier = FakeNotifier()
    _runner(store, FakeClock(datetime(2024, 1, 1, 7, 0)), notifier,
            prompt=lambda a: ("quit", 0)).run()

    assert len(notifier.fired) == 1  # rang the first, quit before the second


def test_no_alarms_reports_and_returns(tmp_path):
    out = io.StringIO()
    runner = AlarmRunner(_store(tmp_path, []), FakeClock(datetime(2024, 1, 1, 7, 0)),
                         FakeNotifier(), prompt=lambda a: ("dismiss", 0), out=out)
    runner.run()

    assert "No upcoming alarms" in out.getvalue()
