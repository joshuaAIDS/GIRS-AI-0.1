"""
IGIRS AI — One-Click Desktop Application Launcher.
Starts the 3D Cyber Command Center HUD with speech-to-speech, tools, and NVIDIA NIM.
"""
import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from gui.overlay_gui import run_gui
from assistant import IGIRSAssistant

def main():
    print("⚡ Starting IGIRS AI 3D Desktop Application...")
    assistant = IGIRSAssistant()
    run_gui(assistant=assistant)

if __name__ == "__main__":
    main()
