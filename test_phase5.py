"""
Verification Test Suite for IGIRS AI Phase 5:
Screen Vision + Media Playback + Daily Briefing Suite.
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
from utils.vision import capture_screen_base64

def test_phase5():
    print("=" * 60)
    print("🌟 IGIRS AI — Phase 5 Verification Suite")
    print("=" * 60)

    assistant = IGIRSAssistant()

    # 1. Test Screen Capture & Base64 Compression
    print("\n[1/4] Testing Screen Capture & Compression...")
    b64 = capture_screen_base64(max_width=1000)
    assert b64 is not None and len(b64) > 100, "Screen capture failed or returned empty base64!"
    print(f"  • Captured & compressed screen image: {len(b64)} chars (base64)")
    print("  [OK] Screen capture utility verified.")

    # 2. Test Media Playback Tool
    print("\n[2/4] Testing Media Playback Tool...")
    res_yt = assistant.tools._tool_play_media(query="Interstellar Theme", platform="youtube")
    print(f"  • YouTube Tool Output: {res_yt}")
    assert "YouTube" in res_yt, "YouTube playback handler failed!"

    res_spot = assistant.tools._tool_play_media(query="Lo-fi Beats", platform="spotify")
    print(f"  • Spotify Tool Output: {res_spot}")
    assert "Spotify" in res_spot, "Spotify playback handler failed!"
    print("  [OK] Media playback handlers verified.")

    # 3. Test Daily Briefing Tool
    print("\n[3/4] Testing Daily Briefing Compilation...")
    briefing = assistant.tools._tool_daily_briefing()
    print("  • Briefing Data:", briefing)
    assert "greeting" in briefing, "Missing greeting in briefing"
    assert "battery" in briefing, "Missing battery in briefing"
    assert "weather" in briefing, "Missing weather in briefing"
    print("  [OK] Daily Briefing compilation verified.")

    # 4. Test Multimodal Screen Vision with NVIDIA NIM
    print("\n[4/4] Testing Live Multimodal Screen Vision Analysis...")
    analysis = assistant.tools._tool_analyze_screen(question="What is the general layout or text visible on the screen?")
    print(f"  • Screen Analysis Result:\n    {analysis[:220]}...")
    assert len(analysis) > 10, "Screen analysis returned empty response!"
    print("  [OK] Multimodal Screen Vision verified.")

    print("\n" + "=" * 60)
    print("🎉 ALL PHASE 5 CHECKS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    test_phase5()
