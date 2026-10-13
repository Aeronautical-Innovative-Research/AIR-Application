
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QGroupBox,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QFormLayout,
    QFrame,
    QMessageBox,
)
from PyQt5.QtCore import Qt, pyqtSignal


class ConfigWindow(QWidget):
    # Emitted when the user clicks Apply.
    settingsApplied = pyqtSignal(dict)

    
    def __init__(self, parent=None):
        super().__init__(parent)

        # Make this a separate top-level window.
        self.setWindowFlags(Qt.Window)

        self.setWindowTitle("Scan Settings")
        self.resize(1100, 740)
        self.setMinimumSize(950, 650)

        self.setup_ui()
        self.update_rate()

        # Center over the AIR application.
        if parent is not None:
            parent_center = parent.frameGeometry().center()
            self.move(
                parent_center.x() - self.width() // 2,
                parent_center.y() - self.height() // 2
            )
        else:
            screen = QApplication.primaryScreen()
            if screen:
                available = screen.availableGeometry()
                self.move(
                    available.center().x() - self.width() // 2,
                    available.center().y() - self.height() // 2
                )


    def setup_ui(self):
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(20)

        panel_layout.setContentsMargins(25, 20, 25, 20)
        panel_layout.setHorizontalSpacing(30)
        panel_layout.setVerticalSpacing(15)

        timing_group.setMinimumWidth(340)
        main_layout.addWidget(settings_panel, 1)

        # Heading
        heading = QLabel("DSA Scan Configuration")
        heading.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #222222;
                border-bottom: 2px solid #777777;
                padding-bottom: 5px;
            }
        """)
        main_layout.addWidget(heading, alignment=Qt.AlignLeft)

        # Settings panel
        settings_panel = QFrame()
        settings_panel.setObjectName("settingsPanel")
        settings_panel.setStyleSheet("""
            QFrame#settingsPanel {
                background-color: #D0D0D0;
                border: 1px solid #999999;
                border-radius: 3px;
            }
            QLabel {
                color: #222222;
                font-weight: bold;
                border: none;
                background: transparent;
            }
        """)

        panel_layout = QGridLayout(settings_panel)
        panel_layout.setContentsMargins(15, 12, 15, 12)
        panel_layout.setHorizontalSpacing(20)
        panel_layout.setVerticalSpacing(10)

        # ---------------------------------
        # LEFT SIDE: Timing configuration
        # ---------------------------------

        timing_group = QGroupBox()
        timing_group.setStyleSheet("""
            QGroupBox {
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        timing_group.setObjectName("timingPanel")

        timing_layout = QVBoxLayout(timing_group)
        timing_layout.setContentsMargins(0, 0, 0, 0)
        timing_layout.setSpacing(12)

        # Period
        period_label = QLabel("Period")
        self.period_input = QSpinBox()
        self.period_input.setRange(1, 100000000)
        self.period_input.setValue(250)
        self.period_input.setSuffix("")

        period_row = QHBoxLayout()
        period_row.addWidget(self.period_input)
        period_row.addWidget(QLabel("microseconds"))

        timing_layout.addWidget(period_label)
        timing_layout.addLayout(period_row)

        # Average
        average_label = QLabel("Average")
        self.average_input = QSpinBox()
        self.average_input.setRange(1, 1000000)
        self.average_input.setValue(10)

        timing_layout.addWidget(average_label)
        timing_layout.addWidget(self.average_input)

        # Rate
        rate_label = QLabel("Rate (Hz)")
        self.rate_display = QLabel("25")
        self.rate_display.setStyleSheet("""
            QLabel {
                background-color: #EEEEEE;
                border: 1px solid #AAAAAA;
                padding: 5px;
                font-weight: normal;
            }
        """)

        timing_layout.addWidget(rate_label)
        timing_layout.addWidget(self.rate_display)

        formula_label = QLabel(
            "Rate = 1/(Period*16*Average)"
        )
        formula_label.setWordWrap(True)
        formula_label.setStyleSheet(
            "font-size: 11px; font-weight: normal;"
        )
        formula_label.setObjectName("formulaLabel")
        timing_layout.addWidget(formula_label)

        # ---------------------------------
        # RIGHT SIDE: Scan configuration
        # ---------------------------------

        scan_layout = QFormLayout()
        scan_layout.setSpacing(9)
        scan_layout.setLabelAlignment(Qt.AlignLeft)

        # Frames per scan
        self.frames_input = QSpinBox()
        self.frames_input.setRange(1, 100000000)
        self.frames_input.setValue(1000)
        scan_layout.addRow(
            QLabel("Frames Per SCAN"),
            self.frames_input
        )

        # Conversion units
        self.conversion_units = QComboBox()
        self.conversion_units.addItems([
            "PA",
            "kPa",
            "Bar",
            "PSI",
            "User Defined",
        ])
        self.conversion_units.setCurrentText("PA")
        scan_layout.addRow(
            QLabel("Conversion Units"),
            self.conversion_units
        )

        # User units
        self.user_units_input = QDoubleSpinBox()
        self.user_units_input.setRange(-1e12, 1e12)
        self.user_units_input.setDecimals(6)
        self.user_units_input.setValue(6894.759766)
        self.user_units_input.setSingleStep(1.0)
        scan_layout.addRow(
            QLabel("User Units"),
            self.user_units_input
        )

        # Units
        self.units_combo = QComboBox()
        self.units_combo.addItems([
            "Engineering Units",
            "Raw Counts",
        ])
        scan_layout.addRow(
            QLabel("Units"),
            self.units_combo
        )

        # Time stamp
        self.timestamp_combo = QComboBox()
        self.timestamp_combo.addItems([
            "No Time Stamp",
            "Time Stamp",
        ])
        scan_layout.addRow(
            QLabel("Time Stamp"),
            self.timestamp_combo
        )

        # Zero correction
        self.zero_correct_combo = QComboBox()
        self.zero_correct_combo.addItems(["ON", "OFF"])
        scan_layout.addRow(
            QLabel("Zero Correct"),
            self.zero_correct_combo
        )

        # Scan trigger
        self.trigger_combo = QComboBox()
        self.trigger_combo.addItems([
            "Internal",
            "External",
        ])
        scan_layout.addRow(
            QLabel("SCAN Trigger"),
            self.trigger_combo
        )

        # Add the two columns to the settings panel.
        panel_layout.addWidget(timing_group, 0, 0)
        panel_layout.addLayout(scan_layout, 0, 1)

        panel_layout.setColumnStretch(0, 1)
        panel_layout.setColumnStretch(1, 2)

        main_layout.addWidget(settings_panel)

        # ---------------------------------
        # Bottom buttons
        # ---------------------------------

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)

        self.close_button = QPushButton("Close")
        self.close_button.setFixedSize(100, 35)
        self.close_button.clicked.connect(self.close)

        self.apply_button = QPushButton("Apply")
        self.apply_button.setFixedSize(100, 35)
        self.apply_button.clicked.connect(self.apply_settings)

        button_layout.addWidget(self.close_button)
        button_layout.addStretch()
        button_layout.addWidget(self.apply_button)

        main_layout.addLayout(button_layout)

        # Update rate when timing values change.
        self.period_input.valueChanged.connect(self.update_rate)
        self.average_input.valueChanged.connect(self.update_rate)

        # Basic control styling.
        
        settings_panel.setStyleSheet("""
            QFrame#settingsPanel {
                background-color: #D0D0D0;
                border: 1px solid #999999;
                border-radius: 5px;
            }

            QFrame#timingPanel {
                background-color: #252629;
                border: none;
                border-radius: 8px;
            }

            QFrame#timingPanel QLabel {
                color: #FFFFFF;
                background-color: transparent;
                border: none;
                font-size: 15px;
                font-weight: bold;
            }

            QFrame#timingPanel QLabel#formulaLabel {
                font-size: 13px;
                font-weight: normal;
            }

            QFrame#settingsPanel QLabel {
                color: #222222;
                background-color: transparent;
                border: none;
                font-size: 14px;
                font-weight: bold;
            }

            QFrame#settingsPanel QSpinBox,
            QFrame#settingsPanel QDoubleSpinBox,
            QFrame#settingsPanel QComboBox {
                background-color: #FFFFFF;
                color: #202020;
                border: 1px solid #AAAAAA;
                border-radius: 4px;
                min-height: 38px;
                padding: 4px 8px;
                font-size: 14px;
            }

            QFrame#settingsPanel QSpinBox::up-button,
            QFrame#settingsPanel QSpinBox::down-button,
            QFrame#settingsPanel QDoubleSpinBox::up-button,
            QFrame#settingsPanel QDoubleSpinBox::down-button {
                width: 20px;
            }
        """)


    def update_rate(self, *args):
        period = self.period_input.value()
        average = self.average_input.value()

        # Period is expressed in microseconds.
        rate = 1_000_000 / (period * 16 * average)

        self.rate_display.setText(f"{rate:g}")

    def get_settings(self):
        """Return the current configuration as a dictionary."""
        return {
            "period": self.period_input.value(),
            "average": self.average_input.value(),
            "rate_hz": float(self.rate_display.text()),
            "frames_per_scan": self.frames_input.value(),
            "conversion_units": self.conversion_units.currentText(),
            "user_units": self.user_units_input.value(),
            "units": self.units_combo.currentText(),
            "timestamp": self.timestamp_combo.currentText(),
            "zero_correct": self.zero_correct_combo.currentText(),
            "scan_trigger": self.trigger_combo.currentText(),
        }

    def apply_settings(self):
        settings = self.get_settings()

        self.settingsApplied.emit(settings)

        QMessageBox.information(
            self,
            "Scan Settings",
            "Settings applied successfully."
        )
