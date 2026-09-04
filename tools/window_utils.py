"""
Window Focusing and Foreground Keystroke Dispatch Utilities for IGIRS AI.
Handles Windows focus-stealing locks, input desktop attachment, and hands-free dispatch.
"""
import sys
import time
import logging
from typing import List, Optional

logger = logging.getLogger("IGIRS.WindowUtils")

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes
    import psutil

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    # Virtual Key Codes
    VK_RETURN = 0x0D
    VK_CONTROL = 0x11
    VK_MENU = 0x12  # Alt key
    VK_S = 0x53
    KEYEVENTF_KEYUP = 0x0002

def find_window_by_keywords(
    title_keywords: List[str],
    process_keywords: Optional[List[str]] = None
) -> Optional[int]:
    """
    Finds the first visible top-level window matching either title keywords or process keywords.
    Attaches to the active user desktop to safely inspect windows in modern Windows 10/11 environments.
    """
    if sys.platform != "win32":
        return None

    try:
        from utils.vision import attach_to_input_desktop
    except ImportError:
        from contextlib import contextmanager
        @contextmanager
        def attach_to_input_desktop():
            yield

    title_kws = [k.lower().strip() for k in title_keywords if k and k.strip()]
    proc_kws = [p.lower().strip() for p in (process_keywords or []) if p and p.strip()]

    matched_hwnd = None

    with attach_to_input_desktop():
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        def enum_callback(hwnd, lParam):
            nonlocal matched_hwnd
            if not user32.IsWindowVisible(hwnd):
                return True

            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            proc_name = ""
            try:
                proc_name = psutil.Process(pid.value).name().lower()
            except Exception:
                pass

            length = user32.GetWindowTextLengthW(hwnd)
            title = ""
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value.lower()

            # 1. Match by window title keywords
            if title_kws and any(tk in title for tk in title_kws):
                matched_hwnd = hwnd
                return False  # stop enumeration

            # 2. Match by process name keywords
            if proc_kws and any(pk in proc_name for pk in proc_kws):
                # Filter out invisible or auxiliary tooltips/status windows
                if length > 0 or any(k in proc_name for k in ["olk", "whatsapp", "mail"]):
                    matched_hwnd = hwnd
                    return False

            return True

        user32.EnumWindows(EnumWindowsProc(enum_callback), 0)

    return matched_hwnd

def bring_window_to_foreground(hwnd: int) -> bool:
    """
    Forces a window to the active foreground on Windows, bypassing Windows 10/11 LockSetForegroundWindow.
    Restores the window if minimized and attaches thread input to guarantee focus transfer.
    """
    if sys.platform != "win32" or not hwnd:
        return False

    try:
        from utils.vision import attach_to_input_desktop
    except ImportError:
        from contextlib import contextmanager
        @contextmanager
        def attach_to_input_desktop():
            yield

    with attach_to_input_desktop():
        if not user32.IsWindow(hwnd):
            return False

        SW_RESTORE = 9
        SW_SHOW = 5
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        else:
            user32.ShowWindow(hwnd, SW_SHOW)

        cur_thread = kernel32.GetCurrentThreadId()
        fg_hwnd = user32.GetForegroundWindow()
        fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0

        attached = False
        if fg_thread and fg_thread != cur_thread:
            try:
                attached = bool(user32.AttachThreadInput(cur_thread, fg_thread, True))
            except Exception:
                attached = False

        user32.BringWindowToTop(hwnd)

        # Alt-key trick: Windows allows foreground change if Alt key was pressed
        user32.keybd_event(VK_MENU, 0, 0, 0)
        user32.SetForegroundWindow(hwnd)
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)

        user32.SetActiveWindow(hwnd)
        user32.SetFocus(hwnd)

        if attached:
            try:
                user32.AttachThreadInput(cur_thread, fg_thread, False)
            except Exception:
                pass

        time.sleep(0.15)
        return True

def simulate_enter():
    """Simulates pressing the Enter key on the active window using PyAutoGUI with Win32 fallback."""
    try:
        import pyautogui
        pyautogui.press("enter")
        return True
    except Exception as e:
        logger.debug(f"PyAutoGUI enter failed: {e}. Using Win32 keybd_event.")
        if sys.platform == "win32":
            user32.keybd_event(VK_RETURN, 0, 0, 0)
            time.sleep(0.05)
            user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
            return True
    return False

def simulate_mail_send():
    """
    Simulates sending an email in Outlook / Windows Mail / Thunderbird.
    Triggers Ctrl + Enter (universal shortcut for New Outlook, classic Outlook, and Mail).
    """
    sent = False
    try:
        import pyautogui
        pyautogui.hotkey("ctrl", "enter")
        sent = True
    except Exception as e:
        logger.debug(f"PyAutoGUI ctrl+enter failed: {e}")

    if sys.platform == "win32":
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_RETURN, 0, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        sent = True

    return sent

def simulate_outlook_alt_s():
    """Triggers Alt + S for classic Outlook Send button."""
    try:
        import pyautogui
        pyautogui.hotkey("alt", "s")
        return True
    except Exception:
        if sys.platform == "win32":
            user32.keybd_event(VK_MENU, 0, 0, 0)
            user32.keybd_event(VK_S, 0, 0, 0)
            time.sleep(0.05)
            user32.keybd_event(VK_S, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
            return True
    return False
