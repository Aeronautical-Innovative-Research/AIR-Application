"""Explicit settings format also lets headless checks isolate preferences."""
from PyQt5.QtCore import QSettings


def preferences(scope):
    return QSettings(QSettings.defaultFormat(), QSettings.UserScope, 'AIR', scope)
