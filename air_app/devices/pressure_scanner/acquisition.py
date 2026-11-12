"""One worker owns the connection and files; UI requests arrive through a queue."""
import math
import queue
import threading
import time
from PyQt5.QtCore import QThread, pyqtSignal
from telnetlib3 import telnetlib
from .models import Frame
from .protocol import StreamParser
from .storage import RunWriter


class AcquisitionWorker(QThread):
    message = pyqtSignal(str)
    state = pyqtSignal(str)
    connected = pyqtSignal(bool)
    run_saved = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.requests = queue.Queue()
        self.plot_frames = queue.Queue(maxsize=2000)
        self.stop_run = threading.Event()
        self.shutdown = threading.Event()
        self.tn = None
        self.demo = False
        self.host = ''
        self.diagnostics = {}

    def request(self, operation, *args):
        self.requests.put((operation, args))

    def command(self, text, wait=0.25):
        if self.demo:
            return {'STATUS': 'STATUS: READY', 'LIST I': 'Demo scanner (local generated data)', 'LIST S': 'Demo settings are applied locally', 'ERROR': 'ERROR: No errors'}.get(text, '')
        if self.tn is None:
            raise ConnectionError('Connect to a scanner first')
        self.tn.write((text + '\r\n').encode('ascii'))
        response = b''
        deadline = time.monotonic() + wait
        while time.monotonic() < deadline:
            response += self.tn.read_very_eager()
            time.sleep(0.01)
        result = response.decode('ascii', errors='replace').strip()
        if text != 'ERROR' and 'ERROR' in result.upper():
            raise RuntimeError(f'{text}: {result}')
        return result

    def ready(self, timeout=5, cancellable=False):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if cancellable and (self.stop_run.is_set() or self.shutdown.is_set()):
                self.command('STOP', wait=0.5)
                raise RuntimeError('Calibration cancelled')
            if 'READY' in self.command('STATUS', wait=0.5).upper():
                return
            if self.shutdown.is_set():
                raise RuntimeError('Shutdown requested')
        raise TimeoutError('Scanner did not report READY')

    def disconnect(self):
        if self.tn is not None:
            self.tn.close()
            self.tn = None
        self.demo = False
        self.connected.emit(False)

    def run(self):
        try:
            while not self.shutdown.is_set():
                try:
                    operation, args = self.requests.get(timeout=0.1)
                except queue.Empty:
                    continue
                try:
                    if operation == 'connect':
                        self.disconnect()
                        self.diagnostics = {}
                        self.host, port, self.demo = args
                        if not self.demo:
                            self.tn = telnetlib.Telnet(self.host, port, timeout=5)
                        self.ready()
                        self.connected.emit(True)
                        self.message.emit('Demo connected' if self.demo else f'Connected to {self.host}:{port}')
                    elif operation == 'disconnect':
                        self.disconnect()
                    elif operation == 'calibrate':
                        self.state.emit('Calibrating')
                        self.ready()
                        self.command('CALZ')
                        time.sleep(0.5)
                        self.ready(timeout=60, cancellable=True)
                        self.message.emit('Zero calibration complete: scanner reports READY')
                    elif operation == 'diagnostics':
                        self.ready()
                        snapshot = {}
                        for command in ('LIST I', 'LIST S', 'ERROR'):
                            snapshot[command] = self.command(command, wait=1)
                            self.message.emit(f'{command}:\n{snapshot[command] or "(no response)"}')
                        from datetime import datetime, timezone
                        self.diagnostics = {'read_at': datetime.now(timezone.utc).isoformat(),
                                            'responses': snapshot}
                    elif operation == 'status':
                        self.message.emit(self.command('STATUS', wait=1))
                    elif operation == 'scan':
                        self.acquire(*args)
                except Exception as error:
                    self.message.emit(f'ERROR: {error}')
                    self.disconnect()
                finally:
                    self.state.emit('Idle')
        finally:
            self.disconnect()

    def acquire(self, settings, root, name, notes):
        self.state.emit('Preparing')
        self.ready()
        for variable, value in settings.commands():
            if self.shutdown.is_set() or self.stop_run.is_set():
                return
            self.command(f'SET {variable} {value}')
        writer = RunWriter(root, name, notes, settings, self.host, self.demo)
        writer.metadata['last_diagnostics'] = self.diagnostics
        parser = StreamParser()
        state, error = 'completed', None
        count, dropped, gaps, last_number = 0, 0, 0, None
        started = time.monotonic()
        last_data = last_flush = started
        scan_started = False
        try:
            if not self.demo:
                self.tn.write(b'SCAN\r\n')
            scan_started = True
            self.state.emit('Running')
            self.run_saved.emit(str(writer.path))
            while not self.stop_run.is_set() and not self.shutdown.is_set():
                now = time.monotonic()
                frames = []
                if self.demo:
                    due = int((now - started) * settings.rate)
                    if count < due:
                        elapsed = count / settings.rate
                        channels = {ch: (100 * math.sin(elapsed * 2 + ch / 4) + ch * 10, 22., True)
                                    for ch in range(1, 17)}
                        frames = [Frame(count + 1, elapsed, channels, elapsed * 1e6, 'us')]
                else:
                    raw = self.tn.read_very_eager().decode('ascii', errors='replace')
                    if raw:
                        writer.raw.write(raw)
                        frames = parser.feed(raw, now - started)
                    if parser.errors:
                        raise RuntimeError('; '.join(parser.errors[:3]))
                for frame in frames:
                    if last_number is not None and frame.number != last_number + 1:
                        gaps += max(1, frame.number - last_number - 1)
                    last_number = frame.number
                    writer.write(frame)
                    count += 1
                    last_data = now
                    try:
                        self.plot_frames.put_nowait(frame)
                    except queue.Full:
                        dropped += 1  # Only display frames; every frame is still stored.
                if now - last_flush >= 1:
                    writer.flush()
                    last_flush = now
                if settings.frames and count >= settings.frames:
                    break
                if not self.demo and now - last_data > max(10, 5 / settings.rate):
                    raise TimeoutError('No complete scanner frame received within the expected interval')
                time.sleep(0.002)
            if self.stop_run.is_set() or self.shutdown.is_set():
                state = 'stopped'
        except Exception as exc:
            state, error = 'failed', str(exc)
            raise
        finally:
            try:
                if scan_started and not self.demo:
                    # Stop even on finite completion/error; never leave an unattended stream.
                    self.command('STOP', wait=0.5)
                    if not self.shutdown.is_set():
                        self.ready()
            except Exception as exc:
                state, error = 'failed', f'{error or ""} STOP/READY failed: {exc}'
                self.disconnect()
                self.message.emit(error)
            finally:
                writer.finish(state, error, display_frames_skipped=dropped,
                              frame_gaps=gaps, incomplete_frames=parser.incomplete)
                self.message.emit(f'Run {state}: {count} frames; {gaps} frame gaps; saved to {writer.path}')
