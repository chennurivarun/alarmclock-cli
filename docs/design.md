# Design — `alarmclock` CLI

A command-line alarm clock in Python. CLI only; no web UI, no database.

This document is the spec I agreed on with my AI pair before writing code. It exists
so the *reasoning* is reviewable, not just the result.

## 1. Problem framing

The brief is deliberately open: "build an alarm clock as a Python CLI." For a 30-minute,
senior-level exercise the scoring is about engineering judgment, not feature count. So the
goal is a **small, well-bounded, fully-tested core** with an honest CLI surface — not a
sprawling feature list with shallow tests.

Two decisions framed everything else:

1. **Scope** → a tight core: multiple named alarms, one-time + recurring, snooze,
   JSON persistence, a blocking `run` command that rings. No timezones, no daemon.
2. **How does an alarm fire?** → a **foreground `run` loop**, not a background daemon.
   A daemon adds process management, IPC, and platform fragility that can't be done well
   or tested honestly in the time box. A blocking loop is simple, portable, and — crucially —
   testable by injecting a fake clock.

## 2. Guiding principle

**Separate the pure "when should this fire?" logic from all I/O** (the real clock, sound,
and disk). That single seam is what makes the core trivially unit-testable: tests never
sleep, never make noise, and never touch the real filesystem clock.

## 3. Architecture

Layered, with dependencies injected at the edges:

| Module          | Responsibility                                              | Depends on        |
|-----------------|-------------------------------------------------------------|-------------------|
| `models.py`     | `Alarm` dataclass, `--repeat` parsing, (de)serialization    | stdlib only       |
| `scheduling.py` | `next_fire_at(alarm, now)` + due-detection — **pure**       | `models`          |
| `clock.py`      | `Clock` protocol → `SystemClock` / `FakeClock`              | stdlib only       |
| `notifier.py`   | `Notifier` protocol → `ConsoleNotifier` / `FakeNotifier`    | `models`          |
| `storage.py`    | JSON repository, atomic write (tmp file + `os.replace`)     | `models`          |
| `runner.py`     | the `run` loop: poll clock, fire due alarms, snooze prompt  | all of the above  |
| `cli.py`        | argparse subcommands → dispatch (thin I/O shell)            | all of the above  |

**Zero runtime dependencies** — stdlib only (`argparse`, `json`, `dataclasses`, `datetime`,
`os`). `pytest` is the only *dev* dependency.

## 4. Domain model

```
Alarm:
  id:          str            # short, stable handle for remove/enable/disable
  label:       str            # human name, optional
  time:        datetime.time  # HH:MM, second precision not needed
  repeat_days: frozenset[int] # weekdays 0=Mon..6=Sun; EMPTY = one-time
  enabled:     bool
```

Modeling a one-time alarm as "empty repeat set" gives a **single code path** and avoids
storing/validating calendar dates.

`next_fire_at(alarm, now) -> datetime | None` — the heart of the system, a pure function:

- Disabled → `None`.
- One-time (`repeat_days` empty) → the next occurrence of `time`: today if still ahead,
  otherwise tomorrow. After it fires it auto-disables (so it never repeats).
- Recurring → the soonest future datetime whose weekday ∈ `repeat_days` and whose clock
  time equals `alarm.time`.

## 5. CLI surface

```
alarm add 07:30 --label "Standup" --repeat weekdays
alarm list
alarm remove  <id>
alarm enable  <id>
alarm disable <id>
alarm run [--snooze 9]      # blocking; rings due alarms, prompts [d]ismiss / [s]nooze
```

`--repeat` accepts: `once` (default) | `daily` | `weekdays` | `weekends` | a comma list
like `mon,wed,fri`.

`run` prints a live countdown to the next alarm and rings when due.

## 6. Behaviour decisions

- **Snooze** is in-memory runtime state inside the runner, not persisted. A snooze means
  "ring again in N minutes"; if you quit, it's gone. This keeps the stored model clean.
- **Storage** lives at `~/.alarmclock/alarms.json` (override via `--db` or `ALARMCLOCK_DB`).
  Writes are **atomic** (write temp, `os.replace`) so a crash can't corrupt the store.
- **Sound** is best-effort and pluggable via `Notifier`: always emit the terminal bell
  `\a`; additionally play a system sound via `afplay` on macOS when available; degrade
  silently elsewhere. Tests use `FakeNotifier` and assert on calls, never make sound.

## 7. Testing plan

Pure core + injected fakes = fast, deterministic tests. No test sleeps or makes noise.

- `next_fire_at` across boundaries: one-time today vs tomorrow, daily, weekdays crossing a
  weekend, disabled returns `None`.
- Due-detection driven by a `FakeClock`: an alarm becomes due exactly when now ≥ next fire.
- Repository: JSON round-trip (serialize → deserialize is identity), atomic write leaves no
  partial file, missing file → empty list.
- `--repeat` parsing: every alias + comma lists + invalid input rejected.
- Snooze: a fired alarm re-fires after N minutes via the fake clock.

## 8. Deliverables

GitHub repo containing the package, the test suite, this design doc, and a `README.md`
covering decisions, usage, and how to run. Commit history is sequenced to tell the build
story for the screen recording.

## 9. Explicitly out of scope (YAGNI)

Timezones, background daemon, multiple alarm sounds/config profiles, persistence of snooze
state, sub-minute precision. Each is a reasonable v2; none earns its complexity in a 30-min
core focused on judgment and correctness.
