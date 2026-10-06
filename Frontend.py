import sys

# PyQt
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QMessageBox,
    QHBoxLayout,
    QVBoxLayout
)

import qdarktheme

# Windows
from Windows.ConfigWindow import ConfigWindow

# Backend
from modules.pressure_scanner.dsa_talker import DSA


class Window(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AIR")
        self.setGeometry(100, 60, 800, 600)

        # Setup DSA for connection
        self.dsa = DSA("191.191.192.176")

        # -------------------------
        # Create Buttons
        # -------------------------

        self.ConnectButton = QPushButton("Connect")
        self.ConnectButton.clicked.connect(self.Connect)

        self.CalibrateButton = QPushButton("Calibrate")
        self.CalibrateButton.clicked.connect(self.Calibrate)

        self.ScanButton = QPushButton("Scan")
        self.ScanButton.clicked.connect(self.Scan)

        self.StatusButton = QPushButton("Status")
        self.StatusButton.clicked.connect(self.Status)

        self.CloseButton = QPushButton("Close")
        self.CloseButton.clicked.connect(self.Close)

        self.ConfigButton = QPushButton("Configuration")
        self.ConfigButton.clicked.connect(self.OpenConfigWindow)

        # -------------------------
        # Button Styling
        # -------------------------

        # button_style = """
        #     QPushButton {
        #         background-color: #2D6CDF;
        #         color: white;
        #         border: none;
        #         border-radius: 6px;
        #         padding: 10px 18px;
        #         font-size: 14px;
        #         font-weight: bold;
        #     }

        #     QPushButton:hover {
        #         background-color: #1F5BB5;
        #     }

        #     QPushButton:pressed {
        #         background-color: #174A91;
        #     }
        # """

        # self.ConnectButton.setStyleSheet(button_style)
        # self.CalibrateButton.setStyleSheet(button_style)
        # self.ScanButton.setStyleSheet(button_style)
        # self.StatusButton.setStyleSheet(button_style)
        # self.CloseButton.setStyleSheet(button_style)
        # self.ConfigButton.setStyleSheet(button_style)

        # -------------------------
        # Layout
        # -------------------------

        button_layout = QHBoxLayout()

        button_layout.setSpacing(15)
        button_layout.setContentsMargins(20, 20, 20, 0)

        button_layout.addWidget(self.ConnectButton)
        button_layout.addWidget(self.CalibrateButton)
        button_layout.addWidget(self.ScanButton)
        button_layout.addWidget(self.StatusButton)
        button_layout.addWidget(self.CloseButton)
        button_layout.addWidget(self.ConfigButton)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)

        # Push everything else toward the bottom
        main_layout.addStretch()

        self.setLayout(main_layout)

    # -------------------------
    # Button Functions
    # -------------------------

    def Connect(self):
        self.dsa.connect()
        QMessageBox.information(
            self,
            "Connection",
            "Connection Successful"
        )

    def Calibrate(self):
        self.dsa.calz()
        QMessageBox.information(
            self,
            "Calibration",
            "Calibration Successful"
        )

    def Scan(self):
        self.dsa.scan()
        # TODO

    def Status(self):
        QMessageBox.information(
            self,
            "Status",
            f"{self.dsa.status}"
        )

    def Close(self):
        self.dsa.close()
        QMessageBox.information(
            self,
            "Connection",
            "Closed Connection Successfully"
        )

    def OpenConfigWindow(self):
        configWindow = ConfigWindow()
        configWindow.show()

    def closeEvent(self, event):
        self.Close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarktheme.load_stylesheet())

    window = Window()
    window.show()

    sys.exit(app.exec_())

