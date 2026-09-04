"""
Verification Test Suite for IGIRS AI Speech-to-Text & Wake Word Subsystem (Phase 3).
"""
import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import speech_recognition as sr
from stt.listener import VoiceListener
from stt.wake_word import WakeWordDetector
from assistant import IGIRSAssistant

def test_stt_pipeline():
    print("=" * 60)
    print("🎙️ IGIRS AI — Phase 3 Speech-to-Text Verification Suite")
    print("=" * 60)

    # 1. Microphone Detection
    print("\n[1/4] Testing Microphone Devices...")
    mics = sr.Microphone.list_microphone_names()
    print(f"  • Detected {len(mics)} audio devices.")
    assert len(mics) > 0, "No microphone devices found!"
    print(f"  • Primary Device: {mics[0]}")
    print("  [OK] Microphone hardware detected.")

    # 2. Ambient Noise Calibration
    print("\n[2/4] Testing Ambient Noise Calibration...")
    listener = VoiceListener()
    listener.calibrate_microphone(duration=0.5)
    print(f"  • Calibrated Energy Threshold: {listener.recognizer.energy_threshold:.1f}")
    assert listener._mic_calibrated, "Calibration failed!"
    print("  [OK] Ambient noise calibration verified.")

    # 3. Wake Word Detector Test
    print("\n[3/4] Testing Wake Word Detector & Command Extractor...")
    detector = WakeWordDetector()
    
    # Test cases
    t1, q1 = detector.check_and_extract("Hey Igris what is the current time")
    assert t1 and q1 == "what is the current time", f"Failed case 1: {t1}, {q1}"
    
    t2, q2 = detector.check_and_extract("jarvis check my battery status")
    assert t2 and q2 == "check my battery status", f"Failed case 2: {t2}, {q2}"

    t3, q3 = detector.check_and_extract("how are you doing today")
    assert not t3 and q3 == "how are you doing today", f"Failed case 3: {t3}, {q3}"

    print("  • 'Hey Igris what is the current time' -> Triggered: True | Extracted: 'what is the current time'")
    print("  • 'jarvis check my battery status'    -> Triggered: True | Extracted: 'check my battery status'")
    print("  • 'how are you doing today'           -> Triggered: False | Extracted: 'how are you doing today'")
    print("  [OK] Wake word detection and command extraction verified.")

    # 4. Assistant STT Integration
    print("\n[4/4] Testing Assistant Speech-to-Speech Controller Integration...")
    assistant = IGIRSAssistant()
    assert hasattr(assistant, "stt"), "Assistant missing STT listener!"
    assert hasattr(assistant, "listen_and_respond"), "Assistant missing listen_and_respond method!"
    print("  • Assistant Speech-to-Speech Pipeline: READY")
    print("  [OK] Assistant STT integration verified.")

    print("\n" + "=" * 60)
    print("🎉 ALL PHASE 3 SPEECH-TO-TEXT CHECKS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    test_stt_pipeline()
