"""Pressure-specific CSV schema and run metadata writer."""
import csv
from datetime import datetime, timezone
import json
from ...storage import create_run_directory


class RunWriter:
    def __init__(self, root, name, notes, settings, host, demo):
        self.path = create_run_directory(root, name)
        self.metadata = dict(name=name.strip() or 'Run', notes=notes,
                             started_at=datetime.now(timezone.utc).isoformat(),
                             settings=settings.to_dict(), host=host, demo=demo,
                             state='recording', frames=0, schema_version=1, device='pressure_scanner')
        self.csv = None
        self.raw = None
        try:
            self._metadata()
            self.csv = (self.path / 'samples.csv').open('w', newline='', encoding='utf-8')
            self.raw = (self.path / 'raw.txt').open('w', encoding='utf-8')
            self.writer = csv.writer(self.csv)
            self.writer.writerow(['frame', 'elapsed_s', 'device_time', 'device_time_units',
                                  'channel', 'pressure', 'temperature_c', 'valid'])
        except BaseException:
            if self.csv:
                self.csv.close()
            if self.raw:
                self.raw.close()
            raise

    def _metadata(self):
        temporary = self.path / 'metadata.tmp'
        temporary.write_text(json.dumps(self.metadata, indent=2), encoding='utf-8')
        temporary.replace(self.path / 'metadata.json')

    def write(self, frame):
        for channel, (pressure, temperature, valid) in sorted(frame.channels.items()):
            self.writer.writerow([frame.number, frame.elapsed, frame.device_time,
                                  frame.device_time_units, channel, pressure,
                                  temperature, int(valid)])
        self.metadata['frames'] += 1

    def flush(self):
        self.csv.flush()
        self.raw.flush()
        self._metadata()

    def finish(self, state, error=None, **extra):
        self.metadata.update(state=state, error=error, ended_at=datetime.now(timezone.utc).isoformat(), **extra)
        try:
            self.flush()
        finally:
            self.csv.close()
            self.raw.close()
