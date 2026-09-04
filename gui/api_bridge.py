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
        """Returns active voice settings."""
        tts = self._assistant.tts
        return {
            "enabled": tts.enabled,
            "volume": tts.volume,
            "rate": tts.rate,
            "english_voice": tts.english_voice,
            "tamil_voice": tts.tamil_voice,
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
        return True

    def stop_speech(self) -> bool:
        """Halts active audio playback."""
        self._assistant.tts.stop()
        self.notify_state("standby")
        return True

    def is_speaking(self) -> bool:
        """Returns True if voice audio is actively playing."""
        return self._assistant.tts.is_speaking()
