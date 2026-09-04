import os
import subprocess
from pathlib import Path
from PIL import Image

def capture_screen(output_path: Path) -> bool:
    """Tries multiple methods to capture screen on Windows."""
    # Method 1: PIL ImageGrab
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        img.save(output_path, "JPEG", quality=85)
        if output_path.exists() and output_path.stat().st_size > 0:
            return True
    except Exception:
        pass

    # Method 2: mss
    try:
        from mss import MSS
        with MSS() as sct:
            mon = sct.monitors[1]
            shot = sct.grab(mon)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            img.save(output_path, "JPEG", quality=85)
            if output_path.exists() and output_path.stat().st_size > 0:
                return True
    except Exception:
        pass

    # Method 3: PowerShell .NET System.Drawing fallback
    try:
        ps_script = f"""
        Add-Type -AssemblyName System.Windows.Forms,System.Drawing
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen
        $bitmap = New-Object System.Drawing.Bitmap($screen.Bounds.Width, $screen.Bounds.Height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen($screen.Bounds.Location, [System.Drawing.Point]::Empty, $screen.Bounds.Size)
        $bitmap.Save('{str(output_path).replace(chr(92), "/")}', [System.Drawing.Imaging.ImageFormat]::Jpeg)
        $graphics.Dispose()
        $bitmap.Dispose()
        """
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True, timeout=8)
        if output_path.exists() and output_path.stat().st_size > 0:
            return True
    except Exception:
        pass

    return False

if __name__ == "__main__":
    out = Path("temp_audio/test_screen.jpg")
    success = capture_screen(out)
    print("Screen capture success:", success, "File exists:", out.exists())
