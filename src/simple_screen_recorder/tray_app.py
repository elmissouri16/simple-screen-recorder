from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QObject, Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from simple_screen_recorder.config import CAPTURE_MODE_FULL, CAPTURE_MODE_WINDOW, RecorderConfig
from simple_screen_recorder.ffmpeg_backend import FfmpegRecorder
from simple_screen_recorder.hotkeys import HotkeyManager
from simple_screen_recorder.window_select import select_window_id

APP_TITLE = "Simple Screen Recorder"


class SettingsDialog(QDialog):
    def __init__(self, config: RecorderConfig, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Recorder Settings")
        self.setMinimumWidth(420)

        self.capture_mode = QComboBox()
        self.capture_mode.addItem("Full screen", CAPTURE_MODE_FULL)
        self.capture_mode.addItem("Select window on start", CAPTURE_MODE_WINDOW)
        self.capture_mode.setCurrentIndex(max(self.capture_mode.findData(config.capture_mode), 0))

        self.output_dir = QLineEdit(config.output_dir)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._choose_output_dir)

        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_dir)
        output_layout.addWidget(browse_button)
        output_widget = QWidget()
        output_widget.setLayout(output_layout)

        self.fps = QSpinBox()
        self.fps.setRange(1, 120)
        self.fps.setValue(config.fps)

        self.container = QComboBox()
        self.container.addItems(["mp4", "mkv"])
        self.container.setCurrentIndex(max(self.container.findText(config.container), 0))

        self.record_system_audio = QCheckBox("Enable system audio recording")
        self.record_system_audio.setChecked(config.record_system_audio)

        self.audio_source = QLineEdit(config.audio_source)
        self.audio_source.setPlaceholderText("Pulse source (auto, default, or explicit source name)")
        self.audio_source.setEnabled(config.record_system_audio)
        self.record_system_audio.toggled.connect(self.audio_source.setEnabled)

        self.hotkey_toggle_recording = QLineEdit(config.hotkey_toggle_recording)
        self.hotkey_toggle_recording.setPlaceholderText("Example: <ctrl>+<alt>+r")

        self.hotkey_stop_recording = QLineEdit(config.hotkey_stop_recording)
        self.hotkey_stop_recording.setPlaceholderText("Example: <ctrl>+<alt>+s")

        form = QFormLayout()
        form.addRow("Capture mode", self.capture_mode)
        form.addRow("Output directory", output_widget)
        form.addRow("Frames per second", self.fps)
        form.addRow("Container", self.container)
        form.addRow("System audio", self.record_system_audio)
        form.addRow("Audio source", self.audio_source)
        form.addRow("Hotkey: toggle rec", self.hotkey_toggle_recording)
        form.addRow("Hotkey: stop rec", self.hotkey_stop_recording)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _choose_output_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Choose output directory", self.output_dir.text())
        if selected:
            self.output_dir.setText(selected)

    def build_config(self) -> RecorderConfig:
        return RecorderConfig(
            output_dir=self.output_dir.text().strip(),
            capture_mode=self.capture_mode.currentData(),
            fps=self.fps.value(),
            container=self.container.currentText(),
            record_system_audio=self.record_system_audio.isChecked(),
            audio_source=self.audio_source.text().strip() or "auto",
            hotkey_toggle_recording=self.hotkey_toggle_recording.text().strip() or "<ctrl>+<alt>+r",
            hotkey_stop_recording=self.hotkey_stop_recording.text().strip() or "<ctrl>+<alt>+s",
        )


