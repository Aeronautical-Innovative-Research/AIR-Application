"""Explicit device registration. Only implemented instruments belong here.

Each device provides a QWidget workspace and cooperative shutdown hooks. The
application shell owns navigation and run identity; each workspace owns its
settings, connection, plots, and device-specific worker. No pressure commands
or frame schema are required of future instruments.
"""
from dataclasses import dataclass
from typing import Callable
from PyQt5.QtWidgets import QWidget
from ..run_storage import RunStoragePanel


class DeviceWorkspace(QWidget):
    """Lifecycle contract for instrument workspaces hosted by the shell."""

    def request_shutdown(self):
        raise NotImplementedError

    def shutdown_complete(self):
        raise NotImplementedError


@dataclass(frozen=True)
class DeviceModule:
    key: str
    title: str
    create_workspace: Callable[[RunStoragePanel], DeviceWorkspace]


def available_devices():
    from .pressure_scanner.panel import PressureScannerPanel
    return (DeviceModule('pressure_scanner', 'Pressure scanner', PressureScannerPanel),)
