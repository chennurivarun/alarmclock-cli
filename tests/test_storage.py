import json
from datetime import time

from alarmclock.models import WEEKDAYS, Alarm
from alarmclock.storage import JsonAlarmStore, resolve_db_path


def test_missing_file_loads_as_empty(tmp_path):
    assert JsonAlarmStore(tmp_path / "nope.json").load() == []


def test_save_then_load_round_trips(tmp_path):
    store = JsonAlarmStore(tmp_path / "a.json")
    alarms = [
        Alarm(time=time(7, 30), label="Wake", repeat_days=WEEKDAYS, id="1"),
        Alarm(time=time(22, 0), id="2"),
    ]
    store.save(alarms)
    assert store.load() == alarms


def test_save_is_atomic_and_overwrites_cleanly(tmp_path):
    path = tmp_path / "a.json"
    store = JsonAlarmStore(path)
    store.save([Alarm(time=time(7, 0), id="1")])
    store.save([Alarm(time=time(8, 0), id="1")])  # overwrite

    assert path.exists()
    assert not (tmp_path / "a.json.tmp").exists()  # temp file swapped away
    assert json.loads(path.read_text())[0]["time"] == "08:00"


def test_resolve_db_path_precedence(tmp_path, monkeypatch):
    monkeypatch.setenv("ALARMCLOCK_DB", str(tmp_path / "env.json"))
    # explicit flag beats env
    assert resolve_db_path(str(tmp_path / "cli.json")) == tmp_path / "cli.json"
    # env beats default
    assert resolve_db_path(None) == tmp_path / "env.json"
    # default when neither is set
    monkeypatch.delenv("ALARMCLOCK_DB")
    assert resolve_db_path(None).name == "alarms.json"
