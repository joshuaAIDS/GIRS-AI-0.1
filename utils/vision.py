"""
Screen Capture and Image Optimization Utilities for IGIRS AI Multimodal Vision.
"""
import io
import os
import base64
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image

import config

logger = logging.getLogger("IGIRS.Vision")

def capture_screen_to_pil() -> Optional[Image.Image]:
    """Tries multiple methods to capture active Windows screen."""
    # Method 1: PIL ImageGrab
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        if img:
            return img
    except Exception as e:
        logger.debug(f"PIL ImageGrab error: {e}")

    # Method 2: mss
    try:
        from mss import MSS
        with MSS() as sct:
            mon = sct.monitors[1]
            shot = sct.grab(mon)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            if img:
                return img
    except Exception as e:
        logger.debug(f"MSS error: {e}")

    # Method 3: PowerShell .NET System.Drawing fallback
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
            return img
    except Exception as e:
        logger.debug(f"PowerShell screen fallback error: {e}")

    return None

def capture_screen_base64(max_width: int = 1280) -> Optional[str]:
    """
    Captures the screen, downscales to optimal resolution, and returns JPEG base64 string.
    """
    img = capture_screen_to_pil()
    if not img:
        return None

    # Convert to RGB if needed
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Downscale maintaining aspect ratio to minimize latency
    if img.width > max_width:
        ratio = max_width / float(img.width)
        new_height = int(float(img.height) * float(ratio))
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

    # Save to compressed JPEG in memory
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    raw_bytes = buf.getvalue()
    b64_str = base64.b64encode(raw_bytes).decode("utf-8")
    return b64_str
