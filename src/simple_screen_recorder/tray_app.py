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
    QColorDialog,
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
from simple_screen_recorder.mouse_highlight import MouseHighlightOverlay
from simple_screen_recorder.window_select import select_window_id

try:
    from pynput import mouse as pynput_mouse
except Exception:  # pragma: no cover - optional runtime feature
    pynput_mouse = None

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

        self.highlight_mouse = QCheckBox("Highlight mouse cursor while recording")
        self.highlight_mouse.setChecked(config.highlight_mouse)

        self.click_effects = QCheckBox("Show click ripple effects")
        self.click_effects.setChecked(config.mouse_click_effects)

        self.highlight_size = QSpinBox()
        self.highlight_size.setRange(40, 200)
        self.highlight_size.setValue(config.mouse_highlight_size)

        self.highlight_thickness = QSpinBox()
        self.highlight_thickness.setRange(2, 16)
        self.highlight_thickness.setValue(config.mouse_highlight_thickness)

        self.highlight_opacity = QSpinBox()
        self.highlight_opacity.setRange(10, 100)
        self.highlight_opacity.setSuffix("%")
        self.highlight_opacity.setValue(config.mouse_highlight_opacity)

        self.highlight_color = QLineEdit(config.mouse_highlight_color)
        self.highlight_color.setPlaceholderText("#F6C445")
        color_button = QPushButton("Pick")
        color_button.clicked.connect(self._choose_highlight_color)
        color_widget = QWidget()
        color_layout = QHBoxLayout()
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.addWidget(self.highlight_color)
        color_layout.addWidget(color_button)
        color_widget.setLayout(color_layout)
        self._highlight_controls = [
            self.click_effects,
            self.highlight_size,
            self.highlight_thickness,
            self.highlight_opacity,
            self.highlight_color,
            color_button,
        ]
        self.highlight_mouse.toggled.connect(self._set_highlight_controls_enabled)
        self._set_highlight_controls_enabled(config.highlight_mouse)

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
        form.addRow("Mouse highlight", self.highlight_mouse)
        form.addRow("Click effects", self.click_effects)
        form.addRow("Highlight size", self.highlight_size)
        form.addRow("Highlight thickness", self.highlight_thickness)
        form.addRow("Highlight opacity", self.highlight_opacity)
        form.addRow("Highlight color", color_widget)
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

    def _set_highlight_controls_enabled(self, enabled: bool) -> None:
        for widget in self._highlight_controls:
            widget.setEnabled(enabled)

    def _choose_highlight_color(self) -> None:
        initial = QColorDialog.getColor(QColor(self.highlight_color.text().strip() or "#F6C445"), self)
        if initial.isValid():
            self.highlight_color.setText(initial.name().upper())

    def build_config(self) -> RecorderConfig:
        return RecorderConfig(
            output_dir=self.output_dir.text().strip(),
            capture_mode=self.capture_mode.currentData(),
            fps=self.fps.value(),
            container=self.container.currentText(),
            record_system_audio=self.record_system_audio.isChecked(),
            highlight_mouse=self.highlight_mouse.isChecked(),
            mouse_click_effects=self.click_effects.isChecked(),
            mouse_highlight_size=self.highlight_size.value(),
            mouse_highlight_thickness=self.highlight_thickness.value(),
            mouse_highlight_opacity=self.highlight_opacity.value(),
            mouse_highlight_color=self.highlight_color.text().strip() or "#F6C445",
            audio_source=self.audio_source.text().strip() or "auto",
            hotkey_toggle_recording=self.hotkey_toggle_recording.text().strip() or "<ctrl>+<alt>+r",
            hotkey_stop_recording=self.hotkey_stop_recording.text().strip() or "<ctrl>+<alt>+s",
        )


