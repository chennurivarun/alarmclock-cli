# ⏰ alarmclock

A small, dependency-free **command-line alarm clock** in Python.

Set named one-time and recurring alarms, then run a foreground watcher that rings
them — bell, banner, and (on macOS) a system sound — with snooze and dismiss.

```console
$ alarm add 07:30 --label Standup --repeat weekdays
Added alarm 1: 07:30 (weekdays) — Standup

$ alarm add 22:00 --label "Wind down" --repeat daily
Added alarm 2: 22:00 (daily) — Wind down

$ alarm list
ID  TIME   REPEAT    STATUS  NEXT    LABEL
1   07:30  weekdays  on      2d20h   Standup
2   22:00  daily     on      11h26m  Wind down

$ alarm run
Watching for alarms… (Ctrl-C to stop)
⏳ next 22:00 Wind down in 11:26:03
```

When an alarm comes due:

```
⏰  22:00  Wind down
  [d]ismiss / [s]nooze / [q]uit? s
  snoozed 9 min.
```

---

## Why it's built this way

This was a time-boxed exercise; the goal was a **small, correct, well-tested core**
rather than a long feature list. Two decisions shaped everything (full reasoning in
[`docs/design.md`](docs/design.md)):

1. **A foreground `run` loop, not a background daemon.** A daemon would mean process
   management, IPC, and platform-specific fragility that can't be done well or tested
   honestly in the time available. A blocking loop is simple, portable, and testable.

2. **The pure "when should this fire?" logic is isolated from all I/O** — the clock,
   sound, and disk are injected at the edges. That single seam is why the test suite
   runs in milliseconds and never sleeps, makes noise, or touches real time.

## Requirements

- Python **3.8+**
- **No runtime dependencies** — standard library only.
- `pytest` only if you want to run the test suite.

## Install

Clone and run as a module — no install needed:

```console
$ python -m alarmclock --help
```

Or install it to get the `alarm` command on your PATH:

```console
$ pip install -e .
$ alarm --help
```

## Usage

```
alarm add <HH:MM> [--label NAME] [--repeat SPEC]   add an alarm
alarm list                                         show all alarms + next fire time
alarm remove  <id>                                 delete an alarm
alarm enable  <id>                                 turn an alarm on
alarm disable <id>                                 turn an alarm off (keep it)
alarm run [--snooze N] [--no-sound]                watch the clock and ring due alarms
```

- `--repeat` accepts: `once` (default) · `daily` · `weekdays` · `weekends` · or a
  comma list like `mon,wed,fri`.
- One-time alarms (`once`) automatically disable themselves after they ring.
- `--snooze N` sets how many minutes the **s** reply snoozes for (default 9). You can
  also type a number at the prompt to snooze that many minutes.
- Alarms are stored as JSON at `~/.alarmclock/alarms.json`. Override the location with
  `--db <path>` or the `ALARMCLOCK_DB` environment variable.

## How it works

Layered, with the fragile parts injected so the core stays pure and testable:

| Module          | Responsibility                                            |
|-----------------|-----------------------------------------------------------|
| `models.py`     | `Alarm` dataclass, `--repeat` parsing, (de)serialization  |
| `scheduling.py` | `next_fire_at(alarm, now)` + due ordering — **pure**      |
| `clock.py`      | `Clock` protocol → `SystemClock` / `FakeClock`            |
| `notifier.py`   | `Notifier` protocol → `ConsoleNotifier` / `FakeNotifier`  |
| `storage.py`    | JSON repository with **atomic** writes (temp + `replace`) |
| `runner.py`     | the `run` loop: wait → ring → dismiss/snooze              |
| `cli.py`        | argparse subcommands → dispatch (thin I/O shell)          |

One-time alarms are modeled as an **empty repeat set**, which keeps one-shot and
recurring alarms on a single code path everywhere downstream.

## Testing

```console
$ pip install pytest      # or:  pip install -e ".[dev]"
$ python -m pytest
```

The suite covers the scheduling boundaries (one-time today vs tomorrow, daily,
weekdays crossing a weekend, disabled), JSON round-tripping and atomic writes, repeat
parsing, and the full `run` loop end to end (snooze, dismiss, quit, no-alarms) — all
driven by a `FakeClock` and `FakeNotifier`, so nothing sleeps or makes a sound.

## Deliberately out of scope

Timezones, a background daemon, multiple alarm sounds, and persisted snooze state are
all reasonable next steps but were cut to keep the core sharp. See
[`docs/design.md`](docs/design.md) §9.

## On AI assistance

Per the exercise, this was built with an AI pair. The workflow was: refine
requirements and pick the two framing decisions → write and commit a design spec →
implement bottom-up (pure core first) → validate, where the validation step actually
caught a bug in the test harness before the result was trusted. The commit history
follows that sequence.
