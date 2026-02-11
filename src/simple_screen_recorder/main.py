from __future__ import annotations

import signal
import sys

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from simple_screen_recorder.tray_app import APP_TITLE, TrayRecorderApp


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Keep Python signal processing alive while Qt event loop is running.
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    signal.signal(signal.SIGTERM, lambda *_: app.quit())
    signal_timer = QTimer()
    signal_timer.start(250)
    signal_timer.timeout.connect(lambda: None)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, APP_TITLE, "No system tray available on this desktop session.")
        return 1

    _tray_app = TrayRecorderApp(app)
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
