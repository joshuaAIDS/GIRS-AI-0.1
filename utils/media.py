"""
Media and Music Playback Utilities for IGIRS AI.
Resolves direct playable video/song URLs from YouTube and Spotify.
"""
import urllib.request
import urllib.parse
import re
import subprocess
import webbrowser
import logging
from typing import Optional

logger = logging.getLogger("IGIRS.Media")

def get_youtube_first_video_id(query: str) -> Optional[str]:
    """
    Scrapes the top video result ID from YouTube search to allow direct video playback.
    """
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.youtube.com/results?search_query={encoded}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            # 1. Match videoId JSON key from YouTube desktop page
            matches = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
            # 2. Fallback to /watch?v= URLs
            if not matches:
                matches = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
            if matches:
                for vid in matches:
                    if len(vid) == 11 and not vid.startswith("AA"):
                        return vid
    except Exception as e:
        logger.warning(f"Failed to scrape YouTube video ID for '{query}': {e}")
    return None

def play_media_content(query: str, platform: str = "youtube") -> str:
    """
    Plays the requested song or media directly on YouTube or Spotify.
    """
    if not query:
        return "Please specify a song or video title to play."

    clean_query = query.strip()
    encoded = urllib.parse.quote_plus(clean_query)
    plat = platform.lower() if platform else "youtube"

    if "spot" in plat:
        # Spotify playback
        try:
            subprocess.Popen(f"start spotify:search:{clean_query}", shell=True)
            return f"Opening Spotify to play '{clean_query}'."
        except Exception:
            webbrowser.open(f"https://open.spotify.com/search/{encoded}")
            return f"Playing '{clean_query}' on Spotify."
    else:
        # YouTube Direct Playback
        vid = get_youtube_first_video_id(clean_query)
        if vid:
            direct_url = f"https://www.youtube.com/watch?v={vid}&autoplay=1"
            try:
                subprocess.Popen(f'start "" "{direct_url}"', shell=True)
            except Exception:
                webbrowser.open(direct_url)
            return f"Playing '{clean_query}' on YouTube."
        else:
            # Fallback to search query if ID resolution failed
            search_url = f"https://www.youtube.com/results?search_query={encoded}"
            try:
                subprocess.Popen(f'start "" "{search_url}"', shell=True)
            except Exception:
                webbrowser.open(search_url)
            return f"Playing '{clean_query}' on YouTube."

if __name__ == "__main__":
    test_queries = ["faded alan walker", "vaathi coming song"]
    for tq in test_queries:
        vid = get_youtube_first_video_id(tq)
        print(f"'{tq}' -> Video ID: {vid} (https://www.youtube.com/watch?v={vid})")
