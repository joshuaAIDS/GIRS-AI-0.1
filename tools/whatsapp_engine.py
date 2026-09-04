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
from tools.window_utils import (
    find_window_by_keywords,
    bring_window_to_foreground,
    simulate_enter,
    click_whatsapp_send_button
)

logger = logging.getLogger("IGIRS.WhatsAppEngine")

class WhatsAppEngine:
    def __init__(self, contacts_manager: Optional[ContactsManager] = None):
        self.contacts = contacts_manager or ContactsManager()
        self.sent_history = []

    def _simulate_enter_press(self, delay: float = 3.0, is_web: bool = False):
        """
        Multi-stage automated window focus and dual-dispatch (Enter + Send Button Click) for WhatsApp.
        Finds WhatsApp Desktop or Browser window, brings it to foreground, presses Enter,
        and clicks the green Send button if focus was outside the input field.
        Runs safely in a separate daemon thread so it never blocks the main assistant event loop.
        """
        def _worker():
            # Initial wait for WhatsApp Desktop / Browser to launch & populate chat
            time.sleep(delay)

            title_kws = ["WhatsApp", "WhatsApp Web"]
            proc_kws = ["whatsapp"]

            # Multi-pulse sequence (up to 3 attempts with safe delay between)
            for attempt in range(1, 4):
                try:
                    hwnd = find_window_by_keywords(title_kws, proc_kws)
                    if hwnd:
                        bring_window_to_foreground(hwnd)
                        time.sleep(0.25)
                        # 1. Primary: Press Enter
                        simulate_enter()
                        logger.info(f"⚡ Hands-Free WhatsApp: Auto-send ENTER triggered (Attempt {attempt}/3) on hwnd {hwnd}.")
                        time.sleep(0.3)

                        # 2. Secondary: Click green send button if input field was not focused
                        clicked = click_whatsapp_send_button(hwnd)
                        if clicked:
                            logger.info(f"⚡ Hands-Free WhatsApp: Green Send button clicked (Attempt {attempt}/3).")
                    else:
                        logger.debug(f"WhatsApp window not found on attempt {attempt}")
                except Exception as e:
                    logger.debug(f"WhatsApp auto-send error on attempt {attempt}: {e}")

                if attempt < 3:
                    time.sleep(1.5)

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
            is_web = (mode_used == "web_fallback")
            delay = 3.0 if mode_used == "native_desktop" else 5.0
            self._simulate_enter_press(delay=delay, is_web=is_web)

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
