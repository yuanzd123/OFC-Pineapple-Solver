"""
ADB and vision configuration for OFC Pineapple Solver.

Configurable settings for:
  - ADB connection (emulator or real phone)
  - Screen regions for card recognition
  - LLM API settings
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Region:
    """A rectangular region on screen (x, y, width, height)."""
    x: int
    y: int
    w: int
    h: int

    def as_tuple(self) -> tuple[int, int, int, int]:
        """Return (left, upper, right, lower) for PIL crop."""
        return (self.x, self.y, self.x + self.w, self.y + self.h)


@dataclass
class AppLayout:
    """Screen regions for a specific poker app.

    All coordinates are for the app's native resolution.
    Set these by running the calibration tool or manually.
    """
    # Resolution of the screen these coordinates are for
    screen_width: int = 1920
    screen_height: int = 1080

    # Region containing the dealt cards (hand)
    hand_region: Optional[Region] = None

    # Regions for player's board rows
    front_region: Optional[Region] = None
    middle_region: Optional[Region] = None
    back_region: Optional[Region] = None

    # Full-screen region (fallback: send whole screen to LLM)
    @property
    def full_screen(self) -> Region:
        return Region(0, 0, self.screen_width, self.screen_height)


@dataclass
class ADBConfig:
    """ADB connection settings."""
    host: str = "127.0.0.1"
    port: int = 16384  # MuMu default
    adb_path: str = ""  # Auto-detected

    def __post_init__(self):
        if not self.adb_path:
            self.adb_path = _find_adb()

    @property
    def device_address(self) -> str:
        return f"{self.host}:{self.port}"


def _find_adb() -> str:
    """Find ADB binary — check MuMu bundled, then system PATH."""
    import shutil
    # MuMu Player's bundled ADB
    mumu_adb = (
        "/Applications/MuMuPlayer.app/Contents/MacOS/"
        "MuMuEmulator.app/Contents/MacOS/tools/adb"
    )
    if os.path.isfile(mumu_adb):
        return mumu_adb
    # System PATH
    sys_adb = shutil.which("adb")
    if sys_adb:
        return sys_adb
    return "adb"  # Fallback, will error on use


@dataclass
class VisionConfig:
    """LLM vision API settings."""
    provider: str = "ollama"  # ollama (local, free) or openai (cloud, paid)
    model: str = "openbmb/minicpm-o4.5"  # Ollama model name
    api_key: str = ""  # Only needed for OpenAI
    max_tokens: int = 200
    timeout: float = 30.0  # Local models can be slower
    ollama_base_url: str = "http://localhost:11434/v1"

    def get_api_key(self) -> str:
        """Get API key from config or environment (OpenAI only)."""
        if self.api_key:
            return self.api_key
        env_key = os.environ.get("OPENAI_API_KEY", "")
        if not env_key:
            raise ValueError(
                "No API key found. Set OPENAI_API_KEY environment variable "
                "or pass api_key in config."
            )
        return env_key


@dataclass
class Config:
    """Top-level configuration."""
    adb: ADBConfig = field(default_factory=ADBConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    layout: AppLayout = field(default_factory=AppLayout)

    @classmethod
    def default(cls) -> "Config":
        return cls()

    @classmethod
    def for_mumu(cls) -> "Config":
        """Preset for MuMu Player Pro."""
        return cls(adb=ADBConfig(host="127.0.0.1", port=16384))

    @classmethod
    def for_usb_device(cls) -> "Config":
        """Preset for USB-connected real phone (no host/port needed)."""
        return cls(adb=ADBConfig(host="", port=0))
