"""Application shell: shared run storage, device workspaces, and shutdown."""
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget
from .devices.registry import available_devices
from .run_storage import RunStoragePanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('AIR • Wind tunnel')
        self.resize(1440, 1000)
        self.setMinimumSize(1120, 820)
        self.setStyleSheet('''
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                min-height: 32px; padding: 2px 8px;
            }
            QPushButton { min-height: 30px; padding: 3px 12px; }
            QGroupBox { font-weight: 600; margin-top: 12px; }
        ''')
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 12, 20, 16)
        layout.setSpacing(12)
        title = QLabel('AIR  /  WIND TUNNEL')
        title.setStyleSheet('font-size: 22px; font-weight: bold; padding: 8px 0;')
        layout.addWidget(title)
        self.run_storage = RunStoragePanel()
        layout.addWidget(self.run_storage)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.workspaces = {}
        for module in available_devices():
            workspace = module.create_workspace(self.run_storage)
            self.workspaces[module.key] = workspace
            self.tabs.addTab(workspace, module.title)
        self.shutdown_timer = QTimer(self)
        self.shutdown_timer.setInterval(50)
        self.shutdown_timer.timeout.connect(self.finish_shutdown)

    def closeEvent(self, event):
        if all(workspace.shutdown_complete() for workspace in self.workspaces.values()):
            self.shutdown_timer.stop()
            event.accept()
            return
        event.ignore()
        if not self.shutdown_timer.isActive():
            self.centralWidget().setEnabled(False)
            self.statusBar().showMessage('Stopping devices and closing run files…')
            for workspace in self.workspaces.values():
                workspace.request_shutdown()
            self.shutdown_timer.start()

    def finish_shutdown(self):
        if all(workspace.shutdown_complete() for workspace in self.workspaces.values()):
            self.close()


def main():
    import sys
    import qdarktheme
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarktheme.load_stylesheet())
    window = MainWindow()
    window.show()
    return app.exec_()