class TrayRecorderApp(QObject):
    hotkey_toggle_signal = pyqtSignal()
    hotkey_stop_signal = pyqtSignal()
    mouse_click_signal = pyqtSignal(str)

    def __init__(self, qt_app) -> None:
        super().__init__()
        self.qt_app = qt_app
        self.config = RecorderConfig.load()
        self.recorder = FfmpegRecorder()
        self.hotkeys = HotkeyManager(self._emit_hotkey_toggle, self._emit_hotkey_stop)
        self._mouse_click_listener: Optional[object] = None
        self.mouse_highlight_overlay = MouseHighlightOverlay(
            diameter=self.config.mouse_highlight_size,
            ring_thickness=self.config.mouse_highlight_thickness,
            opacity=self.config.mouse_highlight_opacity,
            color=self.config.mouse_highlight_color,
        )
        self.mouse_highlight_overlay.set_click_effects_enabled(self.config.mouse_click_effects)
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
        self.mouse_click_signal.connect(self._on_mouse_click_effect)
        self._register_hotkeys()
        self._start_mouse_click_listener()

        if not self.recorder.is_ffmpeg_available():
            self._error("ffmpeg is not available on PATH. Install ffmpeg first.")
        if self._is_wayland():
            self._warn("Wayland session detected. This version currently supports X11 capture only.")
        if pynput_mouse is None and self.config.mouse_click_effects:
            self._warn("Click effects are unavailable (pynput mouse listener could not be loaded).")

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

    def _start_mouse_click_listener(self) -> None:
        if pynput_mouse is None or self._mouse_click_listener is not None:
            return

        def _on_click(_x, _y, button, pressed) -> None:
            if not pressed:
                return
            button_name = getattr(button, "name", str(button))
            self.mouse_click_signal.emit(button_name)

        try:
            listener = pynput_mouse.Listener(on_click=_on_click)
            listener.start()
            self._mouse_click_listener = listener
        except Exception as exc:
            self._mouse_click_listener = None
            self._warn(f"Could not start click effects listener: {exc}")

    def _stop_mouse_click_listener(self) -> None:
        if self._mouse_click_listener is None:
            return
        try:
            self._mouse_click_listener.stop()
        except Exception:
            pass
        self._mouse_click_listener = None

    def _on_mouse_click_effect(self, button_name: str) -> None:
        if not self.recorder.is_recording:
            return
        if not self.config.highlight_mouse:
            return
        if not self.config.mouse_click_effects:
            return
        self.mouse_highlight_overlay.trigger_click_effect(button_name)

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
        self.mouse_highlight_overlay.apply_style(
            diameter=self.config.mouse_highlight_size,
            ring_thickness=self.config.mouse_highlight_thickness,
            opacity=self.config.mouse_highlight_opacity,
            color=self.config.mouse_highlight_color,
        )
        self.mouse_highlight_overlay.set_click_effects_enabled(self.config.mouse_click_effects)
        if self.config.highlight_mouse:
            self.mouse_highlight_overlay.start()
        else:
            self.mouse_highlight_overlay.stop()
        self._update_actions()
        self._info(f"Recording started: {output_path.name}")

    def stop_recording(self) -> None:
        stopped, message = self.recorder.stop()
        self.mouse_highlight_overlay.stop()
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
        self.mouse_highlight_overlay.apply_style(
            diameter=self.config.mouse_highlight_size,
            ring_thickness=self.config.mouse_highlight_thickness,
            opacity=self.config.mouse_highlight_opacity,
            color=self.config.mouse_highlight_color,
        )
        self.mouse_highlight_overlay.set_click_effects_enabled(self.config.mouse_click_effects)
        if self.recorder.is_recording:
            if self.config.highlight_mouse:
                self.mouse_highlight_overlay.start()
            else:
                self.mouse_highlight_overlay.stop()
        self._register_hotkeys()
        self._info("Settings saved.")

    def open_output_folder(self) -> None:
        folder = Path(self.config.output_dir).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def quit_app(self) -> None:
        self.mouse_highlight_overlay.stop()
        self._stop_mouse_click_listener()
        if self.recorder.is_recording:
            self.stop_recording()
        self.hotkeys.stop()
        self.tray.hide()
        self.qt_app.quit()
