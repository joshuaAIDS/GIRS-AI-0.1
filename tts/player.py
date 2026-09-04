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
    def __init__(self):
        self._is_initialized = False
        self._current_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._volume = 1.0
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
        """Returns True if audio is actively playing."""
        try:
            if pygame.mixer.get_init():
                return pygame.mixer.music.get_busy()
        except Exception:
            return False
        return False

    def stop(self):
        """Immediately halts any ongoing audio playback."""
        with self._lock:
            self._stop_event.set()
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()
            except Exception as e:
                logger.debug(f"Stop exception: {e}")

    def play(self, audio_path: Path, blocking: bool = False, on_complete: Optional[Callable] = None):
        """
        Plays an audio file. If blocking is False, plays in background thread.
        """
        self.stop() # Interrupt any previous speech
        self._stop_event.clear()

        def _play_worker():
            try:
                if not pygame.mixer.get_init():
                    pygame.init()
                    pygame.mixer.init()

                pygame.mixer.music.load(str(audio_path))
                pygame.mixer.music.set_volume(self._volume)
                pygame.mixer.music.play()

                while pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                    if self._stop_event.is_set():
                        pygame.mixer.music.stop()
                        break
                    time.sleep(0.05)

                try:
                    if pygame.mixer.get_init():
                        pygame.mixer.music.unload()
                except Exception:
                    pass

                if not self._stop_event.is_set() and on_complete:
                    on_complete()

            except Exception as ex:
                logger.error(f"Playback error for {audio_path}: {ex}")

        if blocking:
            _play_worker()
        else:
            thread = threading.Thread(target=_play_worker, daemon=True)
            self._current_thread = thread
            thread.start()
