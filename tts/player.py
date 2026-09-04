"""
Audio Playback Engine using Pygame Mixer.
Supports asynchronous, non-blocking playback, dynamic volume control, and instant interrupt.
"""
import os
import time
import logging
import threading
from pathlib import Path
from typing import Optional, Callable

# Suppress Pygame welcome message
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame

logger = logging.getLogger("IGIRS.AudioPlayer")

class AudioPlayer:
    def __init__(self, enable_barge_in: bool = False):
        self._is_initialized = False
        self._current_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._volume = 1.0
        self._is_active = False
        self.on_barge_in: Optional[Callable[[], None]] = None
        self.interrupted_by_barge_in = False

        # Voice Barge-In Monitor (Default: False for laptop speaker safety)
        try:
            from stt.barge_in import BargeInMonitor
            self.barge_in = BargeInMonitor()
            self.barge_in.set_enabled(enable_barge_in)
        except Exception as e:
            logger.debug(f"Could not initialize BargeInMonitor: {e}")
            self.barge_in = None

        self._init_mixer()

    def _init_mixer(self):
        """Initializes Pygame mixer cleanly."""
        try:
            pygame.init()
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self._is_initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize Pygame mixer: {e}")
            self._is_initialized = False

    def set_volume(self, volume: float):
        """Sets playback volume between 0.0 and 1.0."""
        self._volume = max(0.0, min(1.0, float(volume)))
        try:
            if not pygame.mixer.get_init():
                self._init_mixer()
            pygame.mixer.music.set_volume(self._volume)
        except Exception as e:
            logger.warning(f"Error setting volume: {e}")

    def get_volume(self) -> float:
        return self._volume

    def is_playing(self) -> bool:
        """
        Returns True if audio is actively playing or in startup state.
        Guarantees no race condition between thread launch and mixer busy state.
        """
        if self._stop_event.is_set():
            return False
        if self._is_active:
            return True
        try:
            if pygame.mixer.get_init():
                return pygame.mixer.music.get_busy()
        except Exception:
            return False
        return False

    def stop(self):
        """Immediately halts any ongoing audio playback and stops barge-in monitoring."""
        with self._lock:
            self._is_active = False
            self._stop_event.set()
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()
            except Exception as e:
                logger.debug(f"Stop exception: {e}")
            if self.barge_in:
                self.barge_in.stop_monitoring()

    def trigger_barge_in(self):
        """Forces an instant barge-in interrupt from any input modality (Spacebar, Orb Tap)."""
        if self.is_playing():
            self._handle_barge_in()

    def _handle_barge_in(self):
        """Callback fired when barge-in interrupts speech."""
        logger.info("⚡ Voice Barge-In: Halting speech playback instantly.")
        self.interrupted_by_barge_in = True
        self.stop()
        try:
            import utils.audio_cues as audio_cues
            audio_cues.play_barge_in_cue()
        except Exception:
            pass
        if self.on_barge_in:
            try:
                self.on_barge_in()
            except Exception as e:
                logger.error(f"Error in on_barge_in handler: {e}")

    def play(self, audio_path: Path, blocking: bool = False, on_complete: Optional[Callable] = None):
        """
        Plays an audio file. If blocking is False, plays in background thread.
        Sets _is_active immediately to eliminate polling race conditions.
        Automatically recovers from transient Windows audio device disconnects.
        """
        self.stop()  # Interrupt any previous speech
        self.interrupted_by_barge_in = False
        self._stop_event.clear()
        self._is_active = True

        def _play_worker():
            try:
                if self._stop_event.is_set():
                    return

                # 1. Initialize or verify mixer state
                try:
                    if not pygame.mixer.get_init():
                        pygame.init()
                        pygame.mixer.init()
                except Exception:
                    pass

                # 2. Load and play with self-healing recovery
                try:
                    pygame.mixer.music.load(str(audio_path))
                    pygame.mixer.music.set_volume(self._volume)
                    pygame.mixer.music.play()
                except Exception as load_err:
                    if self._stop_event.is_set():
                        return
                    logger.debug(f"Mixer load notice ({load_err}), re-opening audio device...")
                    try:
                        pygame.mixer.quit()
                        pygame.init()
                        pygame.mixer.init()
                        pygame.mixer.music.load(str(audio_path))
                        pygame.mixer.music.set_volume(self._volume)
                        pygame.mixer.music.play()
                    except Exception as reinit_err:
                        logger.debug(f"Could not play after audio device re-init: {reinit_err}")
                        return

                # 3. Start voice barge-in monitoring if explicitly enabled
                if self.barge_in and self.barge_in.enabled:
                    self.barge_in.start_monitoring(self._handle_barge_in)

                # Brief settling time to let mixer register busy state
                time.sleep(0.06)

                # 4. Playback loop
                while pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                    if self._stop_event.is_set():
                        pygame.mixer.music.stop()
                        break
                    time.sleep(0.04)

                try:
                    if pygame.mixer.get_init():
                        pygame.mixer.music.unload()
                except Exception:
                    pass

                if not self._stop_event.is_set() and on_complete:
                    on_complete()

            except Exception as ex:
                logger.debug(f"Playback worker notice for {audio_path}: {ex}")
            finally:
                self._is_active = False
                if self.barge_in:
                    self.barge_in.stop_monitoring()

        if blocking:
            _play_worker()
        else:
            thread = threading.Thread(target=_play_worker, daemon=True)
            self._current_thread = thread
            thread.start()
