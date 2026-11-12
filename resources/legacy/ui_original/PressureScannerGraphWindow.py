from pathlib import Path
import pickle
import csv

import pandas as pd
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class PressureScannerGraphWindow(QWidget):
    def __init__(self, parent=None):
        window_flags = (
            Qt.Window
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
        )
        super().__init__(parent, window_flags)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self.data_path = Path("data.pkl")
        self.last_loaded_signature = None
        self.x_values = []
        self.y_values = []

        self.setWindowTitle("Pressure Graph")
        self.resize(800, 600)

        layout = QVBoxLayout(self)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.save_button = QPushButton("Save graph data as CSV")
        self.save_button.clicked.connect(self.save_csv)
        layout.addWidget(self.save_button)

        self.status_label = QLabel(f"Waiting for {self.data_path}...")
        layout.addWidget(self.status_label)

        self.ax = self.figure.add_subplot(111)
        self.line, = self.ax.plot([], [], marker="o")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Measurement")
        self.ax.set_title("Live Sensor Data")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_for_data)
        self.timer.start(2000)  # Check every 2 seconds

        self.check_for_data()  # Also check immediately

    def place_beside_parent(self):
        """Place the graph next to the main window, within the current screen."""
        parent = self.parentWidget()
        if parent is None:
            return

        screen = QApplication.screenAt(parent.frameGeometry().center())
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return

        area = screen.availableGeometry()
        parent_rect = parent.frameGeometry()
        width = self.width()
        height = self.height()
        gap = 12

        if parent_rect.right() + gap + width <= area.right():
            x = parent_rect.right() + gap
            y = parent_rect.top()
        elif parent_rect.left() - gap - width >= area.left():
            x = parent_rect.left() - gap - width
            y = parent_rect.top()
        else:
            x = area.left() + (area.width() - width) // 2
            y = parent_rect.bottom() + gap

        x = max(area.left(), min(x, area.right() - width + 1))
        y = max(area.top(), min(y, area.bottom() - height + 1))
        self.move(x, y)

    def save_csv(self):
        if not self.x_values:
            QMessageBox.information(self, "No data", "There are no graph samples to save yet.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save pressure data",
            "pressure_data.csv",
            "CSV files (*.csv)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".csv"):
            file_path += ".csv"

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(["sample_index", "measurement"])
                writer.writerows(zip(self.x_values, self.y_values))
            self.status_label.setText(f"Saved CSV: {file_path}")
        except OSError as error:
            QMessageBox.critical(self, "Save failed", f"Could not save the CSV file:\n{error}")

    def check_for_data(self):
        if not self.data_path.exists():
            return

        try:
            # Check both timestamp and size so same-second rewrites are noticed.
            stat = self.data_path.stat()
            signature = (stat.st_mtime_ns, stat.st_size)
            if signature == self.last_loaded_signature:
                return

            data = pd.read_pickle(self.data_path)
            records = data[0] if isinstance(data, tuple) else data
            if not isinstance(records, dict):
                raise ValueError("Expected a tuple whose first item is a dictionary")

            # Each entry is [ {pressure_key: pressure_value}, measurement ].
            # The dictionary key ("0", "1", etc.) is used as the sample index.
            samples = sorted(records.items(), key=lambda item: int(item[0]))
            x_values = []
            y_values = []
            for key, entry in samples:
                if not isinstance(entry, (list, tuple)) or len(entry) < 2:
                    continue
                x_values.append(int(key))
                y_values.append(float(entry[1]))

            if not x_values:
                raise ValueError("No graphable samples found in the pickle")

            self.x_values = x_values
            self.y_values = y_values
            self.update_graph(x_values, y_values)
            self.last_loaded_signature = signature
            self.status_label.setText(f"Loaded {len(x_values)} samples from {self.data_path}")
        except (OSError, EOFError, ValueError, TypeError, KeyError, pickle.UnpicklingError) as error:
            # A write may be in progress; leave the last good graph visible and retry.
            self.status_label.setText(f"Waiting for a complete, valid pickle: {error}")

    def update_graph(self, x_values, y_values):
        self.line.set_data(x_values, y_values)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()
