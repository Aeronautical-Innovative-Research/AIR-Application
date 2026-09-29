import sys

# PyQt
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QMessageBox
from PyQt5.QtCore import pyqtSlot

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
        
        # Connect Button
        self.ConnectButton = QPushButton("Connect", self)
        self.ConnectButton.move(100, 50)
        self.ConnectButton.clicked.connect(self.Connect)

        # Calibrate Button
        self.CalibrateButton = QPushButton("Calibrate", self)
        self.CalibrateButton.move(150, 50)
        self.CalibrateButton.clicked.connect(self.Calibrate)

        # Scan Button
        self.ScanButton = QPushButton("Scan", self)
        self.ScanButton.move(200, 50)
        self.ScanButton.clicked.connect(self.Scan)

        # Status Button
        self.StatusButton = QPushButton("Status", self)
        self.StatusButton.move(250, 50)
        self.StatusButton.clicked.connect(self.Status)

        # Close Button
        self.CloseButton = QPushButton("Close", self)
        self.CloseButton.move(300, 50)
        self.CloseButton.clicked.connect(self.Close)

        # Configure Button
        self.ConfigButton = QPushButton("Configuration", self)
        self.ConfigButton.move(350, 50)
        self.ConfigButton.clicked.connect(self.OpenConfigWindow)
        

    def Connect(self):
        self.dsa.connect
        QMessageBox.information(self, "Connection", "Connection Successful")

    def Calibrate(self):
        self.dsa.calz
        QMessageBox.information(self, "Calibration", "Calibration Successful")

    def Scan(self):
        self.dsa.scan
        # TODO

    def Status(self):
        QMessageBox.information(self, "Status", f"{self.dsa.status}")

    def Close(self):
        self.dsa.close
        QMessageBox.information(self, "Connection", "Closed Connection Successfully")

    def OpenConfigWindow(self):
        configWindow = ConfigWindow()   

    def closeEvent(self, event):
        self.Close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())