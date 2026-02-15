"""
ADB screen capture module.

Captures screenshots from Android device via ADB.
Supports both emulator (MuMu) and real phone (USB).
"""

from __future__ import annotations

import io
import subprocess
import time
from pathlib import Path
from typing import Optional

from PIL import Image

from adb.config import ADBConfig, Config, Region


def check_adb(config: ADBConfig | None = None) -> tuple[bool, str]:
    """Check if ADB is available and device is connected.

    Returns (success, message).
    """
    cfg = config or ADBConfig()
    try:
        # First check if adb is installed
        result = subprocess.run(
            [cfg.adb_path, "version"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return False, f"ADB not found at '{cfg.adb_path}'"

        # Connect to device if host is specified (emulator)
        if cfg.host and cfg.port:
            result = subprocess.run(
                [cfg.adb_path, "connect", cfg.device_address],
                capture_output=True, text=True, timeout=5,
            )

        # Check for connected devices
        result = subprocess.run(
            [cfg.adb_path, "devices"],
            capture_output=True, text=True, timeout=5,
        )
        lines = result.stdout.strip().split("\n")[1:]  # Skip header
        devices = [l for l in lines if l.strip() and "device" in l]

        if not devices:
            return False, "No devices connected. Is the emulator running?"

        return True, f"Connected: {devices[0].split()[0]}"

    except FileNotFoundError:
        return False, (
            "ADB not found. Install with: brew install android-platform-tools"
        )
    except subprocess.TimeoutExpired:
        return False, "ADB command timed out"
    except Exception as e:
        return False, f"ADB error: {e}"


def capture_screenshot(config: ADBConfig | None = None) -> Image.Image:
    """Capture a screenshot from the connected Android device.

    Uses `adb exec-out screencap -p` for fastest transfer (raw PNG pipe).
    Returns a PIL Image.
    """
    cfg = config or ADBConfig()

    args = [cfg.adb_path]
    if cfg.host and cfg.port:
        args.extend(["-s", cfg.device_address])
    args.extend(["exec-out", "screencap", "-p"])

    start = time.time()
    result = subprocess.run(
        args,
        capture_output=True,
        timeout=10,
    )

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"screencap failed: {stderr}")

    if not result.stdout:
        raise RuntimeError("screencap returned empty data")

    elapsed = time.time() - start
    img = Image.open(io.BytesIO(result.stdout))

    # Print timing for debugging
    print(f"  📸 Screenshot: {img.size[0]}x{img.size[1]} in {elapsed:.2f}s")
    return img


def crop_region(img: Image.Image, region: Region) -> Image.Image:
    """Crop a region from a screenshot."""
    return img.crop(region.as_tuple())


def save_screenshot(img: Image.Image, path: str | Path) -> None:
    """Save a screenshot to disk (for debugging/calibration)."""
    img.save(str(path))
    print(f"  💾 Saved: {path}")


def get_screen_resolution(config: ADBConfig | None = None) -> tuple[int, int]:
    """Get the device's screen resolution via ADB."""
    cfg = config or ADBConfig()

    args = [cfg.adb_path]
    if cfg.host and cfg.port:
        args.extend(["-s", cfg.device_address])
    args.extend(["shell", "wm", "size"])

    result = subprocess.run(
        args,
        capture_output=True, text=True, timeout=5,
    )

    if result.returncode != 0:
        raise RuntimeError("Failed to get screen resolution")

    # Parse "Physical size: 1920x1080"
    for line in result.stdout.strip().split("\n"):
        if "size" in line.lower():
            parts = line.split(":")[-1].strip().split("x")
            return int(parts[0]), int(parts[1])

    raise RuntimeError(f"Could not parse resolution from: {result.stdout}")
