from __future__ import annotations

import re
import subprocess
from typing import Optional


def select_window_id() -> Optional[str]:
    """Open xwininfo and return selected X11 window id, e.g. 0x3600007."""
    result = subprocess.run(["xwininfo"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None

    match = re.search(r"xwininfo:\s+Window id:\s+(\S+)", result.stdout)
    if not match:
        return None

    return match.group(1)

