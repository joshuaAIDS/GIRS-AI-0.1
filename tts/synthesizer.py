"""
Text-to-Speech Synthesizer using Edge-TTS and Offline SAPI5 Fallback.
Handles text cleaning, language detection, and audio file generation.
"""
import re
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Optional
import config

logger = logging.getLogger("IGIRS.Synthesizer")

def clean_text_for_speech(text: str) -> str:
    """Removes markdown symbols, URLs, code blocks, and emojis for natural speech."""
    if not text:
        return ""

    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", " [code block omitted] ", text)
    text = re.sub(r"`[^`]*`", "", text)

    # Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", " link ", text)

    # Remove markdown headers, bold, italics, quotes
    text = re.sub(r"[#*_~>]+", "", text)

    # Remove list bullet markers like "* " or "- "
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.MULTILINE)

    # Replace common symbol clutter
    text = re.sub(r"[\[\]\(\)\{\}]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def detect_language(text: str) -> str:
    """Detects if the text contains Tamil characters."""
    for char in text:
        if "\u0b80" <= char <= "\u0bff":
            return "ta"
    return "en"

class TTSSynthesizer:
    def __init__(self, output_dir: Path = config.TEMP_AUDIO_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._offline_engine = None

    async def _async_edge_tts(self, text: str, voice: str, rate: str, out_file: Path):
        import edge_tts
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(str(out_file))

    def synthesize(
        self,
        text: str,
        english_voice: str = config.DEFAULT_ENGLISH_VOICE,
        tamil_voice: str = config.DEFAULT_TAMIL_VOICE,
        rate: str = config.DEFAULT_TTS_RATE
    ) -> Optional[Path]:
        """
        Synthesizes text into an MP3 file and returns the file path.
        """
        cleaned = clean_text_for_speech(text)
        if not cleaned:
            return None

        lang = detect_language(cleaned)
        voice = tamil_voice if lang == "ta" else english_voice

        # Generate unique temporary audio file path
        unique_id = uuid.uuid4().hex[:8]
        out_file = self.output_dir / f"speech_{unique_id}_{lang}.mp3"

        # 1. Primary Method: Edge-TTS
        try:
            asyncio.run(self._async_edge_tts(cleaned, voice, rate, out_file))
            if out_file.exists() and out_file.stat().st_size > 0:
                return out_file
        except Exception as e:
            logger.warning(f"Edge-TTS synthesis failed ({e}), attempting offline fallback...")

        # 2. Fallback Method: pyttsx3 (SAPI5)
        try:
            import pyttsx3
            fallback_wav = self.output_dir / f"speech_{unique_id}_fallback.wav"
            engine = pyttsx3.init()
            engine.save_to_file(cleaned, str(fallback_wav))
            engine.runAndWait()
            if fallback_wav.exists() and fallback_wav.stat().st_size > 0:
                return fallback_wav
        except Exception as fallback_err:
            logger.error(f"Offline pyttsx3 fallback failed: {fallback_err}")

        return None
