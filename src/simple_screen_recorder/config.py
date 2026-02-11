from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

APP_DIR_NAME = "simple-screen-recorder"
CONFIG_DIR = Path.home() / ".config" / APP_DIR_NAME
CONFIG_FILE = CONFIG_DIR / "config.json"

CAPTURE_MODE_FULL = "full_screen"
CAPTURE_MODE_WINDOW = "window"
VALID_CAPTURE_MODES = {CAPTURE_MODE_FULL, CAPTURE_MODE_WINDOW}
VALID_CONTAINERS = {"mp4", "mkv"}


@dataclass
class RecorderConfig:
    output_dir: str = str(Path.home() / "Videos" / "Recordings")
    capture_mode: str = CAPTURE_MODE_FULL
    fps: int = 30
    container: str = "mkv"
    record_system_audio: bool = False
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

        record_system_audio = data.get("record_system_audio", defaults.record_system_audio)
        if isinstance(record_system_audio, str):
            record_system_audio = record_system_audio.strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
        else:
            record_system_audio = bool(record_system_audio)

        config = cls(
            output_dir=str(data.get("output_dir", defaults.output_dir)),
            capture_mode=str(data.get("capture_mode", defaults.capture_mode)),
            fps=fps,
            container=str(data.get("container", defaults.container)),
            record_system_audio=record_system_audio,
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

        if not self.audio_source:
            self.audio_source = "auto"

        if not self.hotkey_toggle_recording:
            self.hotkey_toggle_recording = "<ctrl>+<alt>+r"

        if not self.hotkey_stop_recording:
            self.hotkey_stop_recording = "<ctrl>+<alt>+s"

        return self
