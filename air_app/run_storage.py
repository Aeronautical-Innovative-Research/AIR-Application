"""Shared run identity and storage controls, independent of any instrument."""
from pathlib import Path
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (QFileDialog, QFormLayout, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout)
from .storage import DEFAULT_RUNS
from .preferences import preferences


class RunStoragePanel(QGroupBox):
    def __init__(self):
        super().__init__('Run storage')
        self.preferences = preferences('Application')
        self.current_path = None
        grid = QGridLayout(self)
        grid.setContentsMargins(16, 22, 16, 16)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(10)
        fields = QFormLayout()
        fields.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        fields.setHorizontalSpacing(16)
        fields.setVerticalSpacing(10)
        self.name = QLineEdit()
        self.name.setPlaceholderText('Run name, e.g. wing-A_10-deg')
        self.name.setMinimumWidth(280)
        self.folder = QLineEdit(self.preferences.value('run_folder', str(DEFAULT_RUNS)))
        self.folder.setMinimumWidth(280)
        self.folder.setToolTip(self.folder.text())
        self.folder.textChanged.connect(self.folder.setToolTip)
        self.choose_button = QPushButton('Choose…')
        self.choose_button.clicked.connect(self.choose_folder)
        self.default_button = QPushButton('Use default')
        self.default_button.clicked.connect(lambda: self.set_folder(str(DEFAULT_RUNS)))
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder, 1)
        folder_row.addWidget(self.choose_button)
        folder_row.addWidget(self.default_button)
        fields.addRow('Run name', self.name)
        fields.addRow('Save folder', folder_row)
        grid.addLayout(fields, 0, 0)
        notes = QVBoxLayout()
        notes.addWidget(QLabel('Notes'))
        self.notes = QPlainTextEdit()
        self.notes.setPlaceholderText('Conditions, model, operator, observations…')
        self.notes.setMinimumWidth(280)
        self.notes.setFixedHeight(80)
        notes.addWidget(self.notes)
        grid.addLayout(notes, 0, 1)
        self.saved_label = QLabel('Each run saves its date, name, settings, and measurements.')
        self.saved_label.setWordWrap(True)
        self.show_button = QPushButton('Show run folder')
        self.show_button.clicked.connect(self.show_folder)
        footer = QHBoxLayout()
        footer.addWidget(self.saved_label, 1)
        footer.addWidget(self.show_button)
        grid.addLayout(footer, 1, 0, 1, 2)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)

    def save_preferences(self):
        self.preferences.setValue('run_folder', self.folder.text())

    def set_folder(self, path):
        self.folder.setText(path)
        self.save_preferences()

    def choose_folder(self):
        path = QFileDialog.getExistingDirectory(self, 'Run storage folder', self.folder.text())
        if path:
            self.set_folder(path)

    def set_locked(self, locked):
        for widget in (self.name, self.notes, self.folder, self.choose_button, self.default_button):
            widget.setEnabled(not locked)

    def show_folder(self):
        path = self.current_path or Path(self.folder.text()).expanduser()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
