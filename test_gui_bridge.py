"""
Verification Test Suite for IGIRS AI Desktop GUI API Bridge (Phase 4).
"""
import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from assistant import IGIRSAssistant
from gui.api_bridge import DesktopApiBridge

def test_gui_bridge():
    print("=" * 60)
    print("🖥️ IGIRS AI — Phase 4 Desktop GUI Bridge Verification Suite")
    print("=" * 60)

    assistant = IGIRSAssistant()
    bridge = DesktopApiBridge(assistant=assistant)

    # 1. Telemetry Bridge Test
    print("\n[1/4] Testing Telemetry Bridge...")
    telemetry = bridge.get_telemetry()
    print("  • Telemetry Data:", telemetry)
    assert "cpu_usage_percent" in telemetry, "Missing CPU in telemetry"
    assert "battery_percent" in telemetry, "Missing battery in telemetry"
    print("  [OK] Telemetry Bridge verified.")

    # 2. Fact Vault Bridge Test
    print("\n[2/4] Testing Fact Vault Bridge...")
    initial_facts = bridge.get_facts()
    print(f"  • Initial Facts ({len(initial_facts)}):", initial_facts)
    test_fact = "User tested GUI Fact Vault Bridge"
    bridge.add_fact(test_fact)
    updated_facts = bridge.get_facts()
    assert test_fact in updated_facts, "Failed to add fact via bridge!"
    bridge.remove_fact(test_fact)
    assert test_fact not in bridge.get_facts(), "Failed to remove fact via bridge!"
    print("  [OK] Fact Vault Bridge verified.")

    # 3. Voice Settings Bridge Test
    print("\n[3/4] Testing Voice Settings Bridge...")
    settings = bridge.get_voice_settings()
    print("  • Active Voice Settings:", settings)
    assert "english_voice" in settings, "Missing english voice in settings"
    bridge.update_voice_settings({"volume": 85, "rate": "+10%"})
    assert assistant.tts.volume == 0.85, "Volume update failed"
    print("  [OK] Voice Settings Bridge verified.")

    # 4. Message & Tool Invocation Bridge Test
    print("\n[4/4] Testing Message & Tool Bridge...")
    result = bridge.send_message("What is the current time?")
    print(f"  • Status: {result.get('status')}")
    print(f"  • Response: {result.get('response')}")
    print(f"  • Tool Logs: {result.get('tool_logs')}")
    assert result.get("status") == "success", "Message bridge failed!"
    assert len(result.get("response")) > 0, "Empty response from bridge!"
    print("  [OK] Message and Tool Bridge verified.")

    print("\n" + "=" * 60)
    print("🎉 ALL PHASE 4 DESKTOP GUI CHECKS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    test_gui_bridge()
