"""
JavaScript-Python Bridge API for IGIRS AI Desktop GUI.
Exposes assistant methods, live telemetry, Fact Vault, and voice controls to pywebview.
Uses private attributes to prevent pywebview from recursively introspecting native window objects.
"""
import logging
from typing import Dict, Any, List, Optional
import config
from assistant import IGIRSAssistant

logger = logging.getLogger("IGIRS.Bridge")

class DesktopApiBridge:
    def __init__(self, assistant: IGIRSAssistant, window=None):
        self._assistant = assistant
        self._window = window
        # Hook barge-in event to GUI voice state
        if self._assistant and hasattr(self._assistant, "tts") and self._assistant.tts:
            self._assistant.tts.set_on_barge_in(self._on_barge_in_fired)

    def _on_barge_in_fired(self):
        """Called immediately when user speaks over assistant speech."""
        logger.info("Bridge: Voice Barge-In triggered, transitioning GUI to listening.")
        self.notify_state("listening")

    def set_window(self, window):
        self._window = window

    def notify_state(self, state: str):
        """Notifies frontend JS of state changes (standby, listening, thinking, speaking)."""
        if self._window:
            try:
                self._window.evaluate_js(f"if (window.setVoiceState) window.setVoiceState('{state}')")
            except Exception as e:
                logger.debug(f"Error evaluating state JS: {e}")

    def send_message(self, user_input: str) -> Dict[str, Any]:
        """
        Processes a text message from GUI input.
        Returns response text and tool invocation logs.
        """
        user_input = user_input.strip()
        if not user_input:
            return {"status": "empty", "response": ""}

        tool_logs = []

        def on_tool_call(name: str, args: dict):
            self.notify_state("thinking")
            tool_logs.append({"type": "call", "name": name, "args": args})

        def on_tool_result(name: str, result: str):
            tool_logs.append({"type": "result", "name": name, "result": result})

        self.notify_state("thinking")
        
        reply = self._assistant.process_message(
            user_input=user_input,
            on_tool_call=on_tool_call,
            on_tool_result=on_tool_result,
            speak_response=True
        )

        self.notify_state("speaking" if self._assistant.tts.enabled else "standby")

        is_stop = self._assistant.is_stop_listening_intent(user_input)

        return {
            "status": "success",
            "user_input": user_input,
            "response": reply,
            "tool_logs": tool_logs,
            "user_name": self._assistant.memory.user_name,
            "stop_listening": is_stop
        }

    def trigger_voice(self) -> Dict[str, Any]:
        """
        Listens to microphone, transcribes speech, and processes command.
        """
        self.notify_state("listening")
        
        tool_logs = []
        def on_tool_call(name: str, args: dict):
            self.notify_state("thinking")
            tool_logs.append({"type": "call", "name": name, "args": args})

        def on_tool_result(name: str, result: str):
            tool_logs.append({"type": "result", "name": name, "result": result})

        def on_transcribing():
            self.notify_state("thinking")

        user_text, reply = self._assistant.listen_and_respond(
            on_transcribing=on_transcribing,
            on_tool_call=on_tool_call,
            on_tool_result=on_tool_result,
            speak_response=True
        )

        if not user_text:
            self.notify_state("standby")
            return {"status": "timeout", "message": "No speech detected."}

        self.notify_state("speaking" if self._assistant.tts.enabled else "standby")

        is_stop = self._assistant.is_stop_listening_intent(user_text)

        return {
            "status": "success",
            "user_input": user_text,
            "response": reply,
            "tool_logs": tool_logs,
            "user_name": self._assistant.memory.user_name,
            "stop_listening": is_stop
        }

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns live CPU, RAM, and Battery data for HUD gauges."""
        return self._assistant.tools._tool_system_telemetry()

    def get_facts(self) -> List[str]:
        """Returns all saved memory facts."""
        return self._assistant.memory.get_facts()

    def add_fact(self, fact: str) -> bool:
        """Adds a new fact to memory."""
        return self._assistant.memory.add_fact(fact)

    def remove_fact(self, fact_or_index: Any) -> bool:
        """Removes a fact from memory."""
        return self._assistant.memory.remove_fact(fact_or_index)

    def get_notes(self) -> List[Dict[str, Any]]:
        """Returns saved notes."""
        result = self._assistant.tools._tool_manage_notes(action="list")
        return result.get("notes", [])

    def add_note(self, note: str) -> Dict[str, Any]:
        """Saves a new note."""
        return self._assistant.tools._tool_manage_notes(action="add", note=note)

    def clear_history(self) -> bool:
        """Clears active conversation context."""
        self._assistant.memory.clear_history()
        return True

    def get_voice_settings(self) -> Dict[str, Any]:
        """Returns active voice settings including barge-in and audio cues."""
        tts = self._assistant.tts
        import utils.audio_cues as audio_cues
        return {
            "enabled": tts.enabled,
            "volume": tts.volume,
            "rate": tts.rate,
            "english_voice": tts.english_voice,
            "tamil_voice": tts.tamil_voice,
            "barge_in": tts.is_barge_in_enabled(),
            "audio_cues": audio_cues.is_cues_enabled(),
            "available_voices": tts.list_voices()
        }

    def update_voice_settings(self, settings: Dict[str, Any]) -> bool:
        """Updates voice settings from GUI."""
        tts = self._assistant.tts
        if "enabled" in settings:
            tts.set_enabled(settings["enabled"])
        if "volume" in settings:
            tts.set_volume(settings["volume"])
        if "rate" in settings:
            tts.set_rate(settings["rate"])
        if "english_voice" in settings:
            tts.set_voice(settings["english_voice"])
        if "tamil_voice" in settings:
            tts.set_voice(settings["tamil_voice"])
        if "barge_in" in settings:
            tts.set_barge_in_enabled(bool(settings["barge_in"]))
        if "audio_cues" in settings:
            import utils.audio_cues as audio_cues
            audio_cues.set_cues_enabled(bool(settings["audio_cues"]))
        return True

    def toggle_barge_in(self) -> bool:
        """Toggles voice barge-in on/off."""
        tts = self._assistant.tts
        new_val = not tts.is_barge_in_enabled()
        tts.set_barge_in_enabled(new_val)
        return new_val

    def toggle_audio_cues(self) -> bool:
        """Toggles procedural audio cues on/off."""
        import utils.audio_cues as audio_cues
        new_val = not audio_cues.is_cues_enabled()
        audio_cues.set_cues_enabled(new_val)
        return new_val

    def stop_speech(self) -> bool:
        """Halts active audio playback."""
        self._assistant.tts.stop(play_cue=True)
        self.notify_state("standby")
        return True

    def is_speaking(self) -> bool:
        """Returns True if voice audio is actively playing."""
        return self._assistant.tts.is_speaking()

    # --- Media Controls Bridge ---

    def play_media(self, query: str, platform: str = "auto") -> Dict[str, Any]:
        """Plays music or video via Spotify or YouTube."""
        import tools.media_controls as media_controls
        return media_controls.play_media(query=query, platform=platform)

    def control_media(self, action: str) -> Dict[str, Any]:
        """Controls global Windows media playback (play, pause, next, previous, stop)."""
        import tools.media_controls as media_controls
        return media_controls.control_media(action=action)

    def is_spotify_installed(self) -> bool:
        """Checks if Spotify is installed on this machine."""
        import tools.media_controls as media_controls
        return media_controls.is_spotify_installed()

    def play_spotify(self, query: str = "") -> Dict[str, Any]:
        """Plays track/artist/playlist on Spotify."""
        import tools.media_controls as media_controls
        return media_controls.play_spotify(query=query)

    def play_youtube(self, query: str, autoplay: bool = True) -> Dict[str, Any]:
        """Searches YouTube and plays top video with autoplay."""
        import tools.media_controls as media_controls
        return media_controls.play_youtube(query=query, autoplay=autoplay)
