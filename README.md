# AIR — Wind tunnel workstation

Python 3.14 / PyQt5 desktop application with shared run storage and instrument workspaces.
The currently implemented instrument is the Scanivalve DSA3217 pressure scanner.
Configure and zero-calibrate the scanner, record finite or continuous tests,
and inspect individual pressure channels while data arrives.

## Start

```sh
uv venv --python 3.14
uv pip install -r requirements.txt
.venv/bin/python -m air_app
```

`Frontend.py` remains a compatibility launcher. No pickle or intermediate file
is required for live plotting. Acquisition uses Telnet over TCP (default port 23)
through `telnetlib3`; the GUI and plots remain on the main thread.

## Run a test

1. Enter the scanner IP and port, or select **Demo** to use local generated signals.
2. Connect. The hardware must report `STATUS: READY`.
3. Set period, averaging, units, and frame count. **0 frames means continuous**;
   a positive count records a finite run. Nominal rate is
   `1_000_000 / (period_us * 16 * average)` frames/s.
4. For hardware zero calibration, first equalize measurement/reference pressures
   following the manual, then select **Zero calibrate**. Completion requires READY.
5. Set a run name, optional notes, and output folder, then **Start & record**.
6. Select plot channels and history length. Freeze display pauses only the plot.
   **Stop** ends acquisition. Closing the app requests STOP and closes files before exit.

Settings are applied before each run using the scanner's variable names and limits.
Hardware acquisition explicitly selects sensor input (`SIM=0`), ASCII scrolling
output (`BIN=0`, `FORMAT=0`), engineering units, microsecond timestamps, and internal
triggering. `QPKTS=1` requests that the scanner stop with an error rather than silently
discard frames if its buffer fills. These settings affect the scanner's active
configuration; the application does not issue SAVE to change power-on defaults.
External triggering, binary output, and derived velocity calculations are not exposed.

## Saved data

Default: `runs/` inside this repository (resolved from the source location, independent
of the working directory). Git ignores this directory. Choose another folder in the
app; preferences persist. **Use default** restores the repo-local location. The former
pressure-scanner folder preference is not reused; the shared application now owns it.
Every run gets a unique folder such as
`2026-11-09_20-30-00_wing-A_10-deg_a1b2c3`:

- `samples.csv`: one row per channel per frame, with frame ID, host elapsed time,
  original device timestamp and units, pressure, temperature, and validity flag.
- `metadata.json`: name, notes, UTC dates, settings, connection, demo flag, frame
  count, final state, errors, observed frame gaps, and display frames skipped.
- `raw.txt`: incoming ASCII scan stream (empty for generated demo signals).

CSV/raw files and metadata are flushed about once per second; metadata is replaced
atomically. Interrupted processes may leave metadata in `recording` state; retained
CSV/raw data remains available. This is not a guarantee against power-loss data loss.
No automatic overwrite or deletion is performed.

**Open saved run** loads the latest 5,000 frames from a run's `samples.csv` and sibling
metadata, without connecting to hardware. **Show run folder** opens the current run.

The plot uses host receive elapsed time for hardware; device timestamps are retained
in CSV without assuming their rollover behavior. Multiple frames received in the same
network read share host elapsed time. Invalid/nonfinite values and the scanner's
±999999 error sentinels are retained with `valid=0` and shown as plot gaps.

All complete parsed frames go to disk. Display history is limited to 5,000 frames,
with a 2,000-frame transfer queue; a slow GUI can skip display frames, reported in
metadata. Stop ends recording at the current read boundary; trailing frames still
in transit when STOP is issued are not guaranteed to be included. Partial frames
are never written as complete samples.

## Repository map

```text
air_app/
  ui.py                    Application shell and instrument navigation
  run_storage.py           Shared run name, multiline notes, folder preferences
  storage.py               Device-independent run directory creation
  preferences.py           Application and device preference namespaces
  devices/
    registry.py            Implemented-device registration and lifecycle contract
    pressure_scanner/
      panel.py             Scanner controls, plotting, saved pressure-run viewing
      acquisition.py       Scanner worker and calibration/scan lifecycle
      protocol.py          Incremental DSA ASCII parser
      models.py            Scanner settings and pressure frame model
      storage.py           Pressure CSV schema and scanner metadata
resources/
  manuals/          Original datasheet, quickstart, and manual PDFs
  examples/         Original sample pickle and CSV
  legacy/           Original UI/backend source, reference only
  README.md         Reference index and manual sections
tests/              Protocol, storage, and worker tests
Frontend.py         Compatibility launcher
```

Manuals remain in `resources/manuals/`; there are no in-app reference-opening controls. Original source is
retained under `resources/legacy` for comparison, including its known incomplete
configuration UI; it is not imported by the application.

## Extending the application

The shell provides shared run identity/storage controls and hosts registered device
workspaces as tabs. Only the pressure scanner is registered; no tunnel-speed or
force-sensor controls are implemented.

To add a real instrument later:

1. Add a device package under `air_app/devices/` containing its own settings,
   transport/worker, data model, and file schema.
2. Implement a `DeviceWorkspace` with `request_shutdown()` and
   `shutdown_complete()`; keep hardware I/O off the GUI thread. The shell waits
   for every workspace to close its connections/files before exiting.
3. Register its factory and title in `available_devices()`. The factory receives
   the shared `RunStoragePanel` for run name, notes, and folder selection.
4. Use `create_run_directory()` for unique run directories; instrument-specific
   data writers remain within their device package. Include an instrument ID
   in metadata, as the pressure writer does.

This is a foundation for separate instruments, not synchronized multi-instrument
acquisition. A shared experiment/session coordinator can be added when the timing
and control requirements for the next devices are known.

## Scanner diagnostics

**Read scanner diagnostics** reads identification (`LIST I`), active settings
(`LIST S`), and the last errors (`ERROR`) into the activity log while idle.
It never issues `CLEAR` or changes identification variables. The last diagnostic
snapshot is included in subsequent run metadata with its read time; it is a
historical snapshot, not a claim that those settings are still current.

The manual specifies at least 30 minutes of warm-up after power-on and recommends
one hour. This is stated in the scanner workspace; connection time is not treated
as power-on time. Error sentinels and buffer handling are already implemented.

## Validation

```sh
.venv/bin/python -B -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen .venv/bin/python -B tests/gui_smoke.py
uv pip check --python .venv/bin/python
```

Tests exercise arbitrary TCP chunk boundaries, final-frame handling, error values,
settings validation, storage round trips, simulated hardware commands, and finite/
continuous demo acquisition. Demo tests do not validate physical scanner behavior.
The parser expects 16 channel records per frame, matching this scanner. Channel
identifiers are preserved (0–16 accepted to accommodate firmware numbering);
incomplete frames are excluded, and malformed samples fail the run visibly.

Before relying on hardware results, verify connection/READY, zero calibration,
a short finite run with correct units/counts, and continuous acquisition followed
by STOP on the actual scanner. Check raw output against the CSV and device timestamps.

## Useful next additions

- Test presets and searchable run history with tags.
- Device-time plotting after verifying timestamp units and rollover on the scanner.
- Pressure statistics and baseline subtraction over a selected interval.
- Explicit reference-channel selection and air-density input for derived velocity.
- Multiple-scanner synchronization, once single-scanner hardware acceptance passes.
