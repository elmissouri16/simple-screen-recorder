from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Optional

from simple_screen_recorder.config import RecorderConfig


class FfmpegRecorder:
    def __init__(self) -> None:
        self._process: Optional[subprocess.Popen] = None

    @property
    def is_recording(self) -> bool:
        return self._process is not None and self._process.poll() is None

    @staticmethod
    def is_ffmpeg_available() -> bool:
        return shutil.which("ffmpeg") is not None

    @staticmethod
    def _display() -> str:
        return os.environ.get("DISPLAY", ":0.0")

    @staticmethod
    def _read_screen_dimensions() -> tuple[int, int]:
        cmd = ["xdpyinfo"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        match = re.search(r"dimensions:\s+(\d+)x(\d+)\s+pixels", result.stdout)
        if not match:
            raise RuntimeError("Could not detect screen dimensions with xdpyinfo.")
        return int(match.group(1)), int(match.group(2))

    @staticmethod
    def _list_pulse_sources() -> list[str]:
        if shutil.which("pactl") is None:
            return []
        result = subprocess.run(
            ["pactl", "list", "short", "sources"], capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            return []

        names: list[str] = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                names.append(parts[1])
        return names

    @staticmethod
    def _default_sink_name() -> Optional[str]:
        if shutil.which("pactl") is None:
            return None
        result = subprocess.run(["pactl", "info"], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return None
        match = re.search(r"^Default Sink:\s*(.+)$", result.stdout, flags=re.MULTILINE)
        if not match:
            return None
        sink = match.group(1).strip()
        return sink or None

    def _resolve_audio_source(self, requested: str) -> str:
        source = requested.strip().lower()
        if source and source not in {"auto", "default"}:
            return requested.strip()

        available_sources = self._list_pulse_sources()
        if not available_sources:
            return "default"

        default_sink = self._default_sink_name()
        if default_sink:
            monitor_source = f"{default_sink}.monitor"
            if monitor_source in available_sources:
                return monitor_source

        for name in available_sources:
            if name.endswith(".monitor"):
                return name

        return "default"

    def _build_command(
        self, config: RecorderConfig, output_path: Path, window_id: Optional[str] = None
    ) -> list[str]:
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostats",
            "-thread_queue_size",
            "1024",
            "-f",
            "x11grab",
            "-framerate",
            str(config.fps),
        ]

        if window_id:
            cmd.extend(["-window_id", window_id, "-i", self._display()])
        else:
            width, height = self._read_screen_dimensions()
            cmd.extend(["-video_size", f"{width}x{height}", "-i", f"{self._display()}+0,0"])

        if config.record_system_audio:
            audio_source = self._resolve_audio_source(config.audio_source)
            cmd.extend(["-thread_queue_size", "1024", "-f", "pulse", "-i", audio_source])

        cmd.extend(
            [
                "-vcodec",
                "libx264",
                "-preset",
                "ultrafast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
            ]
        )

        if config.record_system_audio:
            cmd.extend(
                [
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "160k",
                    "-ac",
                    "2",
                ]
            )

        cmd.append(str(output_path))

        return cmd

    def start(
        self, config: RecorderConfig, output_path: Path, window_id: Optional[str] = None
    ) -> tuple[bool, str]:
        if self.is_recording:
            return False, "Recording is already running."

        if not self.is_ffmpeg_available():
            return False, "ffmpeg is not installed or not on PATH."

        try:
            cmd = self._build_command(config, output_path, window_id=window_id)
        except Exception as exc:
            return False, str(exc)

        try:
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except OSError as exc:
            self._process = None
            return False, f"Failed to start ffmpeg: {exc}"

        if self._process.poll() is not None:
            code = self._process.returncode
            self._process = None
            return False, f"ffmpeg exited immediately (code {code})."

        return True, ""

    def stop(self) -> tuple[bool, str]:
        if not self._process:
            return False, "No active recording."

        process = self._process
        self._process = None

        if process.poll() is not None:
            return True, ""

        try:
            if process.stdin is not None:
                process.stdin.write("q\n")
                process.stdin.flush()
            try:
                process.wait(timeout=0.2)
                return True, ""
            except subprocess.TimeoutExpired:
                thread = threading.Thread(
                    target=self._finalize_process_background, args=(process,), daemon=True
                )
                thread.start()
                return True, "Finalizing recording..."
        except Exception as exc:
            process.terminate()
            return False, f"Failed to stop ffmpeg cleanly: {exc}"
    @staticmethod
    def _finalize_process_background(process: subprocess.Popen) -> None:
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.terminate()
        except Exception:
            process.terminate()
