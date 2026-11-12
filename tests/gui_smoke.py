import sys, tempfile, time
from pathlib import Path
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication
sys.path.insert(0, str(Path.cwd()))
from air_app.ui import MainWindow

root = tempfile.TemporaryDirectory(prefix='air-gui-')
QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, root.name)
app = QApplication([])
import qdarktheme
app.setStyleSheet(qdarktheme.load_stylesheet())
shell = MainWindow()
shell.show()
window = shell.workspaces['pressure_scanner']
def until(predicate, timeout=10):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(.01)
        if predicate():
            return
    raise AssertionError('Timed out: ' + window.log.toPlainText())
assert window.frames.text() == str(window.frames.value())
assert window.units.minimumWidth() >= 150
assert shell.run_storage.title() == 'Run storage'
from air_app.storage import DEFAULT_RUNS
assert Path(window.folder.text()) == DEFAULT_RUNS
assert DEFAULT_RUNS.parent == Path.cwd()
window.demo.setChecked(True)
window.connect_scanner()
until(lambda: window.is_connected and not window.pending)
window.folder.setText(root.name)
window.notes.setPlainText('Multiline notes\nOperator: demo')
window.name.setText('GUI acceptance')
window.period.setValue(250)
window.average.setValue(10)
window.frames.setValue(20)
window.start_scan()
until(lambda: window.current_path is not None and not window.pending)
until(lambda: window.total == 20)
assert len(window.samples) == 20
window.submit('diagnostics')
until(lambda: not window.pending)
assert window.is_connected
assert 'ERROR: No errors' in window.log.toPlainText()
assert len(list(window.current_path.glob('*.csv'))) == 1
shell.grab().save('/private/tmp/air-dashboard.png')
shell.resize(1120, 820)
app.processEvents()
shell.grab().save('/private/tmp/air-dashboard-small.png')
window.frames.setValue(0)
window.start_scan()
until(lambda: window.total > 2)
window.worker.stop_run.set()
until(lambda: not window.pending)
shell.close()
until(lambda: not window.worker.isRunning())
app.processEvents()
print('PASS: demo connection, finite recording/plot, continuous stop, clean shutdown')
root.cleanup()
