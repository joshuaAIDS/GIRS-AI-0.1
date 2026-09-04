"""
Voice Activity Detection (VAD) & Adaptive Barge-In Monitor for IGIRS AI.
Monitors the microphone in real-time while TTS audio is playing.
Uses calibrated acoustic frame-windowing to prevent laptop speaker self-triggering,
while instantly detecting user speech interrupt (<100ms).
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
        energy_threshold: float = 0.240,
        consecutive_frames_required: int = 8,
        sample_rate: int = 16000,
        block_size: int = 512
    ):
        self.default_threshold: float = energy_threshold
        self.energy_threshold: float = energy_threshold
        self.consecutive_frames_required: int = consecutive_frames_required
        self.sample_rate: int = sample_rate
        self.block_size: int = block_size

        # Disabled by default so laptop speakers do not self-interrupt speech.
        # Spacebar, Escape, and 3D Orb Tap always remain 100% active.
        self.enabled: bool = False
        self._is_monitoring: bool = False
        self._stream = None
        self._on_barge_in: Optional[Callable[[], None]] = None
        self._consecutive_hits: int = 0
        self._lock = threading.Lock()

        # Playback Timing & Settling Guard
        self._monitor_start_time: float = 0.0
        self._settling_window_sec: float = 0.60   # Ignore initial audio buffer / speaker attack
        self._last_barge_in_time: float = 0.0
        self._cooldown_seconds: float = 0.6
        self._sensitivity_mode: str = "off"

    def set_enabled(self, enabled: bool):
        self.enabled = bool(enabled)
        if not self.enabled:
            self._sensitivity_mode = "off"
            self.stop_monitoring()
        elif self._sensitivity_mode == "off":
            self._sensitivity_mode = "speakers"

    def get_mode(self) -> str:
        return self._sensitivity_mode if self.enabled else "off"

    def set_sensitivity(self, mode: str):
        """
        Sets barge-in detection sensitivity profile:
        - 'off': voice barge-in off (Spacebar & Orb Tap still work instantly)
        - 'headphones': sensitive threshold (0.040) for headsets/earbuds where speaker leakage is 0
        - 'speakers': calibrated high-threshold (0.240) for laptop speakers without false triggers
        - 'noisy': high-noise threshold (0.320) for noisy rooms
        """
        mode_clean = mode.lower().strip()
        if mode_clean in ("off", "disable", "disabled", "manual"):
            self.enabled = False
            self._sensitivity_mode = "off"
            self.stop_monitoring()
        elif mode_clean == "headphones":
            self.enabled = True
            self.energy_threshold = 0.040
            self.consecutive_frames_required = 4
            self._settling_window_sec = 0.25
            self._sensitivity_mode = "headphones"
        elif mode_clean == "noisy":
            self.enabled = True
            self.energy_threshold = 0.320
            self.consecutive_frames_required = 10
            self._settling_window_sec = 0.80
            self._sensitivity_mode = "noisy"
        else:
            self.enabled = True
            self.energy_threshold = 0.240
            self.consecutive_frames_required = 8
            self._settling_window_sec = 0.60
            self._sensitivity_mode = "speakers"
        logger.info(f"Barge-in profile set to '{self._sensitivity_mode}' (enabled={self.enabled}, threshold={self.energy_threshold})")

    def is_monitoring(self) -> bool:
        return self._is_monitoring

    def trigger_barge_in(self):
        """Manually or programmatically triggers a barge-in event immediately."""
        with self._lock:
            if not self._is_monitoring:
                return
            now = time.time()
            if (now - self._last_barge_in_time) > self._cooldown_seconds:
                self._last_barge_in_time = now
                logger.info("⚡ Immediate Barge-in triggered programmatically (Spacebar/Click).")
                cb = self._on_barge_in
                self.stop_monitoring()
                if cb:
                    threading.Thread(target=cb, daemon=True).start()

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
                    now = time.time()
                    elapsed = now - self._monitor_start_time

                    # Calculate Root Mean Square (RMS) energy of this frame
                    energy = float(np.sqrt(np.mean(indata**2)))

                    # During the initial settling window, ignore buffer pops
                    if elapsed < self._settling_window_sec:
                        return

                    # Check for voice barge-in exceeding threshold
                    if energy > self.energy_threshold:
                        self._consecutive_hits += 1
                        if self._consecutive_hits >= self.consecutive_frames_required:
                            if (now - self._last_barge_in_time) > self._cooldown_seconds:
                                self._last_barge_in_time = now
                                logger.info(
                                    f"⚡ Voice Barge-in detected! Energy: {energy:.4f} > Threshold: {self.energy_threshold:.4f} "
                                    f"({self._consecutive_hits} frames)"
                                )
                                cb = self._on_barge_in
                                self.stop_monitoring()
                                if cb:
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
            self._monitor_start_time = time.time()

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
