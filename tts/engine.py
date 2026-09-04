"""
Unified Text-to-Speech Engine Facade with Full Voice Controls.
Manages playback, synthesis, volume, speech rate, voice selection, and mute/unmute.
"""
import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import config
from .player import AudioPlayer
from .synthesizer import TTSSynthesizer

logger = logging.getLogger("IGIRS.TTSEngine")

POPULAR_VOICES = [
    {"id": "en-IN-NeerjaNeural", "name": "Neerja (Indian English - Female)", "lang": "English"},
    {"id": "en-IN-PrabhatNeural", "name": "Prabhat (Indian English - Male)", "lang": "English"},
    {"id": "en-US-ChristopherNeural", "name": "Christopher (US English - Confident Male JARVIS)", "lang": "English"},
    {"id": "en-US-AvaNeural", "name": "Ava (US English - Natural Female)", "lang": "English"},
    {"id": "en-GB-SoniaNeural", "name": "Sonia (British English - Elegant Female)", "lang": "English"},
    {"id": "ta-IN-PallaviNeural", "name": "Pallavi (Tamil - Female)", "lang": "Tamil"},
    {"id": "ta-IN-ValluvarNeural", "name": "Valluvar (Tamil - Male)", "lang": "Tamil"}
]

class TTSEngine:
    def __init__(self, memory_manager=None):
        self.memory_manager = memory_manager
        self.player = AudioPlayer()
        self.synthesizer = TTSSynthesizer()

        # Voice Settings
        self.enabled: bool = config.VOICE_ENABLED_DEFAULT
        self.english_voice: str = config.DEFAULT_ENGLISH_VOICE
        self.tamil_voice: str = config.DEFAULT_TAMIL_VOICE
        self.rate: str = config.DEFAULT_TTS_RATE
        self.volume: float = config.DEFAULT_TTS_VOLUME

        self.player.set_volume(self.volume)

    def set_enabled(self, enabled: bool) -> bool:
        """Enables or disables voice output."""
        self.enabled = bool(enabled)
        if not self.enabled:
            self.stop()
        return self.enabled

    def toggle(self) -> bool:
        """Toggles voice output on/off."""
        return self.set_enabled(not self.enabled)

    def set_volume(self, volume_val: Any) -> float:
        """
        Sets volume from percentage (e.g. 80, "80%", 0.8).
        """
        try:
            if isinstance(volume_val, str):
                volume_val = volume_val.replace("%", "").strip()
                val = float(volume_val)
                if val > 1.0:
                    val = val / 100.0
            else:
                val = float(volume_val)
                if val > 1.0:
                    val = val / 100.0

            self.volume = max(0.0, min(1.0, val))
            self.player.set_volume(self.volume)
            return self.volume
        except Exception as e:
            logger.warning(f"Invalid volume value '{volume_val}': {e}")
            return self.volume

    def set_rate(self, rate_val: str) -> str:
        """
        Sets speech rate (e.g. '+15%', '-10%', '1.2x').
        """
        rate_clean = rate_val.strip()
        if rate_clean.endswith("x"):
            try:
                multiplier = float(rate_clean[:-1])
                pct = int((multiplier - 1.0) * 100)
                rate_clean = f"+{pct}%" if pct >= 0 else f"{pct}%"
            except Exception:
                rate_clean = "+0%"
        elif not rate_clean.endswith("%"):
            rate_clean = f"+{rate_clean}%" if not rate_clean.startswith(("-", "+")) else f"{rate_clean}%"

        self.rate = rate_clean
        return self.rate

    def set_voice(self, voice_id_or_name: str) -> bool:
        """
        Sets active English or Tamil voice.
        """
        target = voice_id_or_name.lower().strip()
        for v in POPULAR_VOICES:
            if target == v["id"].lower() or target in v["name"].lower():
                if v["lang"] == "Tamil":
                    self.tamil_voice = v["id"]
                else:
                    self.english_voice = v["id"]
                return True

        # Custom voice ID direct assignment
        if "ta-" in target:
            self.tamil_voice = voice_id_or_name
        else:
            self.english_voice = voice_id_or_name
        return True

    def list_voices(self) -> List[Dict[str, str]]:
        return POPULAR_VOICES

    def is_speaking(self) -> bool:
        return self.player.is_playing()

    def set_barge_in_enabled(self, enabled: bool):
        """Enables or disables voice barge-in interrupt."""
        if self.player.barge_in:
            self.player.barge_in.set_enabled(enabled)

    def is_barge_in_enabled(self) -> bool:
        return bool(self.player.barge_in and self.player.barge_in.enabled)

    def set_on_barge_in(self, callback: Callable[[], None]):
        """Sets external handler fired when barge-in interrupts speech."""
        self.player.on_barge_in = callback

    def set_cues_enabled(self, enabled: bool):
        """Enables or disables procedural audio cues."""
        try:
            import utils.audio_cues as audio_cues
            audio_cues.set_cues_enabled(enabled)
        except Exception:
            pass

    def was_interrupted(self) -> bool:
        """Returns True if the most recent speech was interrupted by voice barge-in."""
        return getattr(self.player, "interrupted_by_barge_in", False)

    def trigger_barge_in(self):
        """Forces an instant barge-in interruption from any UI/keyboard event."""
        if hasattr(self.player, "trigger_barge_in"):
            self.player.trigger_barge_in()

    def stop(self, play_cue: bool = False):
        """Instantly stops speech."""
        self.player.stop()
        if play_cue:
            try:
                import utils.audio_cues as audio_cues
                audio_cues.play_stop_cue()
            except Exception:
                pass

    def speak(self, text: str, blocking: bool = False, on_complete: Optional[Callable] = None):
        """
        Synthesizes text and plays audio asynchronously with Voice Barge-In armed.
        """
        if not self.enabled or not text or not text.strip():
            return

        audio_path = self.synthesizer.synthesize(
            text=text,
            english_voice=self.english_voice,
            tamil_voice=self.tamil_voice,
            rate=self.rate
        )

        if audio_path and audio_path.exists():
            self.player.play(audio_path, blocking=blocking, on_complete=on_complete)
