"""Windows implementation of active window tracking using pywin32 and psutil."""

import sys
from typing import Optional

from app.tracking.base import BaseWindowTracker, WindowInfo


class WindowsWindowTracker(BaseWindowTracker):
    """Tracks active window on Windows using win32gui and psutil."""

    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("WindowsWindowTracker is only supported on Windows")

    def get_active_window(self) -> Optional[WindowInfo]:
        try:
            import win32gui
            import win32process
            import psutil

            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None

            title = win32gui.GetWindowText(hwnd).strip()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid <= 0:
                return None

            try:
                proc = psutil.Process(pid)
                name = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                name = "Unknown"

            # Return None if both name and title are absent/unknown
            if not name and not title:
                return None

            return {
                "name": name or "Unknown",
                "title": title or name or "Unknown",
            }
        except Exception:
            return None
