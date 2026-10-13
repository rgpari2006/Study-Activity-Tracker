"""Abstract base class for OS-specific active window tracking."""

from abc import ABC, abstractmethod
from typing import Optional, TypedDict


class WindowInfo(TypedDict):
    name: str
    title: str


class BaseWindowTracker(ABC):
    """Abstract interface for querying foreground window and process information."""

    @abstractmethod
    def get_active_window(self) -> Optional[WindowInfo]:
        """Return information about the currently active foreground window.

        Returns:
            {"name": "app.exe", "title": "Window title"} or None if undetected.
        """
        pass
