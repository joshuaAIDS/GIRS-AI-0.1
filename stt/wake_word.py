"""
Wake Word Detection and Trigger Phrase Matcher for IGIRS AI.
"""
import re
from typing import Tuple, List
import config

DEFAULT_WAKE_WORDS = [
    "hey igris",
    "hey igirs",
    "ok igris",
    "ok igirs",
    "igris",
    "igirs",
    "hey jarvis",
    "jarvis",
    "hey assistant",
    "assistant"
]

class WakeWordDetector:
    def __init__(self, wake_words: List[str] = None):
        self.wake_words = [w.lower().strip() for w in (wake_words or DEFAULT_WAKE_WORDS)]

    def check_and_extract(self, text: str) -> Tuple[bool, str]:
        """
        Checks if text starts with or contains a wake word.
        Returns (is_wake_word_triggered, remaining_command).
        """
        if not text:
            return False, ""

        clean = text.lower().strip()

        # Sort wake words by length descending so longer phrases match first
        for word in sorted(self.wake_words, key=len, reverse=True):
            # 1. Matches at beginning: e.g. "hey igris what is the time"
            pattern_start = r"^" + re.escape(word) + r"[\s,:\-!.]*(.*)$"
            match = re.match(pattern_start, clean, re.IGNORECASE)
            if match:
                remaining = match.group(1).strip()
                return True, remaining

            # 2. Exact match
            if clean == word:
                return True, ""

            # 3. Contains wake word in phrase
            if word in clean:
                # Extract text after wake word
                idx = clean.find(word)
                after = clean[idx + len(word):].lstrip(" ,:-!.")
                return True, after

        return False, text
