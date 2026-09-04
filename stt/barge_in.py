"""
Voice Activity Detection (VAD) & Barge-In Monitor for IGIRS AI.
Monitors the microphone in real-time while TTS audio is playing.
Instantly triggers an interrupt callback (<100ms) when the user speaks over the assistant.
"""
import time
import logging
import threading
from typing import Optional, Callable
import numpy as np

logger = logging.getLogger("IGIRS.BargeIn")

class BargeInMonitor:
    def __init__(
        self,
        energy_threshold: float = 0.032,
        consecutive_frames_required: int = 2,
        sample_rate: int = 16000,
        block_size: int = 512
    ):
        self.energy_threshold = energy_threshold
        self.consecutive_frames_required = consecutive_frames_required
        self.sample_rate = sample_rate
        self.block_size = block_size

        self.enabled: bool = True
        self._is_monitoring: bool = False
        self._stream = None
        self._on_barge_in: Optional[Callable[[], None]] = None
        self._consecutive_hits: int = 0
        self._lock = threading.Lock()
        self._last_barge_in_time: float = 0.0
        self._cooldown_seconds: float = 0.5

    def set_enabled(self, enabled: bool):
        self.enabled = bool(enabled)
        if not self.enabled:
            self.stop_monitoring()

    def is_monitoring(self) -> bool:
        return self._is_monitoring

    def _ensure_stream(self):
        """Initializes and starts the persistent audio input stream if not already active."""
        if self._stream is not None:
            return True
        try:
            import sounddevice as sd

            def _audio_callback(indata, frames, time_info, status):
                if not self._is_monitoring:
                    return
                try:
                    # Calculate Root Mean Square (RMS) energy
                    energy = float(np.sqrt(np.mean(indata**2)))

                    if energy > self.energy_threshold:
                        self._consecutive_hits += 1
                        if self._consecutive_hits >= self.consecutive_frames_required:
                            now = time.time()
                            if (now - self._last_barge_in_time) > self._cooldown_seconds:
                                self._last_barge_in_time = now
                                logger.info(f"⚡ Barge-in detected! Energy: {energy:.4f} > {self.energy_threshold}")
                                cb = self._on_barge_in
                                self.stop_monitoring()
                                if cb:
                                    # Trigger interrupt callback in background thread
                                    threading.Thread(target=cb, daemon=True).start()
                    else:
                        self._consecutive_hits = max(0, self._consecutive_hits - 1)
                except Exception as ex:
                    logger.debug(f"Barge-in frame error: {ex}")

            self._stream = sd.InputStream(
                channels=1,
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                callback=_audio_callback
            )
            self._stream.start()
            logger.debug("Barge-in persistent stream initialized.")
            return True
        except Exception as e:
            logger.warning(f"Could not initialize barge-in stream: {e}")
            self._stream = None
            return False

    def start_monitoring(self, on_barge_in: Callable[[], None]):
        """Starts real-time microphone energy monitoring."""
        if not self.enabled:
            return

        with self._lock:
            self._on_barge_in = on_barge_in
            self._consecutive_hits = 0

            if not self._ensure_stream():
                self._is_monitoring = False
                return

            self._is_monitoring = True
            logger.debug("Barge-in monitoring enabled.")

    def stop_monitoring(self):
        """Instantly disables microphone monitoring (<1ms) while keeping stream warm."""
        with self._lock:
            self._is_monitoring = False
            self._consecutive_hits = 0
            self._on_barge_in = None
            logger.debug("Barge-in monitoring paused.")

    def close(self):
        """Closes the underlying sound device stream completely."""
        with self._lock:
            self._is_monitoring = False
            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception as e:
                    logger.debug(f"Stream close error: {e}")
                self._stream = None
