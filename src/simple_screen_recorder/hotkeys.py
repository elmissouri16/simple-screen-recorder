from __future__ import annotations

from typing import Callable, Optional

try:
    from pynput import keyboard
except Exception:  # pragma: no cover - fallback if dependency unavailable
    keyboard = None


class HotkeyManager:
    def __init__(
        self,
        on_toggle_recording: Callable[[], None],
        on_stop_recording: Callable[[], None],
    ) -> None:
        self.on_toggle_recording = on_toggle_recording
        self.on_stop_recording = on_stop_recording
        self._listener: Optional[object] = None

    @property
    def supported(self) -> bool:
        return keyboard is not None

    def start(self, toggle_hotkey: str, stop_hotkey: str) -> tuple[bool, str]:
        self.stop()

        if not self.supported:
            return False, "Global hotkeys are unavailable (pynput not installed)."

        try:
            listener = keyboard.GlobalHotKeys(
                {
                    toggle_hotkey: self.on_toggle_recording,
                    stop_hotkey: self.on_stop_recording,
                }
            )
            listener.start()
            self._listener = listener
            return True, ""
        except Exception as exc:
            self._listener = None
            return False, f"Failed to register hotkeys: {exc}"

    def stop(self) -> None:
        if self._listener is None:
            return
        try:
            self._listener.stop()
        except Exception:
            pass
        self._listener = None

