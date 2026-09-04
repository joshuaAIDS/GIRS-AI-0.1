"""
Media Controls & Streaming Automation for IGIRS AI.
Provides voice-activated Spotify playback, YouTube search & autoplay,
and global Windows media key simulation (Play/Pause, Next, Previous, Stop).
"""
import os
import re
import time
import logging
import urllib.request
import urllib.parse
import webbrowser
from typing import Dict, Any, Optional

logger = logging.getLogger("IGIRS.MediaControls")

# Windows Virtual Key Codes for Media Keys
VK_MEDIA_NEXT_TRACK = 0xB0  # 176
VK_MEDIA_PREV_TRACK = 0xB1  # 177
VK_MEDIA_STOP = 0xB2        # 178
VK_MEDIA_PLAY_PAUSE = 0xB3  # 179
VK_VOLUME_MUTE = 0xAD       # 173
VK_VOLUME_DOWN = 0xAE       # 174
VK_VOLUME_UP = 0xAF         # 175

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002


def _send_virtual_key(vk_code: int) -> bool:
    """Sends a Windows virtual key down and up event via ctypes user32."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
        time.sleep(0.02)
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        return True
    except Exception as e:
        logger.debug(f"ctypes keybd_event failed: {e}")
        try:
            import pyautogui
            mapping = {
                VK_MEDIA_PLAY_PAUSE: "playpause",
                VK_MEDIA_NEXT_TRACK: "nexttrack",
                VK_MEDIA_PREV_TRACK: "prevtrack",
                VK_MEDIA_STOP: "stop",
                VK_VOLUME_MUTE: "volumemute",
                VK_VOLUME_UP: "volumeup",
                VK_VOLUME_DOWN: "volumedown"
            }
            key_name = mapping.get(vk_code)
            if key_name:
                pyautogui.press(key_name)
                return True
        except Exception as ex:
            logger.error(f"Media key simulation failed: {ex}")
    return False


def is_spotify_installed() -> bool:
    """Checks if Spotify URI scheme or desktop executable is registered on Windows."""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "spotify")
        winreg.CloseKey(key)
        return True
    except Exception:
        pass

    appdata_path = os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe")
    local_appdata = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe")
    return os.path.exists(appdata_path) or os.path.exists(local_appdata)


def control_media(action: str) -> Dict[str, Any]:
    """
    Controls Windows media playback globally using virtual media keys.
    Supported actions: 'play', 'pause', 'play_pause', 'next', 'previous', 'stop', 'mute'.
    """
    action_clean = action.strip().lower().replace("-", "_").replace(" ", "_")

    key_map = {
        "play": VK_MEDIA_PLAY_PAUSE,
        "pause": VK_MEDIA_PLAY_PAUSE,
        "play_pause": VK_MEDIA_PLAY_PAUSE,
        "playpause": VK_MEDIA_PLAY_PAUSE,
        "resume": VK_MEDIA_PLAY_PAUSE,
        "next": VK_MEDIA_NEXT_TRACK,
        "next_track": VK_MEDIA_NEXT_TRACK,
        "skip": VK_MEDIA_NEXT_TRACK,
        "previous": VK_MEDIA_PREV_TRACK,
        "prev": VK_MEDIA_PREV_TRACK,
        "prev_track": VK_MEDIA_PREV_TRACK,
        "back": VK_MEDIA_PREV_TRACK,
        "stop": VK_MEDIA_STOP,
        "mute": VK_VOLUME_MUTE,
        "unmute": VK_VOLUME_MUTE,
        "volume_mute": VK_VOLUME_MUTE
    }

    vk_code = key_map.get(action_clean)
    if not vk_code:
        return {
            "status": "error",
            "action": action,
            "message": f"Unsupported media action '{action}'. Valid actions: play, pause, next, previous, stop, mute."
        }

    success = _send_virtual_key(vk_code)
    if success:
        return {
            "status": "success",
            "action": action_clean,
            "message": f"Sent media control command: {action_clean.replace('_', ' ').capitalize()}."
        }
    else:
        return {
            "status": "error",
            "action": action_clean,
            "message": f"Failed to send media key for {action_clean}."
        }


def search_youtube(query: str) -> Dict[str, Any]:
    """Opens YouTube search results page for the specified query."""
    encoded_query = urllib.parse.quote(query.strip())
    url = f"https://www.youtube.com/results?search_query={encoded_query}"
    try:
        webbrowser.open(url)
        return {
            "status": "success",
            "platform": "youtube",
            "query": query,
            "url": url,
            "action": "search"
        }
    except Exception as e:
        logger.error(f"Error opening YouTube search: {e}")
        return {"status": "error", "message": f"Failed to open YouTube: {str(e)}"}


def play_youtube(query: str, autoplay: bool = True) -> Dict[str, Any]:
    """
    Searches YouTube, resolves the top matching video, and launches browser with autoplay=1.
    If direct video extraction fails, seamlessly falls back to opening YouTube search results.
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        webbrowser.open("https://www.youtube.com")
        return {"status": "success", "platform": "youtube", "url": "https://www.youtube.com", "action": "open_home"}

    encoded_query = urllib.parse.quote(cleaned_query)
    search_url = f"https://www.youtube.com/results?search_query={encoded_query}"

    video_id: Optional[str] = None
    video_title: Optional[str] = None

    try:
        req = urllib.request.Request(
            search_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        matches = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", html)
        if matches:
            video_id = matches[0]

        title_matches = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"\}', html)
        if not title_matches:
            title_matches = re.findall(r'"title":\{"simpleText":"([^"]+)"\}', html)
        if title_matches:
            video_title = title_matches[0]

    except Exception as ex:
        logger.debug(f"YouTube video ID scrape error (falling back to search URL): {ex}")

    if video_id:
        target_url = f"https://www.youtube.com/watch?v={video_id}&autoplay=1"
        display_title = video_title or cleaned_query
        try:
            webbrowser.open(target_url)
            logger.info(f"Opened YouTube video: {video_id} ({display_title})")
            return {
                "status": "success",
                "platform": "youtube",
                "query": cleaned_query,
                "video_id": video_id,
                "title": display_title,
                "url": target_url,
                "action": "autoplay"
            }
        except Exception as e:
            logger.error(f"Error launching browser: {e}")
            return {"status": "error", "message": str(e)}
    else:
        webbrowser.open(search_url)
        return {
            "status": "success",
            "platform": "youtube",
            "query": cleaned_query,
            "url": search_url,
            "action": "search_fallback"
        }


def play_spotify(query: str = "") -> Dict[str, Any]:
    """
    Plays music on Spotify.
    If query is empty: toggles play/pause or launches Spotify app.
    If query is provided: launches Spotify search URI or Web player fallback.
    """
    cleaned_query = query.strip()
    installed = is_spotify_installed()

    if not cleaned_query:
        if installed:
            try:
                os.startfile("spotify:")
                time.sleep(0.3)
                _send_virtual_key(VK_MEDIA_PLAY_PAUSE)
                return {
                    "status": "success",
                    "platform": "spotify",
                    "action": "resume_or_open",
                    "message": "Resumed Spotify playback or launched Spotify."
                }
            except Exception as e:
                logger.debug(f"startfile spotify failed: {e}")

        webbrowser.open("https://open.spotify.com")
        return {
            "status": "success",
            "platform": "spotify",
            "action": "open_web",
            "url": "https://open.spotify.com"
        }

    encoded_query = urllib.parse.quote(cleaned_query)
    spotify_uri = f"spotify:search:{encoded_query}"
    web_url = f"https://open.spotify.com/search/{encoded_query}"

    if installed:
        try:
            os.startfile(spotify_uri)
            logger.info(f"Launched Spotify URI: {spotify_uri}")
            return {
                "status": "success",
                "platform": "spotify",
                "query": cleaned_query,
                "uri": spotify_uri,
                "action": "desktop_search",
                "message": f"Searching and playing '{cleaned_query}' on Spotify."
            }
        except Exception as e:
            logger.warning(f"Error launching Spotify URI: {e}, falling back to Web")

    webbrowser.open(web_url)
    return {
        "status": "success",
        "platform": "spotify",
        "query": cleaned_query,
        "url": web_url,
        "action": "web_search",
        "message": f"Opened '{cleaned_query}' on Spotify Web."
    }


def play_media(query: str, platform: str = "auto") -> Dict[str, Any]:
    """
    Unified voice media router.
    Routes queries to Spotify or YouTube based on explicit platform argument,
    user request keywords, or content category.
    """
    target_platform = platform.strip().lower()
    q_lower = query.lower()

    if target_platform == "spotify" or "on spotify" in q_lower or "in spotify" in q_lower:
        clean_q = re.sub(r"\b(on|in|from)\s+spotify\b", "", query, flags=re.IGNORECASE).strip()
        return play_spotify(clean_q)

    if target_platform == "youtube" or "on youtube" in q_lower or "in youtube" in q_lower:
        clean_q = re.sub(r"\b(on|in|from)\s+youtube\b", "", query, flags=re.IGNORECASE).strip()
        return play_youtube(clean_q, autoplay=True)

    video_keywords = ["video", "clip", "trailer", "movie", "teaser", "tutorial", "stream", "live", "gameplay", "vlog"]
    if any(vk in q_lower for vk in video_keywords):
        return play_youtube(query, autoplay=True)

    if is_spotify_installed():
        music_keywords = ["song", "track", "album", "playlist", "artist", "beats", "lofi", "music", "spotify"]
        if any(mk in q_lower for mk in music_keywords):
            clean_q = re.sub(r"^(play|listen to)\s+", "", query, flags=re.IGNORECASE).strip()
            return play_spotify(clean_q)

    clean_q = re.sub(r"^(play|watch|listen to)\s+", "", query, flags=re.IGNORECASE).strip()
    return play_youtube(clean_q or query, autoplay=True)
