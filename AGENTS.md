# Repository Guidelines

## Project Structure & Module Organization
- Python package code lives in `src/simple_screen_recorder/`.
- Entry point: `main.py` (Qt application bootstrap).
- `tray_app.py` handles tray UI, settings dialog, and app flow.
- `ffmpeg_backend.py` handles ffmpeg process lifecycle and capture command building.
- `config.py` persists settings in `~/.config/simple-screen-recorder/config.json`.
- `hotkeys.py` and `window_select.py` handle global shortcuts and X11 window picking.
- Static assets are in `src/simple_screen_recorder/assets/`.
- Build and packaging helpers are in `scripts/`; Debian metadata is in `packaging/`.
- Generated artifacts go to `build/` and `dist/`.

## Build, Test, and Development Commands
- `make run`: run from source via `uv` (`scripts/run-python.sh`).
- `make build`: build one-file binary with PyInstaller into `dist/simple-screen-recorder`.
- `make package`: create `.deb` package from the built binary.
- `make all`: run build + package.
- Direct script usage is also valid, for example `./scripts/build-binary.sh`.

## Coding Style & Naming Conventions
- Follow existing Python style: 4-space indentation, type hints, and `from __future__ import annotations` in modules.
- Use `snake_case` for functions/variables, `PascalCase` for classes, and descriptive constants (e.g., `CAPTURE_MODE_FULL`).
- Keep modules focused: UI logic in `tray_app.py`, recorder process logic in `ffmpeg_backend.py`.
- Prefer small, explicit methods and user-facing error messages.

## Testing Guidelines
- No automated test suite is committed yet.
- Before opening a PR, run a manual smoke test:
  1. `make run`
  2. Start/stop full-screen recording
  3. Test window-select mode
  4. If enabled, verify system audio capture
- Verify artifacts when relevant: run `make build` (and `make package` for packaging changes).

## Commit & Pull Request Guidelines
- Current history uses short, imperative, lowercase commit subjects (e.g., `clean unused files`, `init`). Keep subjects concise and specific.
- Prefer one logical change per commit.
- PRs should include what changed and why.
- PRs should include manual verification steps and results.
- Link related issues when applicable.
- Add UI screenshots only when visible behavior changes.

## Platform Notes
- This project targets Linux X11 capture (`x11grab`). Wayland is currently not supported.
- Ensure runtime dependencies (`ffmpeg`, `x11-utils`, Pulse/PipeWire compatibility) are available when testing.
