from PyQt5.QtWidgets import QApplication, QWidget, QPushButton
from PyQt5.QtCore import pyqtSlot
import sys

class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AIR")
        self.setGeometry(100, 60, 800, 600)
        self.ConnectButton = QPushButton("Connect", self)
        self.ConnectButton.move(100, 50)
        self.CalibrateButton = QPushButton("Calibrate", self)
        self.CalibrateButton.move(150, 50)
        self.ScanButton = QPushButton("Scan", self)
        self.ScanButton.move(200, 50)
        self.StatusButton = QPushButton("Status", self)
        self.StatusButton.move(250, 50)
        self.CloseButton = QPushButton("Close", self)
        self.CloseButton.move(300, 50)
        self.ConfigButton = QPushButton("Configuration", self)
        self.ConfigButton.move(350, 50)

    # def closeEvent(self, event):
    #    closeConnection()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())