"""
Procedural High-Tech Audio Cues for IGIRS AI.
Generates pure studio-quality sci-fi sound effects at 44.1kHz with zero disk overhead.
Provides audio feedback for listening, thinking, completion, stop, and barge-in.
"""
import os
import logging
import threading
from typing import Optional, Dict, Any

logger = logging.getLogger("IGIRS.AudioCues")

_cues_enabled = True
_sounds_cache: Dict[str, Any] = {}
_lock = threading.Lock()

def is_cues_enabled() -> bool:
    return _cues_enabled

def set_cues_enabled(enabled: bool):
    global _cues_enabled
    _cues_enabled = bool(enabled)
    logger.info(f"Audio cues enabled: {_cues_enabled}")

def _get_pygame_mixer():
    try:
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        return pygame
    except Exception as e:
        logger.debug(f"Pygame mixer unavailable for cues: {e}")
        return None

def _create_synth_sound(freq_start: float, freq_end: float, duration_ms: int, volume: float = 0.22):
    """Synthesizes a clean sine sweep with cosine attack/decay envelope."""
    try:
        import numpy as np
        import pygame
        sr = 44100
        n_samples = int(sr * (duration_ms / 1000.0))
        t = np.linspace(0, duration_ms / 1000.0, n_samples, endpoint=False)
        freqs = np.linspace(freq_start, freq_end, n_samples)
        phase = 2 * np.pi * freqs * t
        wave = np.sin(phase)
        envelope = np.sin(np.pi * np.linspace(0, 1, n_samples))
        samples = (wave * envelope * volume * 32767).astype(np.int16)
        stereo = np.column_stack((samples, samples))
        return pygame.sndarray.make_sound(stereo)
    except Exception as e:
        logger.debug(f"Synth error: {e}")
        return None

def _create_chord_sound(freq1: float, freq2: float, duration_ms: int, volume: float = 0.20):
    """Synthesizes a dual-tone harmonic chord with envelope."""
    try:
        import numpy as np
        import pygame
        sr = 44100
        n_samples = int(sr * (duration_ms / 1000.0))
        t = np.linspace(0, duration_ms / 1000.0, n_samples, endpoint=False)
        wave = 0.5 * np.sin(2 * np.pi * freq1 * t) + 0.5 * np.sin(2 * np.pi * freq2 * t)
        envelope = np.sin(np.pi * np.linspace(0, 1, n_samples))
        samples = (wave * envelope * volume * 32767).astype(np.int16)
        stereo = np.column_stack((samples, samples))
        return pygame.sndarray.make_sound(stereo)
    except Exception as e:
        logger.debug(f"Chord synth error: {e}")
        return None

def _play_cached(name: str, generator_fn):
    """Plays sound from cache or synthesizes on-demand in background."""
    if not _cues_enabled:
        return
    
    def _worker():
        pygame = _get_pygame_mixer()
        if not pygame:
            return
        with _lock:
            snd = _sounds_cache.get(name)
            if not snd:
                snd = generator_fn()
                if snd:
                    _sounds_cache[name] = snd
        if snd:
            try:
                snd.play()
            except Exception as e:
                logger.debug(f"Play cue error: {e}")

    threading.Thread(target=_worker, daemon=True).start()

def play_listening_cue():
    """Plays upward high-tech chirp (1100Hz -> 1650Hz) signaling mic is live."""
    _play_cached("listening", lambda: _create_synth_sound(1100, 1650, 110, volume=0.20))

def play_thinking_cue():
    """Plays subtle confirmation pulse (950Hz) when query is received."""
    _play_cached("thinking", lambda: _create_synth_sound(950, 950, 65, volume=0.15))

def play_success_cue():
    """Plays pleasant dual harmonic chord (C6 1046Hz + E6 1318Hz)."""
    _play_cached("success", lambda: _create_chord_sound(1046, 1318, 135, volume=0.18))

def play_stop_cue():
    """Plays gentle downward tone (1400Hz -> 720Hz) when stopping voice or mic."""
    _play_cached("stop", lambda: _create_synth_sound(1400, 720, 115, volume=0.18))

def play_barge_in_cue():
    """Plays soft instant click/blip (700Hz) when user interrupts assistant speech."""
    _play_cached("barge_in", lambda: _create_synth_sound(700, 700, 35, volume=0.16))
