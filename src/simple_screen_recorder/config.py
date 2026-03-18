from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

APP_DIR_NAME = "simple-screen-recorder"
CONFIG_DIR = Path.home() / ".config" / APP_DIR_NAME
CONFIG_FILE = CONFIG_DIR / "config.json"

CAPTURE_MODE_FULL = "full_screen"
CAPTURE_MODE_WINDOW = "window"
VALID_CAPTURE_MODES = {CAPTURE_MODE_FULL, CAPTURE_MODE_WINDOW}
VALID_CONTAINERS = {"mp4", "mkv"}


def _to_bool(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


@dataclass
class RecorderConfig:
    output_dir: str = str(Path.home() / "Videos" / "Recordings")
    capture_mode: str = CAPTURE_MODE_FULL
    fps: int = 30
    container: str = "mkv"
    record_system_audio: bool = False
    highlight_mouse: bool = False
    mouse_click_effects: bool = True
    mouse_highlight_size: int = 84
    mouse_highlight_thickness: int = 4
    mouse_highlight_opacity: int = 70
    mouse_highlight_color: str = "#F6C445"
    audio_source: str = "auto"
    hotkey_toggle_recording: str = "<ctrl>+<alt>+r"
    hotkey_stop_recording: str = "<ctrl>+<alt>+s"

    @classmethod
    def load(cls) -> "RecorderConfig":
        if not CONFIG_FILE.exists():
            return cls()

        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()

        defaults = cls()
        try:
            fps = int(data.get("fps", defaults.fps))
        except (TypeError, ValueError):
            fps = defaults.fps

        record_system_audio = _to_bool(data.get("record_system_audio", defaults.record_system_audio))
        # Backward compatibility with previous cursor-scaling config key.
        legacy_scale_cursor = _to_bool(data.get("scale_cursor_during_recording", defaults.highlight_mouse))
        highlight_mouse = _to_bool(data.get("highlight_mouse", legacy_scale_cursor))
        mouse_click_effects = _to_bool(data.get("mouse_click_effects", defaults.mouse_click_effects))
        highlight_size = _to_int(
            data.get("mouse_highlight_size", data.get("recording_cursor_size", defaults.mouse_highlight_size)),
            defaults.mouse_highlight_size,
        )
        highlight_thickness = _to_int(
            data.get("mouse_highlight_thickness", defaults.mouse_highlight_thickness),
            defaults.mouse_highlight_thickness,
        )
        highlight_opacity = _to_int(
            data.get("mouse_highlight_opacity", defaults.mouse_highlight_opacity),
            defaults.mouse_highlight_opacity,
        )
        highlight_color = str(data.get("mouse_highlight_color", defaults.mouse_highlight_color)).strip()

        config = cls(
            output_dir=str(data.get("output_dir", defaults.output_dir)),
            capture_mode=str(data.get("capture_mode", defaults.capture_mode)),
            fps=fps,
            container=str(data.get("container", defaults.container)),
            record_system_audio=record_system_audio,
            highlight_mouse=highlight_mouse,
            mouse_click_effects=mouse_click_effects,
            mouse_highlight_size=highlight_size,
            mouse_highlight_thickness=highlight_thickness,
            mouse_highlight_opacity=highlight_opacity,
            mouse_highlight_color=highlight_color,
            audio_source=str(data.get("audio_source", defaults.audio_source)),
            hotkey_toggle_recording=str(
                data.get("hotkey_toggle_recording", defaults.hotkey_toggle_recording)
            ),
            hotkey_stop_recording=str(data.get("hotkey_stop_recording", defaults.hotkey_stop_recording)),
        )
        return config._validated()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    def _validated(self) -> "RecorderConfig":
        if self.capture_mode not in VALID_CAPTURE_MODES:
            self.capture_mode = CAPTURE_MODE_FULL

        if self.container not in VALID_CONTAINERS:
            self.container = "mkv"

        if self.fps < 1 or self.fps > 120:
            self.fps = 30

        if not self.output_dir:
            self.output_dir = str(Path.home() / "Videos" / "Recordings")

        self.record_system_audio = bool(self.record_system_audio)
        self.highlight_mouse = bool(self.highlight_mouse)
        self.mouse_click_effects = bool(self.mouse_click_effects)
        if self.mouse_highlight_size < 40 or self.mouse_highlight_size > 200:
            self.mouse_highlight_size = 84
        if self.mouse_highlight_thickness < 2 or self.mouse_highlight_thickness > 16:
            self.mouse_highlight_thickness = 4
        if self.mouse_highlight_opacity < 10 or self.mouse_highlight_opacity > 100:
            self.mouse_highlight_opacity = 70
        if not _is_hex_color(self.mouse_highlight_color):
            self.mouse_highlight_color = "#F6C445"

        if not self.audio_source:
            self.audio_source = "auto"

        if not self.hotkey_toggle_recording:
            self.hotkey_toggle_recording = "<ctrl>+<alt>+r"

        if not self.hotkey_stop_recording:
            self.hotkey_stop_recording = "<ctrl>+<alt>+s"

        return self


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _is_hex_color(value: str) -> bool:
    if len(value) != 7 or not value.startswith("#"):
        return False
    try:
        int(value[1:], 16)
    except ValueError:
        return False
    return True
