"""Incremental DSA FORMAT=0 parser; TCP chunks need not align to lines."""
import math
import re
from .models import Frame


class StreamParser:
    def __init__(self):
        self.buffer = ''
        self.number = None
        self.channels = {}
        self.device_time = None
        self.time_units = None
        self.errors = []
        self.incomplete = 0

    def feed(self, text, elapsed):
        self.buffer += text
        frames = []
        while re.search(r'[\r\n]', self.buffer):
            line, self.buffer = re.split(r'[\r\n]', self.buffer, maxsplit=1)
            line = line.strip()
            if not line:
                continue
            if 'ERROR' in line.upper():
                self.errors.append(line)
                continue
            header = re.match(r'^Frame\s+#\s*(\d+)', line, re.I)
            if header:
                if self.number is not None and self.channels:
                    self.incomplete += 1
                self.number = int(header[1])
                self.channels = {}
                self.device_time = None
                self.time_units = None
                continue
            if line.lower().startswith('time '):
                fields = line.split()
                try:
                    self.device_time = float(fields[1])
                    self.time_units = fields[2] if len(fields) > 2 else None
                except (ValueError, IndexError):
                    self.errors.append('Malformed timestamp: ' + line)
                continue
            fields = line.split()
            if self.number is not None and len(fields) >= 2:
                try:
                    channel, pressure = int(fields[0]), float(fields[1])
                    temperature = float(fields[2]) if len(fields) > 2 else None
                except ValueError:
                    self.errors.append('Malformed sample: ' + line)
                    continue
                if not 0 <= channel <= 16:
                    self.errors.append('Invalid channel: ' + line)
                    continue
                if channel in self.channels:
                    self.errors.append('Duplicate channel: ' + line)
                    continue
                valid = math.isfinite(pressure) and abs(pressure) != 999999
                self.channels[channel] = (pressure, temperature, valid)
                if len(self.channels) == 16:
                    frames.append(Frame(self.number, elapsed, self.channels,
                                        self.device_time, self.time_units))
                    self.number = None
                    self.channels = {}
        if len(self.buffer) > 65536:
            raise ValueError('Scanner sent an oversized line without a terminator')
        return frames
