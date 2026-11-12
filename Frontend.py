"""Compatibility entry point. Prefer `python -m air_app`."""
from air_app.ui import MainWindow as Window, main

if __name__ == '__main__':
    raise SystemExit(main())
