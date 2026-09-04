"""
Direct verification script for Windows 'Minimize All Windows' feature.
Run this script to test minimizing all windows directly on your desktop.
"""
import time
from tools.system_controls import minimize_all_windows
from assistant import IGIRSAssistant

def main():
    print("=" * 60)
    print("Testing 'Minimize All Windows' on Windows Desktop")
    print("=" * 60)
    print("Minimizing in 1 second...")
    time.sleep(1)

    # 1. Direct Tool Call Test
    res = minimize_all_windows()
    print(f"\n[Direct Function Result]: {res}")

    if res.get("success"):
        print("[SUCCESS] Windows Shell minimized all desktop windows!")
    else:
        print(f"[FAIL] Error: {res.get('error')}")

    # 2. Assistant Voice/Chat Processing Test
    print("\nTesting via Assistant NLP Processing...")
    assistant = IGIRSAssistant()
    reply = assistant.process_message("minimize all windows", speak_response=False)
    print(f"[Assistant Response]: '{reply}'")
    print("=" * 60)
    print("Verification complete!")

if __name__ == "__main__":
    main()
