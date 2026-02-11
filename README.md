# Simple Screen Recorder (Linux Tray)

Lightweight system tray recorder for Linux Mint using `ffmpeg` + X11.

## Features
- Tray app with one-click start/stop.
- Record full screen or selected window.
- Optional system audio recording (Pulse source).
- Configurable global hotkeys.
- Configurable output directory, FPS, and container.
- Default container is `mkv` (recommended for stable recording).
- Custom tray/menu icons loaded from `src/simple_screen_recorder/assets/`.
- Output naming: `recording-YYYYMMDD-HHMMSS.ext`.

## Requirements (Linux Mint / Ubuntu)
- `uv`
- `ffmpeg`
- `x11-utils` (`xwininfo`, `xdpyinfo`)
- `pulseaudio` or `pipewire-pulse` (for system audio capture)
- `dpkg-deb` / `dpkg-dev` (for `.deb` packaging)

Install system packages:

```bash
sudo apt update
sudo apt install -y ffmpeg x11-utils pulseaudio dpkg-dev
```

## Make Targets

```bash
make run       # run app from Python source via uv
make build     # build one-file binary (PyInstaller)
make package   # build .deb (after build)
make all       # build + package
```

## Build Binary

```bash
./scripts/build-binary.sh
```

Output:
- `dist/simple-screen-recorder`

## Build .deb

```bash
./scripts/package-deb.sh
```

Output:
- `dist/simple-screen-recorder_<version>_<arch>.deb`

## Install .deb

```bash
sudo dpkg -i dist/simple-screen-recorder_*.deb
sudo apt -f install
```

Installed paths:
- binary: `/usr/bin/simple-screen-recorder`
- desktop launcher: `/usr/share/applications/simple-screen-recorder.desktop`

Run:

```bash
simple-screen-recorder
```

Remove:

```bash
sudo apt remove simple-screen-recorder
```

## Settings

Available in tray menu -> `Settings`:
- `Capture mode`: full screen or window click-select.
- `Output directory`
- `Frames per second`
- `Container`: `mkv` or `mp4` (`mkv` default)
- `System audio`: on/off
- `Audio source`: `auto` (recommended), `default`, or explicit source name
- `Hotkey: toggle rec` (default: `<ctrl>+<alt>+r`)
- `Hotkey: stop rec` (default: `<ctrl>+<alt>+s`)

Hotkey format uses `pynput` style, e.g.:
- `<ctrl>+<alt>+r`
- `<shift>+<f8>`

## Audio Notes

- For system audio, `auto` picks the default sink monitor source when available.
- If needed, list sources manually:

```bash
pactl list short sources
```

Then set `Audio source` to a specific monitor, e.g.:
- `alsa_output.pci-0000_00_1f.3.analog-stereo.monitor`

## Custom Icons

The app loads icons from:
- `src/simple_screen_recorder/assets/idle.png`
- `src/simple_screen_recorder/assets/recording.png`
- `src/simple_screen_recorder/assets/stop-recording.png`

If these files are missing, the app falls back to theme/default icons.

## Limitations

- X11 sessions only (`x11grab`).
- Wayland is not supported in current implementation.
