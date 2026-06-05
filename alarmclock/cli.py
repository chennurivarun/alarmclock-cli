"""Argparse front end — a thin shell that parses, calls into the core, and prints.

Deliberately holds no logic of its own: parsing and formatting only. Anything worth
testing lives in the modules underneath.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from .clock import SystemClock
from .models import Alarm, format_repeat, next_id, parse_repeat, parse_time
from .notifier import ConsoleNotifier
from .runner import AlarmRunner, ConsolePrompt
from .scheduling import next_fire_at
from .storage import JsonAlarmStore, resolve_db_path


def _store(args) -> JsonAlarmStore:
    return JsonAlarmStore(resolve_db_path(args.db))


def _find(alarms, alarm_id):
    return next((a for a in alarms if a.id == alarm_id), None)


def cmd_add(args) -> int:
    store = _store(args)
    alarm = Alarm(
        time=parse_time(args.time),
        label=args.label or "",
        repeat_days=parse_repeat(args.repeat),
    )
    alarms = store.load()
    alarm.id = next_id(alarms)
    alarms.append(alarm)
    store.save(alarms)
    print(f"Added alarm {alarm.id}: {alarm.time.strftime('%H:%M')} "
          f"({format_repeat(alarm.repeat_days)})"
          + (f" — {alarm.label}" if alarm.label else ""))
    return 0


def cmd_list(args) -> int:
    store = _store(args)
    alarms = store.load()
    if not alarms:
        print("No alarms set. Add one with:  alarm add 07:30 --label Wake")
        return 0

    now = SystemClock().now()
    rows = []
    for a in sorted(alarms, key=lambda x: (x.time.hour, x.time.minute)):
        status = "on" if a.enabled else "off"
        fire = next_fire_at(a, now)
        nxt = _humanize_until(fire, now) if fire else "—"
        rows.append((a.id, a.time.strftime("%H:%M"), format_repeat(a.repeat_days),
                     status, nxt, a.label or ""))

    headers = ("ID", "TIME", "REPEAT", "STATUS", "NEXT", "LABEL")
    widths = [max(len(str(r[i])) for r in (headers, *rows)) for i in range(len(headers))]
    line = lambda cols: "  ".join(str(c).ljust(widths[i]) for i, c in enumerate(cols))
    print(line(headers))
    for row in rows:
        print(line(row))
    return 0


def cmd_remove(args) -> int:
    store = _store(args)
    alarms = store.load()
    target = _find(alarms, args.id)
    if target is None:
        print(f"No alarm with id {args.id}", file=sys.stderr)
        return 1
    store.save([a for a in alarms if a.id != args.id])
    print(f"Removed alarm {args.id}")
    return 0


def _set_enabled(args, enabled: bool) -> int:
    store = _store(args)
    alarms = store.load()
    target = _find(alarms, args.id)
    if target is None:
        print(f"No alarm with id {args.id}", file=sys.stderr)
        return 1
    target.enabled = enabled
    store.save(alarms)
    print(f"{'Enabled' if enabled else 'Disabled'} alarm {args.id}")
    return 0


def cmd_run(args) -> int:
    store = _store(args)
    runner = AlarmRunner(
        store=store,
        clock=SystemClock(),
        notifier=ConsoleNotifier(play_sound=not args.no_sound),
        prompt=ConsolePrompt(default_snooze=args.snooze),
    )
    print("Watching for alarms… (Ctrl-C to stop)")
    try:
        runner.run()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


def _humanize_until(fire: datetime, now: datetime) -> str:
    secs = int((fire - now).total_seconds())
    if secs < 60:
        return "<1m"
    minutes = secs // 60
    if minutes < 60:
        return f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h{minutes:02d}m"
    days, hours = divmod(hours, 24)
    return f"{days}d{hours}h"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="alarm", description="A tiny CLI alarm clock.")
    parser.add_argument("--db", help="path to the alarms file (overrides ALARMCLOCK_DB)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="add an alarm")
    p_add.add_argument("time", help="time in HH:MM (24-hour), e.g. 07:30")
    p_add.add_argument("--label", help="a name for the alarm")
    p_add.add_argument("--repeat", default="once",
                       help="once | daily | weekdays | weekends | mon,wed,fri")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="list all alarms")
    p_list.set_defaults(func=cmd_list)

    p_remove = sub.add_parser("remove", help="remove an alarm by id")
    p_remove.add_argument("id")
    p_remove.set_defaults(func=cmd_remove)

    p_enable = sub.add_parser("enable", help="enable an alarm by id")
    p_enable.add_argument("id")
    p_enable.set_defaults(func=lambda a: _set_enabled(a, True))

    p_disable = sub.add_parser("disable", help="disable an alarm by id")
    p_disable.add_argument("id")
    p_disable.set_defaults(func=lambda a: _set_enabled(a, False))

    p_run = sub.add_parser("run", help="watch the clock and ring due alarms")
    p_run.add_argument("--snooze", type=int, default=9, help="default snooze minutes")
    p_run.add_argument("--no-sound", action="store_true", help="bell only, no system sound")
    p_run.set_defaults(func=cmd_run)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
