"""
System Hardware & Windows Controls for IGIRS AI.
Provides master volume control, screen brightness, screenshot capture,
workstation locking, and window management.
"""
import os
import ctypes
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("IGIRS.SystemControls")

def _get_audio_endpoint():
    """Helper to retrieve the Windows master audio endpoint volume interface."""
    import pycaw.pycaw as pycaw
    device = pycaw.AudioUtilities.GetSpeakers()
    if hasattr(device, "EndpointVolume"):
        return device.EndpointVolume
    # Legacy pycaw fallback
    from comtypes import CLSCTX_ALL
    interface = device.Activate(pycaw.IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return interface.QueryInterface(pycaw.IAudioEndpointVolume)

def get_volume() -> Dict[str, Any]:
    """Gets current master volume level and mute status."""
    try:
        volume = _get_audio_endpoint()
        current_scalar = volume.GetMasterVolumeLevelScalar()
        level_percent = int(round(current_scalar * 100))
        is_muted = bool(volume.GetMute())
        return {
            "success": True,
            "volume_percent": level_percent,
            "is_muted": is_muted,
            "message": f"Volume is at {level_percent}% ({'Muted' if is_muted else 'Unmuted'})."
        }
    except Exception as e:
        logger.error(f"Failed to get system volume: {e}")
        return {"success": False, "error": str(e), "message": f"Could not read audio volume: {e}"}

def set_volume(level_percent: int) -> Dict[str, Any]:
    """Sets master volume to an exact percentage (0 - 100)."""
    try:
        level_percent = max(0, min(100, int(level_percent)))
        volume = _get_audio_endpoint()
        # If muted and setting volume > 0, unmute automatically
        if level_percent > 0 and volume.GetMute():
            volume.SetMute(0, None)
        scalar = level_percent / 100.0
        volume.SetMasterVolumeLevelScalar(scalar, None)
        return {
            "success": True,
            "volume_percent": level_percent,
            "message": f"System volume set to {level_percent}%."
        }
    except Exception as e:
        logger.error(f"Failed to set volume to {level_percent}%: {e}")
        return {"success": False, "error": str(e), "message": f"Failed to set volume: {e}"}

def change_volume_relative(delta_percent: int) -> Dict[str, Any]:
    """Increases or decreases master volume by delta_percent."""
    try:
        current = get_volume()
        if not current.get("success"):
            return current
        current_level = current["volume_percent"]
        new_level = max(0, min(100, current_level + int(delta_percent)))
        return set_volume(new_level)
    except Exception as e:
        logger.error(f"Failed to adjust volume by {delta_percent}%: {e}")
        return {"success": False, "error": str(e), "message": f"Failed to adjust volume: {e}"}

def mute_volume(mute: bool = True) -> Dict[str, Any]:
    """Mutes or unmutes system audio."""
    try:
        volume = _get_audio_endpoint()
        volume.SetMute(1 if mute else 0, None)
        action_str = "muted" if mute else "unmuted"
        return {
            "success": True,
            "is_muted": mute,
            "message": f"System audio has been {action_str}."
        }
    except Exception as e:
        logger.error(f"Failed to set mute={mute}: {e}")
        return {"success": False, "error": str(e), "message": f"Failed to mute audio: {e}"}

def get_brightness() -> Dict[str, Any]:
    """Queries current screen brightness percentage."""
    try:
        import screen_brightness_control as sbc
        levels = sbc.get_brightness()
        val = levels[0] if isinstance(levels, list) and len(levels) > 0 else levels
        return {
            "success": True,
            "brightness_percent": int(val),
            "message": f"Screen brightness is currently at {int(val)}%."
        }
    except Exception as e:
        logger.error(f"Failed to query brightness: {e}")
        return {"success": False, "error": str(e), "message": f"Could not read screen brightness: {e}"}

def set_brightness(level_percent: int) -> Dict[str, Any]:
    """Sets screen brightness to an exact percentage (0 - 100)."""
    try:
        level_percent = max(0, min(100, int(level_percent)))
        import screen_brightness_control as sbc
        sbc.set_brightness(level_percent)
        return {
            "success": True,
            "brightness_percent": level_percent,
            "message": f"Screen brightness adjusted to {level_percent}%."
        }
    except Exception as e:
        logger.error(f"Failed to set brightness to {level_percent}%: {e}")
        return {"success": False, "error": str(e), "message": f"Could not adjust brightness: {e}"}

def take_screenshot(filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Captures the primary monitor and saves to Pictures/Screenshots.
    Uses multi-method capture (PIL ImageGrab, mss, PowerShell) for maximum reliability.
    """
    try:
        screenshots_dir = Path.home() / "Pictures" / "Screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        if not filename or not filename.strip():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        elif not filename.lower().endswith((".png", ".jpg", ".jpeg")):
            filename = f"{filename}.png"

        target_path = screenshots_dir / filename

        shot = None
        try:
            from utils.vision import capture_screen_to_pil
            shot = capture_screen_to_pil()
        except Exception:
            pass

        if not shot:
            try:
                import pyautogui
                pyautogui.FAILSAFE = False
                shot = pyautogui.screenshot()
            except Exception:
                pass

        if not shot:
            return {"success": False, "message": "Failed to capture screen with all capture methods."}

        shot.save(str(target_path))

        return {
            "success": True,
            "file_path": str(target_path),
            "filename": filename,
            "message": f"Screenshot captured and saved to {target_path.name} in your Screenshots folder."
        }
    except Exception as e:
        logger.error(f"Failed to take screenshot: {e}")
        return {"success": False, "error": str(e), "message": f"Failed to capture screenshot: {e}"}

def lock_workstation() -> Dict[str, Any]:
    """Locks the Windows computer safely."""
    try:
        user32 = ctypes.windll.user32
        locked = user32.LockWorkStation()
        if locked != 0:
            return {"success": True, "message": "Workstation locked successfully."}
        return {"success": False, "message": "Failed to lock workstation."}
    except Exception as e:
        logger.error(f"Failed to lock workstation: {e}")
        return {"success": False, "error": str(e), "message": f"Error locking workstation: {e}"}

def minimize_all_windows() -> Dict[str, Any]:
    """Minimizes all windows to show the desktop via Windows Shell COM and keybd_event."""
    # Method 1: Windows Shell.Application COM object (cleanest, immune to mouse position)
    try:
        import comtypes.client
        shell = comtypes.client.CreateObject("Shell.Application")
        shell.MinimizeAll()
        return {"success": True, "message": "All windows minimized to desktop."}
    except Exception as e:
        logger.debug(f"Shell.Application MinimizeAll error: {e}")

    # Method 2: Native Windows user32 keybd_event (Win + D)
    try:
        VK_LWIN = 0x5B
        VK_D = 0x44
        KEYEVENTF_KEYUP = 0x0002
        user32 = ctypes.windll.user32
        user32.keybd_event(VK_LWIN, 0, 0, 0)
        user32.keybd_event(VK_D, 0, 0, 0)
        user32.keybd_event(VK_D, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        return {"success": True, "message": "All windows minimized to desktop."}
    except Exception as e:
        logger.debug(f"keybd_event error: {e}")

    # Method 3: PowerShell COM fallback
    try:
        import subprocess
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "(New-Object -ComObject Shell.Application).MinimizeAll()"],
            capture_output=True,
            timeout=3
        )
        return {"success": True, "message": "All windows minimized to desktop."}
    except Exception as e:
        logger.error(f"Failed to minimize windows: {e}")
        return {"success": False, "error": str(e), "message": f"Failed to minimize windows: {e}"}
