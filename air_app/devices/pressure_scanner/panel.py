"""Acquisition dashboard. Only the GUI thread touches Qt and Matplotlib."""
from collections import deque
import csv
import json
from pathlib import Path
import queue

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox,
    QFileDialog, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QSpinBox, QSplitter,
    QPlainTextEdit, QScrollArea, QVBoxLayout, QWidget)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from .acquisition import AcquisitionWorker
from .models import ScanSettings
from ...preferences import preferences
from ..registry import DeviceWorkspace



class PressureScannerPanel(DeviceWorkspace):
    def __init__(self, run_storage):
        super().__init__()
        self.run_storage = run_storage
        self.preferences = preferences('PressureScanner')
        self.is_connected = False
        self.busy = False
        self.pending = False
        self.current_path = None
        self.samples = deque(maxlen=5000)
        self.total = 0
        self.worker = AcquisitionWorker()
        self.worker.message.connect(self.log_message)
        self.worker.state.connect(self.on_state)
        self.worker.connected.connect(self.on_connected)
        self.worker.run_saved.connect(self.on_run_saved)
        self.build_ui()
        self.worker.start()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_plot)
        self.timer.start(100)
        self.update_controls()

    @staticmethod
    def form(group):
        form = QFormLayout(group)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.setContentsMargins(16, 22, 16, 16)
        return form

    def button(self, text, callback):
        button = QPushButton(text)
        button.clicked.connect(callback)
        return button

    def spin(self, minimum, maximum, value):
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setMinimumWidth(150)
        return spin

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        splitter = QSplitter()
        layout.addWidget(splitter, 1)
        controls = QWidget()
        left = QVBoxLayout(controls)
        self.connection_group = QGroupBox('Connection')
        form = self.form(self.connection_group)
        self.host = QLineEdit(self.preferences.value('host', '191.191.192.176'))
        self.port = self.spin(1, 65535, int(self.preferences.value('port', 23)))
        self.demo = QCheckBox('Demo • generated signals, no hardware')
        form.addRow('Scanner address', self.host)
        form.addRow('TCP port', self.port)
        form.addRow(self.demo)
        self.connect_button = self.button('Connect', self.connect_scanner)
        self.disconnect_button = self.button('Disconnect', lambda: self.submit('disconnect'))
        row = QHBoxLayout()
        row.addWidget(self.connect_button)
        row.addWidget(self.disconnect_button)
        form.addRow(row)
        left.addWidget(self.connection_group)

        self.scan_group = QGroupBox('Acquisition settings')
        form = self.form(self.scan_group)
        self.period = self.spin(125, 65535, int(self.preferences.value('period', 250)))
        self.average = self.spin(1, 240, int(self.preferences.value('average', 10)))
        self.frames = self.spin(0, 2147483647, int(self.preferences.value('frames', 0)))
        self.frames.setToolTip('0 runs continuously until Stop; a positive value sets the frame count.')
        self.units = QComboBox()
        self.units.setMinimumWidth(150)
        self.units.addItems(['PA', 'KPA', 'PSI', 'BAR'])
        self.units.setCurrentText(self.preferences.value('units', 'PA'))
        self.rate = QLabel()
        for label, field in [('Period (µs)', self.period), ('Average', self.average),
                             ('Frames', self.frames), ('Pressure units', self.units),
                             ('Nominal rate', self.rate)]:
            form.addRow(label, field)
        self.period.valueChanged.connect(self.update_rate)
        self.average.valueChanged.connect(self.update_rate)
        self.frames.valueChanged.connect(self.update_rate)
        self.update_rate()
        self.calibrate_button = self.button('Zero calibrate…', self.calibrate)
        self.status_button = self.button('Read status', lambda: self.submit('status'))
        row = QHBoxLayout()
        row.addWidget(self.calibrate_button)
        row.addWidget(self.status_button)
        form.addRow(row)
        left.addWidget(self.scan_group)

        self.name = self.run_storage.name
        self.notes = self.run_storage.notes
        self.folder = self.run_storage.folder
        self.save_group = QGroupBox('Run controls')
        form = self.form(self.save_group)
        self.start_button = self.button('▶  Start & record', self.start_scan)
        self.stop_button = self.button('■  Stop', self.worker.stop_run.set)
        row = QHBoxLayout()
        row.addWidget(self.start_button)
        row.addWidget(self.stop_button)
        form.addRow(row)
        self.saved_label = self.run_storage.saved_label
        self.open_button = self.button('Open saved pressure run…', self.open_run)
        left.addWidget(self.open_button)
        self.diagnostics_button = self.button('Read scanner diagnostics', lambda: self.submit('diagnostics'))
        left.addWidget(self.diagnostics_button)
        hint = QLabel('0 frames runs until Stop.\nWarm-up: at least 30 minutes after power-on; 1 hour recommended.')
        hint.setWordWrap(True)
        left.addWidget(hint)
        left.addStretch()
        controls.setMinimumWidth(350)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(controls)
        scroll.setMinimumWidth(380)
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.addWidget(scroll, 1)
        sidebar_layout.addWidget(self.save_group)
        splitter.addWidget(sidebar)

        plot_panel = QWidget()
        right = QVBoxLayout(plot_panel)
        self.summary = QLabel('Idle • connect to a scanner or select Demo')
        right.addWidget(self.summary)
        self.figure = Figure(layout='constrained')
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)
        right.addWidget(self.canvas, 1)
        self.lines = {}
        channels = QGridLayout()
        self.channel_checks = {}
        # Some firmware uses channel 0; retain original identifiers in plots/data.
        for ch in range(17):
            check = QCheckBox(str(ch))
            check.setChecked(ch in (1, 2, 3, 4))
            check.toggled.connect(self.redraw)
            self.channel_checks[ch] = check
            channels.addWidget(check, ch // 9, ch % 9)
            self.lines[ch], = self.ax.plot([], [], label=f'Ch {ch}', linewidth=1.3)
        right.addLayout(channels)
        row = QHBoxLayout()
        self.window_seconds = QDoubleSpinBox()
        self.window_seconds.setRange(1, 3600)
        self.window_seconds.setValue(30)
        self.window_seconds.setSuffix(' s')
        self.window_seconds.valueChanged.connect(self.redraw)
        self.pause = QCheckBox('Freeze display (recording continues)')
        self.pause.toggled.connect(lambda frozen: None if frozen else self.redraw())
        row.addWidget(QLabel('Visible history'))
        row.addWidget(self.window_seconds)
        row.addWidget(self.pause)
        right.addLayout(row)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        self.log.setMaximumHeight(150)
        right.addWidget(self.log)
        splitter.addWidget(plot_panel)
        splitter.setSizes([400, 940])
        self.redraw()

    def update_rate(self):
        rate = 1e6 / (self.period.value() * 16 * self.average.value())
        duration = f' • {self.frames.value()/rate:.1f} s' if self.frames.value() else ' • continuous'
        self.rate.setText(f'{rate:g} frames/s{duration}')

    def submit(self, operation, *args):
        self.pending = True
        self.update_controls()
        self.worker.request(operation, *args)

    def connect_scanner(self):
        if not self.demo.isChecked() and not self.host.text().strip():
            self.log_message('Enter a scanner address')
            return
        self.preferences.setValue('host', self.host.text().strip())
        self.preferences.setValue('port', self.port.value())
        self.submit('connect', self.host.text().strip(), self.port.value(), self.demo.isChecked())

    def on_connected(self, value):
        self.is_connected = value
        self.update_controls()

    def on_state(self, state):
        self.busy = state != 'Idle'
        if state == 'Idle':
            self.pending = False
            if self.current_path:
                self.saved_label.setText(f'Run folder: {self.current_path.name}')
                self.saved_label.setToolTip(str(self.current_path))
        self.summary.setText(f'{state} • {self.total} frames received')
        self.update_controls()

    def update_controls(self):
        idle = not self.busy and not self.pending
        self.connect_button.setEnabled(idle and not self.is_connected)
        self.disconnect_button.setEnabled(idle and self.is_connected)
        self.host.setEnabled(idle and not self.is_connected)
        self.port.setEnabled(idle and not self.is_connected)
        self.demo.setEnabled(idle and not self.is_connected)
        self.scan_group.setEnabled(idle)
        self.calibrate_button.setEnabled(idle and self.is_connected)
        self.status_button.setEnabled(idle and self.is_connected)
        self.start_button.setEnabled(idle and self.is_connected)
        self.stop_button.setEnabled(self.busy or self.pending)
        self.open_button.setEnabled(idle)
        self.diagnostics_button.setEnabled(idle and self.is_connected)
        self.run_storage.set_locked(not idle)

    def calibrate(self):
        if self.demo.isChecked():
            self.log_message('Demo: zero calibration simulated')
            return
        answer = QMessageBox.question(self, 'Zero calibration',
            'Equalize the measurement and reference pressures as described in the manual. '
            'Confirm the plumbing is ready for a zero-offset calibration. Continue?')
        if answer == QMessageBox.Yes:
            self.worker.stop_run.clear()
            self.submit('calibrate')

    def start_scan(self):
        if not self.folder.text().strip():
            self.log_message('Choose a save folder first')
            return
        settings = ScanSettings(self.period.value(), self.average.value(), self.frames.value(), self.units.currentText())
        for key, value in [('period', settings.period), ('average', settings.average),
                           ('frames', settings.frames), ('units', settings.units)]:
            self.preferences.setValue(key, value)
        self.samples.clear()
        self.total = 0
        while True:
            try:
                self.worker.plot_frames.get_nowait()
            except queue.Empty:
                break
        self.run_storage.save_preferences()
        self.worker.stop_run.clear()
        self.submit('scan', settings, self.folder.text(), self.name.text(), self.notes.toPlainText())
        self.redraw()

    def on_run_saved(self, path):
        self.current_path = Path(path)
        self.run_storage.current_path = self.current_path
        self.saved_label.setText(f'Recording: {self.current_path.name}')
        self.saved_label.setToolTip(path)

    def refresh_plot(self):
        changed = False
        for _ in range(2000):
            try:
                frame = self.worker.plot_frames.get_nowait()
            except queue.Empty:
                break
            self.samples.append(frame)
            self.total += 1
            changed = True
        if changed:
            self.summary.setText(f'{"Acquiring" if self.busy else "Idle"} • {self.total} display frames • '
                                 f'{len(self.samples)} in memory')
            if not self.pause.isChecked():
                self.redraw()

    def redraw(self, *_):
        if not hasattr(self, 'lines'):
            return
        end = self.samples[-1].elapsed if self.samples else 0
        start = max(0, end - self.window_seconds.value()) if hasattr(self, 'window_seconds') else 0
        visible = [frame for frame in self.samples if frame.elapsed >= start]
        for ch, line in self.lines.items():
            selected = self.channel_checks[ch].isChecked()
            line.set_visible(selected)
            points = [(f.elapsed, f.channels[ch][0] if f.channels[ch][2] else float('nan'))
                      for f in visible if ch in f.channels] if selected else []
            line.set_data([p[0] for p in points], [p[1] for p in points])
        self.ax.set_xlabel('Elapsed time (s) • host receive time for hardware')
        self.ax.set_ylabel(f'Pressure ({self.units.currentText()})')
        self.ax.set_title('Channel pressure • latest 5,000 display frames')
        self.ax.grid(True, alpha=0.2)
        self.ax.relim(visible_only=True)
        self.ax.autoscale_view()
        self.ax.set_xlim(start, max(start + 1, end))
        handles = [line for line in self.lines.values() if line.get_visible()]
        if handles:
            self.ax.legend(handles=handles, loc='upper right', ncol=4, fontsize=8)
        elif self.ax.get_legend():
            self.ax.get_legend().remove()
        self.canvas.draw_idle()

    def log_message(self, message):
        self.log.appendPlainText(message)

    def open_run(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Open run samples', self.folder.text(), 'Run CSV (samples.csv)')
        if not path:
            return
        try:
            from .models import Frame
            metadata = json.loads(Path(path).with_name('metadata.json').read_text())
            samples = deque(maxlen=5000)
            frame = None
            with open(path, newline='', encoding='utf-8') as stream:
                for row in csv.DictReader(stream):
                    number = int(row['frame'])
                    if frame is None or number != frame.number:
                        if frame is not None:
                            samples.append(frame)
                        frame = Frame(number, float(row['elapsed_s']), {})
                    frame.channels[int(row['channel'])] = (float(row['pressure']), None, row['valid'] == '1')
                if frame is not None:
                    samples.append(frame)
            self.samples = samples
            self.units.setCurrentText(metadata['settings']['units'])
            self.current_path = Path(path).parent
            self.run_storage.current_path = self.current_path
            self.saved_label.setText(f'Run folder: {self.current_path.name}')
            self.saved_label.setToolTip(str(self.current_path))
            self.summary.setText(f'Saved run: {metadata["name"]} • {metadata["state"]} • {metadata["frames"]} frames')
            self.redraw()
        except (OSError, ValueError, KeyError) as error:
            self.log_message(f'Could not open run: {error}')

    def request_shutdown(self):
        self.worker.stop_run.set()
        self.worker.shutdown.set()
        self.setEnabled(False)

    def shutdown_complete(self):
        return not self.worker.isRunning()
