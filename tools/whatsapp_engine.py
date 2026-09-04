"""
Hands-Free WhatsApp Automation Engine for IGIRS AI.
Supports both Windows WhatsApp Desktop native URI protocols and WhatsApp Web fallback,
with contact name/nickname resolution and automated Enter-key dispatch.
"""
import os
import re
import time
import ctypes
import logging
import threading
import webbrowser
import urllib.parse
from typing import Dict, Any, Optional
from pathlib import Path
from tools.contacts_manager import ContactsManager

logger = logging.getLogger("IGIRS.WhatsAppEngine")

VK_RETURN = 0x0D
KEYEVENTF_KEYUP = 0x0002

class WhatsAppEngine:
    def __init__(self, contacts_manager: Optional[ContactsManager] = None):
        self.contacts = contacts_manager or ContactsManager()
        self.sent_history = []

    def _simulate_enter_press(self, delay: float = 2.5):
        """
        Waits for WhatsApp Desktop / Browser to launch and focus, then triggers Enter key.
        Runs safely in a separate daemon thread so it never blocks the main assistant event loop.
        """
        def _worker():
            try:
                time.sleep(delay)
                # Primary method: Windows API keybd_event
                ctypes.windll.user32.keybd_event(VK_RETURN, 0, 0, 0)
                time.sleep(0.05)
                ctypes.windll.user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
                logger.info("⚡ Hands-Free WhatsApp: Auto-send ENTER key pressed.")
            except Exception as e:
                # Secondary fallback: PyAutoGUI if installed
                try:
                    import pyautogui
                    pyautogui.press("enter")
                    logger.info("⚡ Hands-Free WhatsApp: Auto-send via PyAutoGUI executed.")
                except Exception as ex:
                    logger.debug(f"Could not simulate Enter key for WhatsApp: {e} / {ex}")

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def send_message(
        self,
        recipient: str,
        message: str,
        auto_send: bool = True
    ) -> Dict[str, Any]:
        """
        Dispatches a WhatsApp message to a contact name, nickname, or direct phone number.
        """
        message = message.strip()
        if not message:
            return {"status": "error", "message": "Cannot send an empty WhatsApp message."}

        # 1. Resolve Recipient
        contact = self.contacts.get_contact(recipient)
        rec_name = recipient
        rec_phone = ""

        if contact:
            rec_name = contact.get("name", recipient)
            rec_phone = contact.get("phone", "")
        else:
            # Check if input itself looks like a phone number
            digits_only = re.sub(r"[^\d+]", "", recipient)
            if len(digits_only) >= 7:
                rec_phone = self.contacts.normalize_phone(recipient)
                rec_name = rec_phone
            else:
                return {
                    "status": "error",
                    "message": f"Could not find contact '{recipient}' in your contacts book. Please provide a valid phone number or add them to your contacts."
                }

        if not rec_phone:
            return {
                "status": "error",
                "message": f"Contact '{rec_name}' does not have a saved phone number."
            }

        # Normalize phone for WhatsApp URL (plain digits with country code, no '+')
        phone_digits = re.sub(r"\D", "", rec_phone)
        encoded_text = urllib.parse.quote(message)

        native_uri = f"whatsapp://send?phone={phone_digits}&text={encoded_text}"
        web_url = f"https://web.whatsapp.com/send?phone={phone_digits}&text={encoded_text}"

        mode_used = "native_desktop"
        opened_successfully = False

        # 2. Try Native Desktop Protocol (Windows WhatsApp App)
        try:
            os.startfile(native_uri)
            opened_successfully = True
            logger.info(f"Launched WhatsApp via native protocol for {rec_name} ({phone_digits})")
        except Exception as e:
            logger.debug(f"Native WhatsApp protocol not registered or failed: {e}. Falling back to Web.")
            mode_used = "web_fallback"
            try:
                webbrowser.open(web_url)
                opened_successfully = True
                logger.info(f"Launched WhatsApp Web in default browser for {rec_name} ({phone_digits})")
            except Exception as ex:
                logger.error(f"Failed to open WhatsApp Web: {ex}")
                return {"status": "error", "message": f"Failed to open WhatsApp: {ex}"}

        # 3. Hands-Free Auto-Send Enter key
        if auto_send and opened_successfully:
            # Give slightly longer delay for web browser vs native app
            delay = 2.5 if mode_used == "native_desktop" else 4.0
            self._simulate_enter_press(delay=delay)

        # 4. Record sent log
        dispatch_record = {
            "timestamp": time.strftime("%Y-%m-%d %I:%M %p"),
            "recipient_name": rec_name,
            "recipient_phone": rec_phone,
            "message": message,
            "mode": mode_used,
            "auto_send": auto_send
        }
        self.sent_history.append(dispatch_record)

        preview = (message[:75] + "...") if len(message) > 75 else message
        summary = f"Dispatched WhatsApp to {rec_name} ({rec_phone}): \"{preview}\""
        if auto_send:
            summary += " with hands-free auto-send."

        return {
            "status": "success",
            "recipient_name": rec_name,
            "recipient_phone": rec_phone,
            "message": message,
            "mode": mode_used,
            "auto_send": auto_send,
            "summary": summary
        }
