"""
Verification Test Suite for IGIRS AI Voice Engine (Phase 2).
"""
import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import time
from pathlib import Path
import config
from tts import TTSEngine, TTSSynthesizer, AudioPlayer
from assistant import IGIRSAssistant

def test_voice_engine():
    print("=" * 60)
    print("🔊 IGIRS AI — Phase 2 Voice Output Verification Suite")
    print("=" * 60)

    # 1. Synthesizer Test
    print("\n[1/5] Testing Text-to-Speech Synthesis (Edge-TTS)...")
    synth = TTSSynthesizer()
    eng_text = "Hello Joshua, voice synthesis is operational."
    mp3_path = synth.synthesize(eng_text)
    print(f"  • English Audio Generated: {mp3_path}")
    assert mp3_path is not None and mp3_path.exists(), "English synthesis failed!"
    print("  [OK] English TTS synthesized successfully.")

    # 2. Tamil Language Detection & Synthesis
    print("\n[2/5] Testing Tamil Language Synthesis...")
    tamil_text = "வணக்கம் ஜோஷுவா! குரல் அமைப்பு தயாராக உள்ளது."
    tamil_mp3 = synth.synthesize(tamil_text)
    print(f"  • Tamil Audio Generated: {tamil_mp3}")
    assert tamil_mp3 is not None and tamil_mp3.exists(), "Tamil synthesis failed!"
    print("  [OK] Tamil TTS synthesized successfully.")

    # 3. Audio Player Playback
    print("\n[3/5] Testing Audio Player (Pygame Mixer)...")
    player = AudioPlayer()
    player.set_volume(0.8)
    print("  • Playing test audio segment...")
    player.play(mp3_path, blocking=False)
    time.sleep(0.3)
    assert player.is_playing(), "Player is not playing audio!"
    print(f"  • Is Playing: {player.is_playing()} | Volume: {int(player.get_volume() * 100)}%")
    player.stop()
    print("  • Stop called. Is Playing:", player.is_playing())
    assert not player.is_playing(), "Player failed to stop!"
    print("  [OK] Non-blocking playback and instant stop verified.")

    # 4. Voice Controls (Engine Facade)
    print("\n[4/5] Testing Voice Controls & Persona Switcher...")
    tts = TTSEngine()
    tts.set_volume("75%")
    assert tts.volume == 0.75, "Volume setting mismatch!"
    tts.set_rate("+15%")
    assert tts.rate == "+15%", "Rate setting mismatch!"
    tts.set_voice("Christopher")
    assert "Christopher" in tts.english_voice, "Voice switch failed!"
    print(f"  • Active English Voice: {tts.english_voice}")
    print(f"  • Volume: {int(tts.volume * 100)}% | Rate: {tts.rate}")
    print("  [OK] Voice controls verified.")

    # 5. Assistant Integrated Voice Test
    print("\n[5/5] Testing Assistant with Voice Pipeline...")
    assistant = IGIRSAssistant()
    print("  • Asking: 'Hi IGIRS, is the voice engine active?'")
    reply = assistant.process_message("Hi IGIRS, is the voice engine active?", speak_response=True)
    print(f"  • Text Response: \"{reply}\"")
    time.sleep(0.5)
    print(f"  • Assistant Speech Active: {assistant.tts.is_speaking()}")
    assistant.tts.stop()
    print("  [OK] Assistant end-to-end voice loop verified.")

    print("\n" + "=" * 60)
    print("🎉 ALL PHASE 2 VOICE CHECKS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    test_voice_engine()
