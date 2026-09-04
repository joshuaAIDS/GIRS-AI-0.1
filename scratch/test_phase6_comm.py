"""
Verification Test Suite for IGIRS AI Phase 6:
Hands-Free WhatsApp & Email Assistant, Contacts Address Book, and Comm Hub.
"""
import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Set UTF-8 encoding for console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from tools.contacts_manager import ContactsManager
from tools.whatsapp_engine import WhatsAppEngine
from tools.email_engine import EmailEngine
from assistant import IGIRSAssistant
from gui.api_bridge import DesktopApiBridge

def run_tests():
    print("=" * 65)
    print("💬 IGIRS AI — Phase 6 Communications Assistant Verification")
    print("=" * 65)

    # 1. Contacts Manager Verification
    print("\n[1/5] Testing Contacts Manager (CRUD, E.164 Normalization, Nicknames)...")
    test_store = Path("scratch/test_contacts_store.json")
    if test_store.exists():
        test_store.unlink()

    cm = ContactsManager(store_file=test_store)

    # Phone normalization test
    norm1 = cm.normalize_phone("98765 43210")
    norm2 = cm.normalize_phone("+91-98765-43210")
    norm3 = cm.normalize_phone("00919876543210")
    assert norm1 == "+919876543210", f"Expected +919876543210, got {norm1}"
    assert norm2 == "+919876543210", f"Expected +919876543210, got {norm2}"
    assert norm3 == "+919876543210", f"Expected +919876543210, got {norm3}"
    print("  • Phone normalization: E.164 verified.")

    # Add contacts
    c_mom = cm.add_contact(name="Mary Watson", phone="9876511111", email="mary@example.com", nickname="Mom")
    c_boss = cm.add_contact(name="David Vance", phone="9876522222", email="david@company.com", nickname="Boss")
    assert c_mom["nickname"] == "Mom"
    assert c_boss["nickname"] == "Boss"

    # Fuzzy nickname lookup
    found_mom = cm.get_contact("mom")
    found_boss = cm.get_contact("BOSS")
    found_name = cm.get_contact("Mary")
    assert found_mom is not None and found_mom["name"] == "Mary Watson"
    assert found_boss is not None and found_boss["name"] == "David Vance"
    assert found_name is not None and found_name["nickname"] == "Mom"
    print("  • Nickname and fuzzy contact lookup verified.")
    print("  [OK] Contacts Manager verified.")

    # 2. WhatsApp Engine Verification
    print("\n[2/5] Testing WhatsApp Engine (URI Encoding & Recipient Resolution)...")
    wa = WhatsAppEngine(contacts_manager=cm)

    # Resolve contact and prepare dispatch (auto_send=False for unit testing)
    wa_res = wa.send_message(recipient="Mom", message="Heading home now! See you in 15 mins.", auto_send=False)
    assert wa_res["status"] == "success", f"WhatsApp failed: {wa_res}"
    assert wa_res["recipient_name"] == "Mary Watson"
    assert wa_res["recipient_phone"] == "+919876511111"
    print(f"  • WhatsApp dispatch resolved: {wa_res['recipient_name']} ({wa_res['recipient_phone']})")
    print(f"  • Mode: {wa_res['mode']}, Summary: {wa_res['summary']}")
    print("  [OK] WhatsApp Engine verified.")

    # 3. Email Engine Verification (AI Drafting & Fallback)
    print("\n[3/5] Testing Email Engine (AI Drafting & Mailto Fallback)...")
    assistant = IGIRSAssistant()
    mail = EmailEngine(contacts_manager=cm)

    # Test AI Smart Compose
    print("  • Generating AI email draft using NVIDIA NIM...")
    draft = mail.draft_email(
        instruction="Ask Boss for an update on the quarterly engineering milestone",
        recipient="Boss",
        tone="professional",
        llm_client=assistant.llm
    )
    assert draft["status"] == "success"
    assert draft["recipient_name"] == "David Vance"
    assert len(draft["subject"]) > 5
    assert len(draft["body"]) > 20
    print(f"  • AI Drafted Subject: {draft['subject']}")
    print(f"  • AI Drafted Body Preview: {draft['body'][:100]}...")

    # Test Fallback Send (Native Mail Client without SMTP credentials)
    mail_res = mail.send_email(to="Boss", subject=draft["subject"], body=draft["body"])
    assert mail_res["status"] == "success"
    assert mail_res["to"] == "david@company.com"
    print(f"  • Email dispatch mode: {mail_res.get('mode')} -> {mail_res['to']}")
    print("  [OK] Email Engine verified.")

    # 4. Tool Registry Integration
    print("\n[4/5] Testing Tool Registry Communication Dispatch...")
    assistant.tools.contacts.add_contact(name="Mary Watson", phone="9876511111", email="mary@example.com", nickname="Mom")
    reg_wa = assistant.tools.execute_tool("send_whatsapp", {"recipient": "Mom", "message": "Test message", "auto_send": False})
    assert "Dispatched WhatsApp" in reg_wa
    print("  • Tool send_whatsapp execution verified.")

    reg_contacts = assistant.tools.execute_tool("manage_contacts", {"action": "list"})
    assert "contacts" in reg_contacts
    print("  • Tool manage_contacts execution verified.")

    reg_draft = assistant.tools.execute_tool("draft_email", {"instruction": "Thank team for hard work", "recipient": "Team"})
    assert "subject" in reg_draft
    print("  • Tool draft_email execution verified.")
    print("  [OK] Tool Registry Integration verified.")

    # 5. Desktop GUI API Bridge Verification
    print("\n[5/5] Testing Desktop GUI API Bridge Communication Methods...")
    bridge = DesktopApiBridge(assistant)

    contacts_list = bridge.get_contacts()
    assert len(contacts_list) >= 1
    print(f"  • Bridge get_contacts returned {len(contacts_list)} contacts.")

    new_c = bridge.save_contact(name="Sarah Connor", phone="+14155551234", email="sarah@resistance.org", nickname="Sarah")
    assert new_c["status"] == "success"
    print("  • Bridge save_contact verified.")

    cfg = bridge.get_email_config()
    assert "smtp_server" in cfg
    assert "has_password" in cfg
    print("  • Bridge get_email_config verified.")

    b_draft = bridge.draft_email(instruction="Invite to project demo tomorrow at 4 PM", recipient="Sarah")
    assert b_draft["status"] == "success"
    print("  • Bridge draft_email verified.")

    b_wa = bridge.send_whatsapp(recipient="Sarah", message="Hi Sarah, demo is at 4 PM tomorrow!", auto_send=False)
    assert b_wa["status"] == "success"
    print("  • Bridge send_whatsapp verified.")

    # Clean up test contact
    if new_c.get("contact", {}).get("id"):
        bridge.delete_contact(new_c["contact"]["id"])
        print("  • Cleaned test contact.")

    if test_store.exists():
        test_store.unlink()

    print("\n" + "=" * 65)
    print("🎉 ALL PHASE 6 COMMUNICATIONS CHECKS PASSED!")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