class TrayRecorderApp(QObject):
    hotkey_toggle_signal = pyqtSignal()
    hotkey_stop_signal = pyqtSignal()

    def __init__(self, qt_app) -> None:
        super().__init__()
        self.qt_app = qt_app
        self.config = RecorderConfig.load()
        self.recorder = FfmpegRecorder()
        self.hotkeys = HotkeyManager(self._emit_hotkey_toggle, self._emit_hotkey_stop)
        self.current_output_path: Optional[Path] = None

        self.idle_icon = self._load_state_icon(recording=False)
        self.recording_icon = self._load_state_icon(recording=True)
        self.stop_icon = self._load_stop_icon()

        self.tray = QSystemTrayIcon(self.idle_icon)
        self.tray.setToolTip(APP_TITLE)
        self.tray.activated.connect(self._on_tray_activated)

        self.menu = QMenu()
        self.action_start = QAction("Start Recording")
        self.action_start.setIcon(self.recording_icon)
        self.action_start.triggered.connect(self.start_recording)
        self.menu.addAction(self.action_start)

        self.action_stop = QAction("Stop Recording")
        self.action_stop.setIcon(self.stop_icon)
        self.action_stop.triggered.connect(self.stop_recording)
        self.menu.addAction(self.action_stop)

        self.menu.addSeparator()
        self.action_settings = QAction("Settings")
        self.action_settings.triggered.connect(self.open_settings)
        self.menu.addAction(self.action_settings)

        self.action_open_output = QAction("Open Output Folder")
        self.action_open_output.triggered.connect(self.open_output_folder)
        self.menu.addAction(self.action_open_output)

        self.menu.addSeparator()
        self.action_quit = QAction("Quit")
        self.action_quit.triggered.connect(self.quit_app)
        self.menu.addAction(self.action_quit)

        self.tray.setContextMenu(self.menu)
        self.tray.show()
        self._update_actions()
        self.hotkey_toggle_signal.connect(self._on_hotkey_toggle)
        self.hotkey_stop_signal.connect(self._on_hotkey_stop)
        self._register_hotkeys()

        if not self.recorder.is_ffmpeg_available():
            self._error("ffmpeg is not available on PATH. Install ffmpeg first.")
        if self._is_wayland():
            self._warn("Wayland session detected. This version currently supports X11 capture only.")

    def _load_icon_from_assets(self, candidates: list[str]) -> QIcon:
        base_dir = Path(__file__).resolve().parent / "assets"
        for name in candidates:
            path = base_dir / name
            if not path.exists():
                continue
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon
        return QIcon()

    def _load_state_icon(self, recording: bool) -> QIcon:
        asset_candidates = ["recording.png", "tray-recording.png"] if recording else ["idle.png", "tray-idle.png"]
        asset_icon = self._load_icon_from_assets(asset_candidates)
        if not asset_icon.isNull():
            return asset_icon

        theme_icon = "media-record" if recording else "video-display"
        icon = QIcon.fromTheme(theme_icon)
        if not icon.isNull():
            return icon

        pix = QPixmap(48, 48)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)
        color = QColor("#E02424" if recording else "#1D4E89")
        painter.setBrush(color)
        painter.drawEllipse(8, 8, 32, 32)
        painter.end()
        return QIcon(pix)

    def _load_stop_icon(self) -> QIcon:
        asset_icon = self._load_icon_from_assets(["stop-recording.png", "stop.png"])
        if not asset_icon.isNull():
            return asset_icon
        icon = QIcon.fromTheme("media-playback-stop")
        if not icon.isNull():
            return icon
        return self.idle_icon

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            if self.recorder.is_recording:
                self.stop_recording()
            else:
                self.start_recording()

    def _is_wayland(self) -> bool:
        return os.environ.get("XDG_SESSION_TYPE", "").strip().lower() == "wayland"

    def _make_output_path(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"recording-{timestamp}.{self.config.container}"
        return Path(self.config.output_dir).expanduser() / filename

    def _prepare_output_dir(self) -> tuple[bool, str]:
        output_dir = Path(self.config.output_dir).expanduser()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            return True, ""
        except OSError as exc:
            return False, f"Cannot use output directory: {exc}"

    def _update_actions(self) -> None:
        recording = self.recorder.is_recording
        ffmpeg_available = self.recorder.is_ffmpeg_available()
        self.action_start.setEnabled((not recording) and ffmpeg_available)
        self.action_stop.setEnabled(recording)
        self.tray.setIcon(self.recording_icon if recording else self.idle_icon)

    def _info(self, text: str) -> None:
        self.tray.showMessage(APP_TITLE, text, QSystemTrayIcon.NoIcon, 3000)

    def _warn(self, text: str) -> None:
        self.tray.showMessage(APP_TITLE, text, QSystemTrayIcon.NoIcon, 4000)

    def _error(self, text: str) -> None:
        QMessageBox.critical(None, APP_TITLE, text)

    def _emit_hotkey_toggle(self) -> None:
        self.hotkey_toggle_signal.emit()

    def _emit_hotkey_stop(self) -> None:
        self.hotkey_stop_signal.emit()

    def _on_hotkey_toggle(self) -> None:
        if self.recorder.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def _on_hotkey_stop(self) -> None:
        if self.recorder.is_recording:
            self.stop_recording()

    def _register_hotkeys(self) -> None:
        ok, message = self.hotkeys.start(
            self.config.hotkey_toggle_recording,
            self.config.hotkey_stop_recording,
        )
        if not ok:
            self._warn(message)

    def start_recording(self) -> None:
        if self.recorder.is_recording:
            return
        if self._is_wayland():
            self._error("Wayland session detected. Switch to an X11 session to use this recorder.")
            return
        if not self.recorder.is_ffmpeg_available():
            self._error("ffmpeg is missing. Install it and restart the app.")
            self._update_actions()
            return

        self.config = self.config._validated()
        ok, error = self._prepare_output_dir()
        if not ok:
            self._error(error)
            return

        window_id = None
        if self.config.capture_mode == CAPTURE_MODE_WINDOW:
            self._info("Click the target window to start recording.")
            window_id = select_window_id()
            if not window_id:
                self._warn("Window selection canceled.")
                return

        output_path = self._make_output_path()
        started, message = self.recorder.start(self.config, output_path=output_path, window_id=window_id)
        if not started:
            self._error(f"Failed to start recording. {message}")
            self._update_actions()
            return

        self.current_output_path = output_path
        self._update_actions()
        self._info(f"Recording started: {output_path.name}")

    def stop_recording(self) -> None:
        stopped, message = self.recorder.stop()
        self._update_actions()

        if not stopped:
            self._error(message)
            return

        if self.current_output_path:
            if message:
                self._info(f"{message} {self.current_output_path.name}")
            else:
                self._info(f"Recording saved: {self.current_output_path}")
            self.current_output_path = None
        else:
            self._info("Recording stopped.")

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.config)
        if dialog.exec_() != QDialog.Accepted:
            return

        updated = dialog.build_config()._validated()
        self.config = updated
        self.config.save()
        self._register_hotkeys()
        self._info("Settings saved.")

    def open_output_folder(self) -> None:
        folder = Path(self.config.output_dir).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def quit_app(self) -> None:
        if self.recorder.is_recording:
            self.stop_recording()
        self.hotkeys.stop()
        self.tray.hide()
        self.qt_app.quit()
