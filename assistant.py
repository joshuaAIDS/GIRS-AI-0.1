"""
IGIRS Assistant Controller.
Glues together the LLM Client, Memory Manager, Tool Engine, TTS Voice Engine, STT Listener, and Prompting.
Features smart Intent Routing to prevent hallucinated/unwanted tool calls.
"""
import sys
import re
import json
import logging
from typing import Dict, Any, List, Optional, Callable, Tuple

# Ensure UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import config
from llm.nvidia_client import NvidiaLLMClient
from llm.prompts import build_system_prompt
from memory.manager import MemoryManager
from tools.registry import ToolRegistry
from tts import TTSEngine
from stt import VoiceListener, WakeWordDetector

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(asctime)s - %(name)s: %(message)s")
logger = logging.getLogger("IGIRS.Assistant")

class IGIRSAssistant:
    def __init__(self):
        self.memory = MemoryManager()
        self.llm = NvidiaLLMClient()
        self.tts = TTSEngine(memory_manager=self.memory)
        self.tools = ToolRegistry(memory_manager=self.memory, llm_client=self.llm, tts_engine=self.tts)
        self.stt = VoiceListener()
        self.wake_word = WakeWordDetector()
        logger.info(f"Initialized {config.ASSISTANT_NAME} for {self.memory.user_name}")

    def get_system_prompt(self) -> str:
        """Constructs current dynamic system prompt."""
        return build_system_prompt(
            user_name=self.memory.user_name,
            facts=self.memory.get_facts()
        )

    def is_stop_listening_intent(self, text: str) -> bool:
        """Detects if user is commanding to stop listening or stop voice mode."""
        t = (text or "").lower().strip()
        stop_patterns = [
            r"\b(stop\s+(listen|listening|voice|always\s+listening|mic|microphone))\b",
            r"\b(turn\s+off\s+(listening|voice|mic))\b",
            r"\b(disable\s+(listening|voice))\b",
            r"\b(mute\s+(mic|microphone))\b",
            r"\b(hands\s*free\s+off)\b"
        ]
        return any(re.search(p, t) for p in stop_patterns) or t in [
            "stop listen", "stop listening", "stop voice", "mute mic", "stop mic", "cancel listening"
        ]

    def route_tools_for_input(self, user_input: str) -> Optional[List[Dict[str, Any]]]:
        """
        Determines if the user input requires tools.
        Returns filtered tool definitions or None if purely conversational.
        """
        text = user_input.lower().strip()

        # Purely conversational patterns that must NEVER trigger tools
        pure_chat_keywords = [
            "hi", "hello", "hey", "how are you", "who are you", "what are you",
            "speak in english", "speck in english", "talk in english",
            "what are you telling", "what are you saying", "what do you mean",
            "thanks", "thank you", "ok", "okay", "cool", "nice", "awesome",
            "good evening", "good night", "bye", "goodbye"
        ]

        # Exact match or simple greeting check
        if text in pure_chat_keywords or any(text == k for k in pure_chat_keywords):
            return None

        # Check for specific tool trigger intents
        selected_tool_names = set()

        # 1. System Telemetry
        if any(w in text for w in ["telemetry", "cpu", "ram usage", "battery", "system status", "computer specs", "system health", "பலகாரம்"]):
            selected_tool_names.add("get_system_telemetry")

        # 2. Time & Date
        if any(w in text for w in ["what time", "current time", "what is the time", "what's the time", "what date", "what day is today", "today's date", "நேரம்", "மணி என்ன"]):
            selected_tool_names.add("get_time_date")

        # 3. App Launch (Requires explicit command verbs like open/launch/start)
        if re.search(r"\b(open|launch|start)\s+(chrome|browser|vscode|code|notepad|calc|calculator|spotify|explorer|cmd|terminal)\b", text):
            selected_tool_names.add("open_application")

        # 4. Manage Notes
        if re.search(r"\b(take a note|take note|save note|add note|write down|my notes|show notes|list notes|clear notes)\b", text):
            selected_tool_names.add("manage_notes")

        # 5. Screen Vision & Multimodal Inspection
        screen_vision_triggers = [
            "screen", "on my screen", "look at my screen", "read my screen", "see my screen",
            "what am i looking at", "debug my screen", "what's on my screen", "what is on my screen",
            "read this error", "debug this error", "what error is this", "inspect screen",
            "inspect window", "read this window", "explain my screen", "read screen", "vision"
        ]
        if any(w in text for w in screen_vision_triggers) or (
            re.search(r"\b(look at|read|debug|inspect|explain|what is|what's)\b", text)
            and any(w in text for w in ["screen", "window", "error", "dialog", "terminal", "page"])
        ):
            selected_tool_names.add("analyze_screen")

        # 6. Media Playback (YouTube / Spotify)
        if (re.search(r"\b(play|listen to)\b", text) and any(w in text for w in ["youtube", "spotify", "music", "song", "track", "playlist", "lofi", "lo-fi", "beats", "video", "soundtrack"])) or "play " in text:
            selected_tool_names.add("play_media")

        # 7. Daily Briefing / Morning Routine
        if any(w in text for w in ["briefing", "daily briefing", "morning briefing", "status report", "brief me", "good morning"]):
            selected_tool_names.add("get_daily_briefing")

        # 8. Remember Fact
        if re.search(r"\b(remember that|my favorite|i live in|my name is)\b", text):
            selected_tool_names.add("remember_user_fact")

        # 9. Web Search (Explicit search commands)
        if re.search(r"\b(search for|search the web|search web|google|look up|who is|latest news on)\b", text):
            selected_tool_names.add("web_search")

        # --- Phase 1: Hardware & System Controls ---

        # 10. Volume & Sound
        if re.search(r"\b(volume|sound|louder|quieter|turn it up|turn it down|mute|unmute)\b", text):
            if "mute" in text or "unmute" in text:
                selected_tool_names.add("mute_volume")
            elif any(w in text for w in ["what", "check", "how high", "level"]) and "volume" in text:
                selected_tool_names.add("get_volume")
            else:
                selected_tool_names.add("set_volume")
                selected_tool_names.add("change_volume_relative")

        # 11. Screen Brightness
        if re.search(r"\b(brightness|dim the screen|dim screen|brighten screen)\b", text):
            if any(w in text for w in ["what", "check", "level"]) and "brightness" in text:
                selected_tool_names.add("get_brightness")
            else:
                selected_tool_names.add("set_brightness")
                selected_tool_names.add("get_brightness")

        # 12. Screenshot
        if re.search(r"\b(screenshot|capture screen|screen capture|take a snap|snap the screen)\b", text):
            selected_tool_names.add("take_screenshot")

        # 13. Lock Workstation
        if re.search(r"\b(lock (the )?(pc|computer|workstation|laptop|screen)|lock my (pc|computer|laptop))\b", text):
            selected_tool_names.add("lock_workstation")

        # 14. Minimize Windows / Show Desktop
        if re.search(r"\b(minimize\b|show desktop|go to desktop|toggle desktop|clear screen)\b", text):
            selected_tool_names.add("minimize_all_windows")

        # --- Phase 1: Productivity ---

        # 15. Voice Timers & Alarms
        if re.search(r"\b(timer|alarm|countdown|remind me in)\b", text):
            selected_tool_names.add("set_timer")

        # 16. Live Weather & Forecast
        if re.search(r"\b(weather|temperature|forecast|is it raining|will it rain|how hot|how cold)\b", text):
            selected_tool_names.add("get_live_weather")

        if not selected_tool_names:
            return None

        # Return only the relevant tool schemas
        all_tools = self.tools.get_tool_definitions()
        filtered = [t for t in all_tools if t["function"]["name"] in selected_tool_names]
        return filtered if filtered else None

    def process_message(
        self,
        user_input: str,
        on_tool_call: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        on_tool_result: Optional[Callable[[str, str], None]] = None,
        speak_response: bool = True
    ) -> str:
        """
        Processes a user message through the LLM, tool loop, and TTS engine.
        """
        user_input = user_input.strip()
        if not user_input:
            return ""

        # Stop prior speech upon new user input
        self.tts.stop()

        # Handle direct "stop listening" commands immediately
        if self.is_stop_listening_intent(user_input):
            stop_reply = f"I've stopped listening, {self.memory.user_name}. Tap the mic or continuous voice whenever you need me!"
            self.memory.add_user_message(user_input)
            self.memory.add_assistant_message(stop_reply)
            if speak_response:
                self.tts.speak(stop_reply)
            return stop_reply

        # 1. Add User message to memory
        self.memory.add_user_message(user_input)

        # 2. Prepare messages and tools for LLM
        system_prompt = self.get_system_prompt()
        messages = self.memory.get_messages_for_llm(system_prompt)
        
        # Route tools intelligently
        active_tools = self.route_tools_for_input(user_input)

        # 3. Call LLM
        response_data = self.llm.chat_completion(
            messages=messages,
            tools=active_tools
        )

        choices = response_data.get("choices", [])
        if not choices:
            fallback_msg = "I'm sorry, I couldn't generate a response."
            self.memory.add_assistant_message(fallback_msg)
            if speak_response:
                self.tts.speak(fallback_msg)
            return fallback_msg

        message = choices[0].get("message", {})
        tool_calls = message.get("tool_calls")
        content = message.get("content") or ""

        # 4. Handle Tool Calling if invoked
        if tool_calls and active_tools:
            self.memory.add_assistant_message(content, tool_calls=tool_calls)

            for tool_call in tool_calls:
                call_id = tool_call.get("id", "call_default")
                function = tool_call.get("function", {})
                fn_name = function.get("name", "")
                raw_args = function.get("arguments", "{}")
                
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except Exception:
                    args = {}

                if on_tool_call:
                    on_tool_call(fn_name, args)

                # Execute tool
                tool_output = self.tools.execute_tool(fn_name, args)

                if on_tool_result:
                    on_tool_result(fn_name, tool_output)

                # Add tool result to conversation history
                self.memory.add_tool_response(call_id, fn_name, tool_output)

            # If the only tool called was analyze_screen, the vision output is already the final complete analysis
            if len(tool_calls) == 1 and tool_calls[0].get("function", {}).get("name") == "analyze_screen":
                final_content = tool_output
                self.memory.add_assistant_message(final_content)
                if speak_response:
                    paragraphs = [p for p in final_content.split("\n\n") if p.strip()]
                    spoken = paragraphs[0].replace("*", "").replace("#", "").strip() if paragraphs else final_content
                    if len(spoken) > 280:
                        spoken = spoken[:280] + "..."
                    self.tts.speak(spoken)
                return final_content

            # 5. Call LLM again to get final answer incorporating tool outputs
            second_messages = self.memory.get_messages_for_llm(system_prompt)
            second_response = self.llm.chat_completion(
                messages=second_messages,
                tools=None
            )

            second_choices = second_response.get("choices", [])
            if second_choices:
                final_content = second_choices[0].get("message", {}).get("content", "")
            else:
                final_content = "Tool executed successfully."

            self.memory.add_assistant_message(final_content)
            if speak_response:
                self.tts.speak(final_content)
            return final_content

        else:
            # Sanitize any hallucinated raw JSON tool call from LLM content
            content_cleaned = content.strip()
            if content_cleaned.startswith("{") and content_cleaned.endswith("}"):
                try:
                    parsed = json.loads(content_cleaned)
                    if isinstance(parsed, dict) and ("name" in parsed or "function" in parsed or "action" in parsed or "tool" in parsed):
                        tool_fn = parsed.get("name") or parsed.get("function") or parsed.get("action")
                        if tool_fn in ["stop_listening", "stop_listen", "stop_voice", "mute"]:
                            content = f"I've stopped listening, {self.memory.user_name}. Tap the mic whenever you need me!"
                        elif tool_fn == "play_media":
                            args = parsed.get("parameters") or parsed.get("arguments") or {}
                            content = self.tools.execute_tool("play_media", args)
                        elif tool_fn == "analyze_screen":
                            args = parsed.get("parameters") or parsed.get("arguments") or {}
                            content = self.tools.execute_tool("analyze_screen", args)
                        else:
                            content = f"All set, {self.memory.user_name}!"
                except Exception:
                    pass

            # Direct text response
            self.memory.add_assistant_message(content)
            if speak_response:
                self.tts.speak(content)
            return content

    def listen_and_respond(
        self,
        timeout: int = 6,
        phrase_time_limit: int = 15,
        on_listening: Optional[Callable[[], None]] = None,
        on_transcribing: Optional[Callable[[], None]] = None,
        on_tool_call: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        on_tool_result: Optional[Callable[[str, str], None]] = None,
        speak_response: bool = True
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Listens to the microphone, transcribes speech, and processes the response.
        Returns (transcribed_user_text, assistant_reply_text).
        """
        transcribed_text = self.stt.listen_and_transcribe(
            timeout=timeout,
            phrase_time_limit=phrase_time_limit,
            on_listening=on_listening,
            on_transcribing=on_transcribing
        )

        if not transcribed_text:
            return None, None

        # Process message through AI assistant
        reply = self.process_message(
            user_input=transcribed_text,
            on_tool_call=on_tool_call,
            on_tool_result=on_tool_result,
            speak_response=speak_response
        )

        return transcribed_text, reply
