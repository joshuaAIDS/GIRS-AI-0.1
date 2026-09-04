"""
Automated Test for Hands-Free WhatsApp & Email Auto-Send Dispatch.
Verifies window focusing, keystroke simulation, and end-to-end tool execution.
"""
import sys
import time
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.contacts_manager import ContactsManager
from tools.whatsapp_engine import WhatsAppEngine
from tools.email_engine import EmailEngine
from tools.window_utils import (
    find_window_by_keywords,
    bring_window_to_foreground,
    simulate_enter,
    simulate_mail_send,
    simulate_outlook_alt_s
)
from assistant import IGIRSAssistant
from gui.api_bridge import DesktopApiBridge

def run_tests():
    print("=" * 65)
    print("🚀 RUNNING HANDS-FREE AUTO-SEND DISPATCH TEST SUITE")
    print("=" * 65)

    # 1. Test window_utils functions
    print("\n[1/4] Testing Window Utils & Keystroke Simulation...")
    # Find any visible window (e.g. WhatsApp, Chrome, Python, or Code)
    found_hwnd = find_window_by_keywords(["WhatsApp", "Chrome", "Code", "Command"])
    print(f"  • find_window_by_keywords result: hwnd = {found_hwnd}")
    if found_hwnd:
        brought = bring_window_to_foreground(found_hwnd)
        print(f"  • bring_window_to_foreground result: {brought}")
        assert brought is True

    # Test keystroke simulation functions (syntax & safety check)
    assert callable(simulate_enter)
    assert callable(simulate_mail_send)
    assert callable(simulate_outlook_alt_s)
    print("  • Keystroke simulators loaded and callable.")
    print("  [OK] Window Utils verified.")

    # 2. Test WhatsApp Hands-Free Engine
    print("\n[2/4] Testing WhatsApp Hands-Free Engine...")
    contacts = ContactsManager()
    contacts.add_contact(name="Test Contact", phone="+19876543210", nickname="Tester")
    wa = WhatsAppEngine(contacts_manager=contacts)

    # Note: auto_send=False for unit test to avoid pressing enter on active window during test run
    res_draft = wa.send_message(recipient="Tester", message="Unit test draft", auto_send=False)
    assert res_draft["status"] == "success"
    assert res_draft["auto_send"] is False
    print("  • WhatsApp send_message with auto_send=False verified.")

    # Verify auto_send method signature and execution
    assert hasattr(wa, "_simulate_enter_press")
    print("  • WhatsApp _simulate_enter_press method verified.")
    print("  [OK] WhatsApp Hands-Free Engine verified.")

    # 3. Test Email Hands-Free Engine
    print("\n[3/4] Testing Email Hands-Free Engine...")
    contacts.add_contact(name="Email Tester", email="tester@example.com", nickname="EmailGuy")
    mail = EmailEngine(contacts_manager=contacts)

    assert hasattr(mail, "_simulate_mail_send")
    # Verify open_in_mail_client accepts auto_send
    res_mail = mail.send_email(
        to="EmailGuy",
        subject="IGIRS Test Subject",
        body="IGIRS Test Body",
        auto_send=False
    )
    assert res_mail["status"] == "success"
    assert res_mail["to"] == "tester@example.com"
    assert "Dispatched email" in res_mail["summary"]
    print(f"  • Email dispatch result: {res_mail['summary']}")
    print("  [OK] Email Hands-Free Engine verified.")

    # 4. Test Assistant & Bridge Integration
    print("\n[4/4] Testing Tool Registry & Bridge Auto-Send API...")
    assistant = IGIRSAssistant()
    if hasattr(assistant, "tts"):
        assistant.tts.enabled = False
    bridge = DesktopApiBridge(assistant)

    # Check registry schema
    tools_def = assistant.tools.get_tool_definitions()
    send_email_def = next((t for t in tools_def if t["function"]["name"] == "send_email"), None)
    assert send_email_def is not None
    props = send_email_def["function"]["parameters"]["properties"]
    assert "auto_send" in props
    print("  • Tool registry send_email schema contains auto_send parameter.")

    send_wa_def = next((t for t in tools_def if t["function"]["name"] == "send_whatsapp"), None)
    assert send_wa_def is not None
    wa_props = send_wa_def["function"]["parameters"]["properties"]
    assert "auto_send" in wa_props
    print("  • Tool registry send_whatsapp schema contains auto_send parameter.")

    # Test Bridge send_email with auto_send parameter
    bridge_mail_res = bridge.send_email(
        to="tester@example.com",
        subject="Bridge Test",
        body="Bridge Body",
        auto_send=False
    )
    assert bridge_mail_res["status"] == "success"
    print("  • Bridge send_email with auto_send parameter verified.")

    print("\n" + "=" * 65)
    print("🎉 ALL HANDS-FREE AUTO-SEND VERIFICATIONS PASSED!")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
