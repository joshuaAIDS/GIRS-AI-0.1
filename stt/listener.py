"""
Speech-to-Text (STT) Listener using SpeechRecognition and PyAudio.
Supports ambient noise calibration, silence detection, and bilingual recognition (English + Tamil).
"""
import logging
from typing import Optional, Callable

logger = logging.getLogger("IGIRS.STT")

try:
    import speech_recognition as sr
    HAS_SR = True
except ImportError:
    sr = None
    HAS_SR = False
    logger.warning("speech_recognition is not installed. Voice input will be disabled.")

import config

class VoiceListener:
    def __init__(self, energy_threshold: int = 300, dynamic_energy: bool = True):
        self.is_available = HAS_SR
        if HAS_SR:
            try:
                self.recognizer = sr.Recognizer()
                self.recognizer.energy_threshold = energy_threshold
                self.recognizer.dynamic_energy_threshold = dynamic_energy
                # Low-latency speech cut-off: 450ms silence triggers transcription
                self.recognizer.pause_threshold = 0.45
                self.recognizer.non_speaking_duration = 0.25
            except Exception:
                self.recognizer = None
                self.is_available = False
        else:
            self.recognizer = None
        self._mic_calibrated = False

    def calibrate_microphone(self, duration: float = 0.4):
        """Calibrates recognizer to background room noise quickly."""
        if not self.is_available or not self.recognizer:
            return
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=duration)
                self._mic_calibrated = True
                logger.info(f"Microphone calibrated. Energy threshold: {self.recognizer.energy_threshold:.1f}")
        except Exception as e:
            logger.warning(f"Microphone calibration notice: {e}")

    def listen_and_transcribe(
        self,
        timeout: int = 6,
        phrase_time_limit: int = 15,
        language: str = "en-IN",
        on_listening: Optional[Callable[[], None]] = None,
        on_transcribing: Optional[Callable[[], None]] = None,
        play_cues: bool = True
    ) -> Optional[str]:
        """
        Listens to the microphone with sub-second latency and transcribes speech into text.
        """
        if not self.is_available or not self.recognizer:
            logger.warning("Speech recognition is not available in current environment.")
            return None

        try:
            with sr.Microphone() as source:
                if not self._mic_calibrated:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.35)
                    self._mic_calibrated = True

                if play_cues:
                    try:
                        import utils.audio_cues as audio_cues
                        audio_cues.play_listening_cue()
                    except Exception:
                        pass

                if on_listening:
                    on_listening()

                # Listen for speech from microphone
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )

                if play_cues:
                    try:
                        import utils.audio_cues as audio_cues
                        audio_cues.play_thinking_cue()
                    except Exception:
                        pass

                if on_transcribing:
                    on_transcribing()

                # 1. Primary STT: Google Web Speech Recognizer
                try:
                    text = self.recognizer.recognize_google(audio, language=language)
                    if text and text.strip():
                        return text.strip()
                except sr.UnknownValueError:
                    return None
                except sr.RequestError as req_err:
                    logger.warning(f"Google STT request error: {req_err}")

                # 2. Fallback to US English
                if language != "en-US":
                    try:
                        text = self.recognizer.recognize_google(audio, language="en-US")
                        if text and text.strip():
                            return text.strip()
                    except Exception:
                        pass

        except sr.WaitTimeoutError:
            return None
        except Exception as e:
            logger.error(f"Microphone listening error: {e}")
            return None

        return None
