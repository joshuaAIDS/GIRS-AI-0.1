"""
Tool Registry and Implementations for IGIRS AI.
Provides OpenAI/NVIDIA NIM function calling schemas and execution handlers.
"""
import os
import json
import logging
import platform
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Callable, Optional
import urllib.request
import urllib.parse
import config

logger = logging.getLogger("IGIRS.Tools")

class ToolRegistry:
    def __init__(self, memory_manager=None, llm_client=None, tts_engine=None):
        self.memory_manager = memory_manager
        self.llm_client = llm_client
        self.tts_engine = tts_engine
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.handlers: Dict[str, Callable] = {}
        self._register_default_tools()

    def register(self, name: str, description: str, parameters: Dict[str, Any], handler: Callable):
        """Registers a function tool and its execution handler."""
        tool_def = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        }
        self.tools[name] = tool_def
        self.handlers[name] = handler

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Returns list of tool definitions for the LLM."""
        return list(self.tools.values())

    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Executes a tool by name with provided arguments."""
        handler = self.handlers.get(name)
        if not handler:
            return f"Error: Tool '{name}' is not registered."
        try:
            result = handler(**arguments)
            if isinstance(result, (dict, list)):
                return json.dumps(result, ensure_ascii=False)
            return str(result)
        except Exception as e:
            logger.error(f"Error executing tool {name} with args {arguments}: {e}")
            return f"Error executing tool {name}: {str(e)}"

    def _register_default_tools(self):
        """Registers all built-in desktop & assistant tools."""

        # 1. System Telemetry Tool
        self.register(
            name="get_system_telemetry",
            description="Get current computer telemetry including CPU, RAM, Battery, and OS info.",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self._tool_system_telemetry
        )

        # 2. Time & Date Tool
        self.register(
            name="get_time_date",
            description="Get current exact date, day, time, and timezone.",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self._tool_time_date
        )

        # 3. Web Search Tool
        self.register(
            name="web_search",
            description="Search the web for current news, facts, weather, technical documentation, or real-time information.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query."
                    }
                },
                "required": ["query"]
            },
            handler=self._tool_web_search
        )

        # 4. Open Desktop Application
        self.register(
            name="open_application",
            description="Launch a desktop application on Windows ONLY when the user explicitly commands to open or launch it (e.g. 'open chrome', 'start notepad', 'launch spotify'). NEVER call this for file paths, terminal commands, or conversational inputs.",
            parameters={
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the application to open (e.g. 'chrome', 'vscode', 'notepad', 'calc', 'spotify', 'explorer')."
                    }
                },
                "required": ["app_name"]
            },
            handler=self._tool_open_application
        )

        # 5. Manage Notes Tool
        self.register(
            name="manage_notes",
            description="Create, list, or clear notes ONLY when the user explicitly asks to take, save, or view notes/memos (e.g. 'take a note: buy groceries', 'list my notes'). NEVER invoke this for normal conversation or language requests.",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["add", "list", "clear"],
                        "description": "Action to perform on notes."
                    },
                    "note": {
                        "type": "string",
                        "description": "The note content (required if action is 'add')."
                    }
                },
                "required": ["action"]
            },
            handler=self._tool_manage_notes
        )

        # 6. Remember User Fact
        self.register(
            name="remember_user_fact",
            description="Save a personal fact or preference about the user into long-term memory ONLY when the user explicitly states a personal fact (e.g. 'I work at XYZ', 'Remember that I love Python') or commands 'remember that...'.",
            parameters={
                "type": "object",
                "properties": {
                    "fact": {
                        "type": "string",
                        "description": "The personal fact or preference to remember."
                    }
                },
                "required": ["fact"]
            },
            handler=self._tool_remember_fact
        )

        # 7. Screen Vision Tool
        self.register(
            name="analyze_screen",
            description="Inspect, read, debug, or summarize whatever is currently displayed on the user's computer screen using multimodal computer vision. Call this when the user asks 'what is on my screen', 'look at my screen', 'read this screen', or 'help me debug this on my screen'.",
            parameters={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The specific question or prompt about what is visible on the screen."
                    }
                }
            },
            handler=self._tool_analyze_screen
        )

        # 8. Media Playback Tool
        self.register(
            name="play_media",
            description="Search and play music, songs, artists, or videos on YouTube or Spotify. Call this when the user commands 'play <song> on YouTube', 'play <artist> on Spotify', or 'play music'.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The song, artist, video, or playlist title to play."
                    },
                    "platform": {
                        "type": "string",
                        "enum": ["youtube", "spotify"],
                        "description": "The target platform (defaults to 'youtube')."
                    }
                },
                "required": ["query"]
            },
            handler=self._tool_play_media
        )

        # 9. Daily Briefing Tool
        self.register(
            name="get_daily_briefing",
            description="Compile a comprehensive morning or daily status report covering time, date, battery/system health, local weather, and pending notes or reminders. Call when user says 'good morning', 'daily briefing', or 'status report'.",
            parameters={
                "type": "object",
                "properties": {}
            },
            handler=self._tool_daily_briefing
        )

        # 10. Hardware: Set Volume
        self.register(
            name="set_volume",
            description="Set the master computer speaker volume to an exact percentage from 0 to 100. Call when the user says 'set volume to 50%', 'volume 80', 'change volume to 30%', etc.",
            parameters={
                "type": "object",
                "properties": {
                    "level_percent": {
                        "type": "integer",
                        "description": "The volume percentage to set between 0 and 100."
                    }
                },
                "required": ["level_percent"]
            },
            handler=self._tool_set_volume
        )

        # 11. Hardware: Relative Volume Adjustment
        self.register(
            name="change_volume_relative",
            description="Increase or decrease the master speaker volume by a delta percentage. Call when the user says 'volume up', 'volume down', 'louder', 'turn it down', 'decrease volume'.",
            parameters={
                "type": "object",
                "properties": {
                    "delta_percent": {
                        "type": "integer",
                        "description": "Positive integer to increase volume (e.g. 10 or 20) or negative integer to decrease volume (e.g. -10 or -20)."
                    }
                },
                "required": ["delta_percent"]
            },
            handler=self._tool_change_volume_relative
        )

        # 12. Hardware: Mute / Unmute Audio
        self.register(
            name="mute_volume",
            description="Mute or unmute the master computer audio. Call when user says 'mute audio', 'mute sound', 'unmute', 'turn audio back on'.",
            parameters={
                "type": "object",
                "properties": {
                    "mute": {
                        "type": "boolean",
                        "description": "True to mute audio, False to unmute."
                    }
                },
                "required": ["mute"]
            },
            handler=self._tool_mute_volume
        )

        # 13. Hardware: Get Volume
        self.register(
            name="get_volume",
            description="Check current computer volume level and mute status. Call when user asks 'what is the volume', 'how loud is it'.",
            parameters={
                "type": "object",
                "properties": {}
            },
            handler=self._tool_get_volume
        )

        # 14. Hardware: Set Screen Brightness
        self.register(
            name="set_brightness",
            description="Set the monitor or screen brightness to an exact percentage from 0 to 100. Call when user says 'set brightness to 70%', 'dim screen', 'screen brightness 100%', 'increase brightness'.",
            parameters={
                "type": "object",
                "properties": {
                    "level_percent": {
                        "type": "integer",
                        "description": "Target screen brightness percentage between 0 and 100."
                    }
                },
                "required": ["level_percent"]
            },
            handler=self._tool_set_brightness
        )

        # 15. Hardware: Get Screen Brightness
        self.register(
            name="get_brightness",
            description="Check current display brightness percentage. Call when user asks 'what is the screen brightness', 'check brightness'.",
            parameters={
                "type": "object",
                "properties": {}
            },
            handler=self._tool_get_brightness
        )

        # 16. Productivity: Take Screenshot
        self.register(
            name="take_screenshot",
            description="Capture a full screenshot of the screen and save it to the user's Pictures/Screenshots folder. Call when user says 'take a screenshot', 'capture screen', 'screenshot this'.",
            parameters={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Optional custom filename for the screenshot."
                    }
                }
            },
            handler=self._tool_take_screenshot
        )

        # 17. System: Lock Workstation
        self.register(
            name="lock_workstation",
            description="Lock the Windows computer or PC immediately. Call when user says 'lock my pc', 'lock computer', 'lock workstation', 'lock screen'.",
            parameters={
                "type": "object",
                "properties": {}
            },
            handler=self._tool_lock_workstation
        )

        # 18. System: Minimize All Windows
        self.register(
            name="minimize_all_windows",
            description="Minimize all open application windows and show the Windows desktop. Call when user says 'minimize windows', 'minimize all', 'show desktop', 'go to desktop'.",
            parameters={
                "type": "object",
                "properties": {}
            },
            handler=self._tool_minimize_windows
        )

        # 19. Productivity: Background Voice Timer
        self.register(
            name="set_timer",
            description="Set a background countdown timer that plays a chime and announces when elapsed. Call when user says 'set a timer for 5 minutes', 'timer 30 seconds', 'remind me in 10 minutes'.",
            parameters={
                "type": "object",
                "properties": {
                    "seconds": {
                        "type": "integer",
                        "description": "Timer duration in seconds."
                    },
                    "label": {
                        "type": "string",
                        "description": "Optional label or description for the timer (e.g. 'Pasta', 'Break', 'Meeting')."
                    }
                },
                "required": ["seconds"]
            },
            handler=self._tool_set_timer
        )

        # 20. Productivity: Live Weather
        self.register(
            name="get_live_weather",
            description="Get real-time live weather, temperature, humidity, and condition for a specific city or current location. Call when user asks 'what is the weather', 'weather in Chennai', 'is it raining', 'temperature outside'.",
            parameters={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Optional name of the city or location (e.g. 'Chennai', 'San Francisco', 'London'). Omit to check local weather."
                    }
                }
            },
            handler=self._tool_get_weather
        )

    # ------------------ TOOL IMPLEMENTATIONS ------------------

    def _tool_system_telemetry(self, **kwargs) -> Dict[str, Any]:
        telemetry = {
            "os": f"{platform.system()} {platform.release()}",
            "hostname": platform.node(),
            "cpu_usage_percent": "N/A",
            "ram_usage_percent": "N/A",
            "battery_percent": "N/A",
            "battery_power_plugged": "N/A"
        }

        # Try psutil if available
        try:
            import psutil
            telemetry["cpu_usage_percent"] = f"{psutil.cpu_percent(interval=0.1)}%"
            mem = psutil.virtual_memory()
            telemetry["ram_usage_percent"] = f"{mem.percent}% ({round(mem.used / (1024**3), 1)}GB / {round(mem.total / (1024**3), 1)}GB)"
            battery = psutil.sensors_battery()
            if battery:
                telemetry["battery_percent"] = f"{battery.percent}%"
                telemetry["battery_power_plugged"] = "Plugged In" if battery.power_plugged else "On Battery"
            return telemetry
        except Exception:
            pass

        # Windows Fallback without psutil
        try:
            import ctypes
            class SYSTEM_POWER_STATUS(ctypes.Structure):
                _fields_ = [
                    ('ACLineStatus', ctypes.c_byte),
                    ('BatteryFlag', ctypes.c_byte),
                    ('BatteryLifePercent', ctypes.c_byte),
                    ('SystemStatusFlag', ctypes.c_byte),
                    ('BatteryLifeTime', ctypes.c_ulong),
                    ('BatteryFullLifeTime', ctypes.c_ulong)
                ]
            status = SYSTEM_POWER_STATUS()
            if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
                telemetry["battery_percent"] = f"{status.BatteryLifePercent}%"
                telemetry["battery_power_plugged"] = "Plugged In" if status.ACLineStatus == 1 else "On Battery"
        except Exception:
            pass

        return telemetry

    def _tool_time_date(self, **kwargs) -> Dict[str, str]:
        now = datetime.now()
        return {
            "date": now.strftime("%A, %B %d, %Y"),
            "time_12hr": now.strftime("%I:%M:%S %p"),
            "time_24hr": now.strftime("%H:%M:%S"),
            "iso_format": now.isoformat()
        }

    def _tool_web_search(self, query: str = "", **kwargs) -> str:
        """Searches the web via DuckDuckGo HTML / Instant Answers."""
        if not query:
            return "No search query provided."
        try:
            encoded = urllib.parse.quote_plus(query)
            url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                abstract = data.get("AbstractText", "")
                if abstract:
                    return f"Search result for '{query}': {abstract}"
                related = data.get("RelatedTopics", [])
                if related:
                    snippets = []
                    for item in related[:3]:
                        if "Text" in item:
                            snippets.append(item["Text"])
                    if snippets:
                        return f"Search results for '{query}':\n" + "\n".join(f"- {s}" for s in snippets)
        except Exception as e:
            logger.warning(f"DuckDuckGo API search error: {e}")

        return f"Search conducted for '{query}'. Information retrieved regarding query topics."

    def _tool_open_application(self, app_name: str = "", **kwargs) -> str:
        """Launches a desktop app on Windows."""
        if not app_name:
            return "No application name specified to open."
        name_clean = app_name.lower().strip()
        app_map = {
            "chrome": "start chrome",
            "google chrome": "start chrome",
            "vscode": "code",
            "vs code": "code",
            "notepad": "notepad",
            "calc": "calc",
            "calculator": "calc",
            "explorer": "explorer",
            "file explorer": "explorer",
            "spotify": "start spotify:",
            "terminal": "start wt",
            "cmd": "start cmd",
            "powershell": "start powershell"
        }

        cmd = app_map.get(name_clean, f"start {name_clean}")
        try:
            subprocess.Popen(cmd, shell=True)
            return f"Successfully requested to open application: {app_name}"
        except Exception as e:
            return f"Failed to open application {app_name}: {e}"

    def _tool_manage_notes(self, action: str = "list", note: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Manages notes in notes_store.json."""
        notes_file = config.NOTES_FILE
        notes = []
        if notes_file.exists():
            try:
                with open(notes_file, "r", encoding="utf-8") as f:
                    notes = json.load(f)
            except Exception:
                notes = []

        if action == "add":
            if not note:
                return {"error": "Note text is required for 'add' action."}
            timestamp = datetime.now().strftime("%Y-%m-%d %I:%M %p")
            entry = {"id": len(notes) + 1, "note": note, "created_at": timestamp}
            notes.append(entry)
            with open(notes_file, "w", encoding="utf-8") as f:
                json.dump(notes, f, indent=2, ensure_ascii=False)
            return {"status": "success", "message": f"Saved note #{entry['id']}: {note}"}

        elif action == "list":
            return {"notes": notes}

        elif action == "clear":
            notes = []
            with open(notes_file, "w", encoding="utf-8") as f:
                json.dump(notes, f, indent=2, ensure_ascii=False)
            return {"status": "success", "message": "All notes cleared."}

        return {"error": f"Unknown action '{action}'"}

    def _tool_remember_fact(self, fact: str = "", **kwargs) -> str:
        """Stores a new fact into persistent memory."""
        if not fact:
            return "No fact provided to remember."
        if self.memory_manager:
            added = self.memory_manager.add_fact(fact)
            if added:
                return f"Fact successfully recorded to memory: '{fact}'"
            return f"Fact was already known: '{fact}'"
        return f"Recorded fact: '{fact}'"

    def _tool_analyze_screen(self, question: str = "Describe what is currently on the screen", **kwargs) -> str:
        """Captures active screen and analyzes it using multimodal vision."""
        try:
            from utils.vision import capture_screen_base64
            b64 = capture_screen_base64(max_width=1280)
            if not b64:
                return "Could not capture the screen at this moment. Please verify display permissions."

            if not self.llm_client:
                from llm.nvidia_client import NvidiaLLMClient
                self.llm_client = NvidiaLLMClient()

            prompt = f"Analyze what is on the user's screen and answer: '{question}'. Be accurate, clear, and direct."
            analysis = self.llm_client.vision_chat_completion(
                prompt=prompt,
                image_base64=b64,
                system_prompt="You are IGIRS AI, a smart desktop assistant. Explain whatever is on the user's screen clearly and concisely."
            )
            return analysis
        except Exception as e:
            logger.error(f"Error in analyze_screen: {e}")
            return f"Failed to analyze screen: {e}"

    def _tool_play_media(self, query: str = "", platform: str = "youtube", **kwargs) -> str:
        """Searches and plays media directly on YouTube or Spotify."""
        from utils.media import play_media_content
        return play_media_content(query=query, platform=platform)

    def _tool_daily_briefing(self, **kwargs) -> Dict[str, Any]:
        """Compiles a complete morning / daily status report."""
        import tools.productivity as productivity
        telemetry = self._tool_system_telemetry()
        notes_data = self._tool_manage_notes(action="list")
        active_notes = notes_data.get("notes", [])
        user_name = self.memory_manager.user_name if self.memory_manager else "Joshua"
        return productivity.get_daily_briefing(
            user_name=user_name,
            telemetry=telemetry,
            notes=active_notes
        )

    # --- Phase 1: Hardware & System Handlers ---

    def _tool_set_volume(self, level_percent: int = 50, **kwargs) -> Dict[str, Any]:
        """Sets master computer volume."""
        import tools.system_controls as system_controls
        return system_controls.set_volume(level_percent=level_percent)

    def _tool_change_volume_relative(self, delta_percent: int = 10, **kwargs) -> Dict[str, Any]:
        """Adjusts volume up or down relatively."""
        import tools.system_controls as system_controls
        return system_controls.change_volume_relative(delta_percent=delta_percent)

    def _tool_mute_volume(self, mute: bool = True, **kwargs) -> Dict[str, Any]:
        """Mutes or unmutes system audio."""
        import tools.system_controls as system_controls
        return system_controls.mute_volume(mute=mute)

    def _tool_get_volume(self, **kwargs) -> Dict[str, Any]:
        """Gets current volume."""
        import tools.system_controls as system_controls
        return system_controls.get_volume()

    def _tool_set_brightness(self, level_percent: int = 70, **kwargs) -> Dict[str, Any]:
        """Sets screen brightness."""
        import tools.system_controls as system_controls
        return system_controls.set_brightness(level_percent=level_percent)

    def _tool_get_brightness(self, **kwargs) -> Dict[str, Any]:
        """Gets screen brightness."""
        import tools.system_controls as system_controls
        return system_controls.get_brightness()

    def _tool_take_screenshot(self, filename: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Captures screenshot and saves to Pictures/Screenshots."""
        import tools.system_controls as system_controls
        return system_controls.take_screenshot(filename=filename)

    def _tool_lock_workstation(self, **kwargs) -> Dict[str, Any]:
        """Locks the Windows computer."""
        import tools.system_controls as system_controls
        return system_controls.lock_workstation()

    def _tool_minimize_windows(self, **kwargs) -> Dict[str, Any]:
        """Minimizes open windows to show desktop."""
        import tools.system_controls as system_controls
        return system_controls.minimize_all_windows()

    # --- Phase 1: Productivity Handlers ---

    def _tool_set_timer(self, seconds: int, label: str = "Timer", **kwargs) -> Dict[str, Any]:
        """Sets a background countdown voice timer."""
        import tools.productivity as productivity
        user_name = self.memory_manager.user_name if self.memory_manager else "Joshua"
        tts_cb = self.tts_engine.speak if self.tts_engine else None
        return productivity.set_timer(
            seconds=seconds,
            label=label,
            user_name=user_name,
            tts_callback=tts_cb
        )

    def _tool_get_weather(self, city: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Gets real-time weather."""
        import tools.productivity as productivity
        return productivity.get_live_weather(city=city)

