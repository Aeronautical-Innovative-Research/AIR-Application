import csv
import json
import queue
from pathlib import Path
import tempfile
import time
import unittest

from air_app.devices.pressure_scanner.acquisition import AcquisitionWorker
from air_app.devices.pressure_scanner.models import ScanSettings
from air_app.devices.pressure_scanner.protocol import StreamParser
from air_app.devices.pressure_scanner.storage import RunWriter


def wire_frame(number, base=1):
    return f'Frame # {number}\r\nTime 1000 us\r\n' + ''.join(
        f'{ch} {ch * 1.25} 22.5\r\n' for ch in range(base, base + 16))


class ProtocolTests(unittest.TestCase):
    def test_every_byte_boundary_and_final_frame(self):
        wire = wire_frame(1) + wire_frame(2)
        for split in range(len(wire) + 1):
            parser = StreamParser()
            frames = parser.feed(wire[:split], 0) + parser.feed(wire[split:], 1)
            self.assertEqual([f.number for f in frames], [1, 2])
            self.assertEqual(frames[0].channels[16], (20., 22.5, True))
            self.assertEqual(frames[0].device_time, 1000)
            self.assertEqual(parser.errors, [])

    def test_invalid_and_partial_frames(self):
        parser = StreamParser()
        text = wire_frame(1).replace('1 1.25', '1 999999')
        frames = parser.feed(text, 0)
        self.assertFalse(frames[0].channels[1][2])
        parser.feed('Frame # 2\n1 1 20\nFrame # 3\nERROR: buffer full\n', 1)
        self.assertEqual(parser.incomplete, 1)
        self.assertIn('ERROR: buffer full', parser.errors)

    def test_zero_based_channels(self):
        frames = StreamParser().feed(wire_frame(1, base=0), 0)
        self.assertEqual(set(frames[0].channels), set(range(16)))

    def test_settings_ranges_and_commands(self):
        settings = ScanSettings()
        self.assertEqual(settings.rate, 25)
        self.assertIn(('FPS', 0), settings.commands())
        self.assertIn(('SIM', 0), settings.commands())
        for args in [dict(period=124), dict(average=241), dict(frames=-1), dict(units='bad')]:
            with self.assertRaises(ValueError):
                ScanSettings(**args)


class StorageTests(unittest.TestCase):
    def test_unique_runs_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as root:
            one = RunWriter(root, '../test / name', 'notes', ScanSettings(), 'scanner', False)
            two = RunWriter(root, '../test / name', '', ScanSettings(), 'scanner', True)
            frame = StreamParser().feed(wire_frame(1), .5)[0]
            one.write(frame)
            one.finish('stopped')
            two.finish('completed')
            self.assertNotEqual(one.path, two.path)
            self.assertEqual(one.path.parent, Path(root))
            metadata = json.loads((one.path / 'metadata.json').read_text())
            self.assertEqual(metadata['frames'], 1)
            self.assertEqual(metadata['state'], 'stopped')
            with (one.path / 'samples.csv').open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 16)
            self.assertEqual(rows[-1]['pressure'], '20.0')


class WorkerTests(unittest.TestCase):
    def test_failed_stream_still_stops_and_finalizes(self):
        class FailedStream:
            def __init__(self):
                self.commands = []
                self.pending = b''
            def write(self, value):
                command = value.decode().strip()
                self.commands.append(command)
                if command == 'STATUS':
                    self.pending += b'STATUS: READY\r\n'
                elif command == 'SCAN':
                    self.pending += b'ERROR: buffer full\r\n'
            def read_very_eager(self):
                result, self.pending = self.pending, b''
                return result
        with tempfile.TemporaryDirectory() as root:
            worker = AcquisitionWorker()
            worker.tn = FailedStream()
            with self.assertRaisesRegex(RuntimeError, 'buffer full'):
                worker.acquire(ScanSettings(), root, 'failure', '')
            self.assertIn('STOP', worker.tn.commands)
            metadata_path, = Path(root).glob('*/metadata.json')
            self.assertEqual(json.loads(metadata_path.read_text())['state'], 'failed')

    def test_finite_demo_saves_every_channel(self):
        with tempfile.TemporaryDirectory() as root:
            worker = AcquisitionWorker()
            worker.demo = True
            worker.host = 'demo'
            worker.acquire(ScanSettings(period=125, average=1, frames=5), root, 'demo', '')
            metadata_path, = Path(root).glob('*/metadata.json')
            metadata = json.loads(metadata_path.read_text())
            self.assertEqual(metadata['frames'], 5)
            self.assertEqual(metadata['state'], 'completed')
            self.assertEqual(worker.plot_frames.qsize(), 5)

    def test_fragmented_hardware_stream_and_stop_command(self):
        class FakeTelnet:
            def __init__(self):
                self.pending = b''
                self.commands = []
            def write(self, value):
                command = value.decode().strip()
                self.commands.append(command)
                if command == 'STATUS':
                    self.pending += b'STATUS: READY\r\n'
                if command == 'SCAN':
                    self.pending += (wire_frame(1) + wire_frame(2)).encode()
            def read_very_eager(self):
                result, self.pending = self.pending[:17], self.pending[17:]
                return result
        with tempfile.TemporaryDirectory() as root:
            worker = AcquisitionWorker()
            worker.tn = FakeTelnet()
            worker.acquire(ScanSettings(frames=2), root, 'fake', '')
            self.assertIn('STOP', worker.tn.commands)
            metadata_path, = Path(root).glob('*/metadata.json')
            self.assertEqual(json.loads(metadata_path.read_text())['frames'], 2)

    def test_continuous_stop(self):
        import threading
        with tempfile.TemporaryDirectory() as root:
            worker = AcquisitionWorker()
            worker.demo = True
            timer = threading.Timer(.08, worker.stop_run.set)
            timer.start()
            worker.acquire(ScanSettings(period=125, average=1), root, 'continuous', '')
            timer.join()
            metadata_path, = Path(root).glob('*/metadata.json')
            metadata = json.loads(metadata_path.read_text())
            self.assertEqual(metadata['state'], 'stopped')
            self.assertGreater(metadata['frames'], 0)


if __name__ == '__main__':
    unittest.main()
