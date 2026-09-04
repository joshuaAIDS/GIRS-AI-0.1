"""
Desktop 3D Cyber Command Center GUI Launcher using pywebview.
Embeds the WebGL 3D Orb and Glassmorphic HUD with full JS-Python bridging.
"""
import os
import sys
import logging
from pathlib import Path
from typing import Optional
import webview
import config
from assistant import IGIRSAssistant
from gui.api_bridge import DesktopApiBridge

logger = logging.getLogger("IGIRS.GUI")

def run_gui(assistant: Optional[IGIRSAssistant] = None):
    """Launches the native Windows Desktop GUI."""
    if assistant is None:
        assistant = IGIRSAssistant()

    bridge = DesktopApiBridge(assistant=assistant)
    html_path = config.BASE_DIR / "gui" / "web" / "index.html"

    if not html_path.exists():
        raise FileNotFoundError(f"GUI HTML template not found at {html_path}")

    # Create PyWebView native window
    window = webview.create_window(
        title=f"{config.ASSISTANT_NAME} — 3D Cyber Command Center",
        url=f"file:///{html_path.as_posix()}",
        js_api=bridge,
        width=1320,
        height=820,
        min_size=(960, 640),
        background_color="#03050A",
        easy_drag=False
    )

    bridge.set_window(window)
    logger.info("Launching 3D Cyber HUD GUI window...")
    
    # Start webview loop (blocks until window is closed)
    webview.start(debug=False)

if __name__ == "__main__":
    run_gui()
