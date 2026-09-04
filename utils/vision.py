"""
Screen Capture and Image Optimization Utilities for IGIRS AI Multimodal Vision.
Supports full-screen capture, active window focus, and seamless desktop station attachment.
"""
import io
import os
import sys
import base64
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from contextlib import contextmanager
from PIL import Image

import config

logger = logging.getLogger("IGIRS.Vision")

PREVIEW_PATH = config.TEMP_AUDIO_DIR / "screen_preview.jpg"

@contextmanager
def attach_to_input_desktop():
    """
    On Windows, ensures the calling thread is attached to the active user desktop ('Default')
    instead of an isolated sandbox, service, or virtual desktop station.
    """
    h_input = None
    old_desk = None
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            old_desk = user32.GetThreadDesktop(kernel32.GetCurrentThreadId())
            h_input = user32.OpenInputDesktop(0, False, 0x01FF)
            if h_input:
                user32.SetThreadDesktop(h_input)
        except Exception as e:
            logger.debug(f"attach_to_input_desktop error: {e}")
    try:
        yield
    finally:
        if sys.platform == "win32" and h_input:
            try:
                if old_desk:
                    user32.SetThreadDesktop(old_desk)
                user32.CloseDesktop(h_input)
            except Exception:
                pass

def get_active_window_rect() -> Optional[Tuple[int, int, int, int]]:
    """Returns (left, top, right, bottom) of active foreground window on Windows."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        rect = wintypes.RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            # Validate bounding box
            if rect.right > rect.left and rect.bottom > rect.top:
                return (rect.left, rect.top, rect.right, rect.bottom)
    except Exception as e:
        logger.debug(f"Could not get foreground window rect: {e}")
    return None

def capture_screen_to_pil(focus_window: bool = False) -> Optional[Image.Image]:
    """
    Captures the active Windows screen or foreground window cleanly.
    Tries PIL ImageGrab with input desktop attachment, then MSS, then PowerShell GDI.
    """
    img = None

    with attach_to_input_desktop():
        # Method 1: PIL ImageGrab
        try:
            from PIL import ImageGrab
            grabbed = ImageGrab.grab(all_screens=True)
            if grabbed:
                img = grabbed
        except Exception as e:
            logger.debug(f"PIL ImageGrab error: {e}")

        # Method 2: mss
        if img is None:
            try:
                import mss
                with mss.MSS() as sct:
                    # Monitor 1 is primary monitor; monitor 0 is all monitors bounding box
                    mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                    shot = sct.grab(mon)
                    grabbed = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                    if grabbed:
                        img = grabbed
            except Exception as e:
                logger.debug(f"MSS capture error: {e}")

        # Method 3: PowerShell .NET System.Drawing fallback
        if img is None:
            try:
                temp_file = config.TEMP_AUDIO_DIR / "temp_screen_fallback.jpg"
                ps_script = f"""
                Add-Type -AssemblyName System.Windows.Forms,System.Drawing
                $screen = [System.Windows.Forms.Screen]::PrimaryScreen
                $bitmap = New-Object System.Drawing.Bitmap($screen.Bounds.Width, $screen.Bounds.Height)
                $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
                $graphics.CopyFromScreen($screen.Bounds.Location, [System.Drawing.Point]::Empty, $screen.Bounds.Size)
                $bitmap.Save('{str(temp_file).replace(chr(92), "/")}', [System.Drawing.Imaging.ImageFormat]::Jpeg)
                $graphics.Dispose()
                $bitmap.Dispose()
                """
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True, timeout=8)
                if temp_file.exists() and temp_file.stat().st_size > 0:
                    with Image.open(temp_file) as f_img:
                        img = f_img.copy()
                    temp_file.unlink(missing_ok=True)
            except Exception as e:
                logger.debug(f"PowerShell screen fallback error: {e}")

    if not img:
        return None

    # Convert mode to RGB if needed
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # If focus_window requested, crop to active foreground window
    if focus_window:
        rect = get_active_window_rect()
        if rect:
            left, top, right, bottom = rect
            # Clamp to image bounds
            left = max(0, min(img.width - 50, left))
            top = max(0, min(img.height - 50, top))
            right = min(img.width, max(left + 50, right))
            bottom = min(img.height, max(top + 50, bottom))
            if right > left and bottom > top:
                img = img.crop((left, top, right, bottom))

    # Save a cached preview for the desktop GUI HUD
    try:
        PREVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
        preview_img = img.copy()
        if preview_img.width > 960:
            p_ratio = 960 / float(preview_img.width)
            p_h = int(float(preview_img.height) * p_ratio)
            preview_img = preview_img.resize((960, p_h), Image.Resampling.LANCZOS)
        preview_img.save(PREVIEW_PATH, format="JPEG", quality=82)
    except Exception as e:
        logger.debug(f"Could not save preview thumbnail: {e}")

    return img

def capture_screen_base64(max_width: int = 1280, focus_window: bool = False) -> Optional[str]:
    """
    Captures the screen, downscales to optimal vision resolution, and returns JPEG base64 string.
    """
    img = capture_screen_to_pil(focus_window=focus_window)
    if not img:
        return None

    # Downscale maintaining aspect ratio to minimize latency
    if img.width > max_width:
        ratio = max_width / float(img.width)
        new_height = int(float(img.height) * float(ratio))
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

    # Save to compressed JPEG in memory
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82)
    raw_bytes = buf.getvalue()
    b64_str = base64.b64encode(raw_bytes).decode("utf-8")
    return b64_str

def get_screen_preview_path() -> Optional[Path]:
    """Returns Path to the most recently captured screen preview if available."""
    if PREVIEW_PATH.exists() and PREVIEW_PATH.stat().st_size > 0:
        return PREVIEW_PATH
    return None
