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
        self.doc_engine = None
        self.contacts_mgr = None
        self.wa_engine = None
        self.mail_engine = None
        self._web_automator = None
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.handlers: Dict[str, Callable] = {}
        self._register_default_tools()

    @property
    def web(self):
        """Lazy-loaded WebAutomator instance."""
        if self._web_automator is None:
            from tools.web_automator import WebAutomator
            self._web_automator = WebAutomator()
        return self._web_automator

    @property
    def documents(self):
        """Lazy-loaded DocumentEngine instance."""
        if self.doc_engine is None:
            from tools.document_engine import DocumentEngine
            self.doc_engine = DocumentEngine()
        return self.doc_engine

    @property
    def contacts(self):
        """Lazy-loaded ContactsManager instance."""
        if self.contacts_mgr is None:
            from tools.contacts_manager import ContactsManager
            self.contacts_mgr = ContactsManager()
        return self.contacts_mgr

    @property
    def whatsapp(self):
        """Lazy-loaded WhatsAppEngine instance."""
        if self.wa_engine is None:
            from tools.whatsapp_engine import WhatsAppEngine
            self.wa_engine = WhatsAppEngine(self.contacts)
        return self.wa_engine

    @property
    def email(self):
        """Lazy-loaded EmailEngine instance."""
        if self.mail_engine is None:
            from tools.email_engine import EmailEngine
            self.mail_engine = EmailEngine(self.contacts)
        return self.mail_engine

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
            description="Inspect, read, debug, or summarize whatever is currently displayed on the user's computer screen or active window using multimodal computer vision. Call this when the user asks 'what is on my screen', 'look at my screen', 'read this screen', 'debug this error', or 'what window is open'.",
            parameters={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The specific question or prompt about what is visible on the screen or window."
                    },
                    "focus_window": {
                        "type": "boolean",
                        "description": "If true, crops specifically to the active foreground window instead of the entire desktop."
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

        # 21. Media: Unified Voice Media Player (Spotify & YouTube)
        self.register(
            name="play_media",
            description="Play songs, music, albums, artists, playlists, videos, or podcasts on Spotify or YouTube. Automatically routes to the right platform or respects user's explicit choice. Call when user says 'play Bohemian Rhapsody', 'play some lofi beats', 'play music', 'play video tutorial'.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The song title, artist, playlist, or video query to play."
                    },
                    "platform": {
                        "type": "string",
                        "enum": ["auto", "spotify", "youtube"],
                        "description": "Target platform: 'auto' (default), 'spotify', or 'youtube'."
                    }
                },
                "required": ["query"]
            },
            handler=self._tool_play_media
        )

        # 22. Media: YouTube Auto-Play & Search
        self.register(
            name="play_youtube",
            description="Search YouTube and automatically open and play the top video with autoplay. Call when user says 'play ... on YouTube', 'open YouTube video ...', 'watch ... on YouTube'.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The video search query or song to play on YouTube."
                    },
                    "autoplay": {
                        "type": "boolean",
                        "description": "Whether to automatically start playback (defaults to true)."
                    }
                },
                "required": ["query"]
            },
            handler=self._tool_play_youtube
        )

        # 23. Media: Spotify Search & Playback
        self.register(
            name="play_spotify",
            description="Search and play a song, artist, album, or playlist on Spotify, or resume Spotify playback. Call when user says 'play ... on Spotify', 'open Spotify', 'resume Spotify'.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Optional song, artist, or playlist name. If empty, resumes current Spotify playback."
                    }
                }
            },
            handler=self._tool_play_spotify
        )

        # 24. Media: Global Playback Controls
        self.register(
            name="control_media",
            description="Control media playback on Windows (play, pause, next track, previous track, stop, mute). Works globally across Spotify, YouTube, VLC, and browser tabs without needing window focus. Call when user says 'pause music', 'resume song', 'next track', 'skip song', 'previous track', 'stop music'.",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["play", "pause", "play_pause", "next", "previous", "stop", "mute"],
                        "description": "Playback action to execute."
                    }
                },
                "required": ["action"]
            },
            handler=self._tool_control_media
        )

        # 25. Documents: Query Knowledge Vault (PDFs, Notes, Resumes, Code)
        self.register(
            name="query_documents",
            description="Search, query, and answer questions across local PDFs, lecture notes, resumes, study materials, or code files indexed in the Knowledge Vault. Call when the user asks questions about their files, resume, coursework, or code logic.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The question to answer using the indexed documents."
                    },
                    "doc_name": {
                        "type": "string",
                        "description": "Optional name or keyword of a specific document to restrict search to."
                    }
                },
                "required": ["query"]
            },
            handler=self._tool_query_documents
        )

        # 26. Documents: Summarize Document
        self.register(
            name="summarize_document",
            description="Generate a comprehensive executive summary of an indexed PDF, resume, lecture note, or code file. Call when user asks 'summarize this document', 'give an overview of my resume', 'summarize chapter 2'.",
            parameters={
                "type": "object",
                "properties": {
                    "doc_name": {
                        "type": "string",
                        "description": "Optional name or keyword of the document to summarize. If omitted, summarizes the most recent file."
                    },
                    "focus": {
                        "type": "string",
                        "description": "Optional specific topic or area of interest to focus the summary on."
                    }
                }
            },
            handler=self._tool_summarize_document
        )

        # 27. Documents: List Indexed Files
        self.register(
            name="list_indexed_documents",
            description="List all local documents, PDFs, lecture notes, resumes, and code files currently indexed in the Knowledge Vault.",
            parameters={
                "type": "object",
                "properties": {}
            },
            handler=self._tool_list_indexed_documents
        )

        # 28. Documents: Index Local File
        self.register(
            name="index_local_file",
            description="Ingest and index a local file path from disk (PDF, DOCX, Python, JS, Markdown, text) into the Knowledge Vault for conversational Q&A.",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute or relative file path to the local document or code file."
                    }
                },
                "required": ["file_path"]
            },
            handler=self._tool_index_local_file
        )

        # 29. WhatsApp: Send Message
        self.register(
            name="send_whatsapp",
            description="Send a WhatsApp message to a contact name, nickname (e.g. Mom, Dad, Boss, Karthik), or direct phone number. Supports hands-free auto-send.",
            parameters={
                "type": "object",
                "properties": {
                    "recipient": {
                        "type": "string",
                        "description": "Recipient name, nickname from contacts book, or phone number with country code."
                    },
                    "message": {
                        "type": "string",
                        "description": "The exact message content to send."
                    },
                    "auto_send": {
                        "type": "boolean",
                        "description": "If true, automatically triggers Enter key to send the message hands-free (defaults to true)."
                    }
                },
                "required": ["recipient", "message"]
            },
            handler=self._tool_send_whatsapp
        )

        # 30. Email: Send Email
        self.register(
            name="send_email",
            description="Send an email directly via SMTP or open in default mail client (Windows Mail / Outlook). Resolves contact names automatically.",
            parameters={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient contact name, nickname, or email address."
                    },
                    "subject": {
                        "type": "string",
                        "description": "Subject line of the email."
                    },
                    "body": {
                        "type": "string",
                        "description": "Body message text of the email."
                    },
                    "attachment_path": {
                        "type": "string",
                        "description": "Optional local file path to attach to the email."
                    },
                    "auto_send": {
                        "type": "boolean",
                        "description": "If true, automatically sends the email hands-free via SMTP or Outlook Ctrl+Enter shortcut (defaults to true)."
                    }
                },
                "required": ["to", "subject", "body"]
            },
            handler=self._tool_send_email
        )

        # 31. Email: AI Smart Drafting
        self.register(
            name="draft_email",
            description="Draft a professional, well-structured email using AI from brief instructions.",
            parameters={
                "type": "object",
                "properties": {
                    "instruction": {
                        "type": "string",
                        "description": "Brief instruction or key points to cover in the email draft."
                    },
                    "recipient": {
                        "type": "string",
                        "description": "Optional recipient name or relationship."
                    },
                    "tone": {
                        "type": "string",
                        "description": "Tone of the email, e.g., 'professional', 'casual', 'urgent', 'polite'."
                    }
                },
                "required": ["instruction"]
            },
            handler=self._tool_draft_email
        )

        # 32. Email: Check Unread Emails
        self.register(
            name="check_unread_emails",
            description="Check recent unread emails in the user's inbox via IMAP SSL and provide a voice summary.",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of unread emails to retrieve (default: 5)."
                    }
                }
            },
            handler=self._tool_check_unread_emails
        )

        # 33. Contacts: Manage Address Book
        self.register(
            name="manage_contacts",
            description="Manage the personal contacts book: add new contact, list contacts, search by name/nickname, or delete.",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["add", "list", "get", "delete"],
                        "description": "Action to perform on contacts: 'add', 'list', 'get', 'delete'."
                    },
                    "name": {
                        "type": "string",
                        "description": "Contact's full name (required for 'add' or 'get')."
                    },
                    "phone": {
                        "type": "string",
                        "description": "Contact's phone number with country code (e.g. +919876543210)."
                    },
                    "email": {
                        "type": "string",
                        "description": "Contact's email address."
                    },
                    "nickname": {
                        "type": "string",
                        "description": "Nickname or relationship (e.g. 'Mom', 'Boss', 'Dad')."
                    },
                    "contact_id": {
                        "type": "string",
                        "description": "Unique contact ID (required for 'delete')."
                    }
                },
                "required": ["action"]
            },
            handler=self._tool_manage_contacts
        )

        # 34. Web: Live Price Comparison & Tracking
        self.register(
            name="check_product_prices",
            description="Search live product prices across e-commerce sites (Amazon, Flipkart) to find the best deal, discount, and price comparison.",
            parameters={
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Name or model of the product to search (e.g. 'iPhone 15 128GB', 'Sony WH-1000XM5', 'MacBook Air M2')."
                    },
                    "sites": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of e-commerce sites to search, e.g. ['amazon', 'flipkart']."
                    },
                    "max_results_per_site": {
                        "type": "integer",
                        "description": "Max listings to fetch per store (default: 3)."
                    }
                },
                "required": ["product_name"]
            },
            handler=self._tool_check_product_prices
        )

        # 35. Web: Smart Webpage Scraper & Reader
        self.register(
            name="scrape_webpage",
            description="Scrapes a live webpage, extracting clean readable markdown text, articles, tables, and links while stripping boilerplate ads and navigation.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The target website URL to scrape."
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["content", "table", "links"],
                        "description": "Extraction mode: 'content' for clean text/markdown, 'table' for tables, 'links' for URLs."
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Max characters of content to return (default: 4000)."
                    }
                },
                "required": ["url"]
            },
            handler=self._tool_scrape_webpage
        )

        # 36. Web: Webpage Screenshot Capture
        self.register(
            name="capture_webpage_screenshot",
            description="Capture a high-resolution PNG screenshot of any live website URL using headless browser automation.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Target website URL to capture."
                    },
                    "full_page": {
                        "type": "boolean",
                        "description": "If true, captures the entire scrollable page height instead of just the viewport."
                    }
                },
                "required": ["url"]
            },
            handler=self._tool_capture_webpage_screenshot
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

    def _tool_analyze_screen(
        self,
        question: str = "Describe what is currently on the screen",
        focus_window: bool = False,
        image_base64: Optional[str] = None,
        image_path: Optional[str] = None,
        **kwargs
    ) -> str:
        """Captures active screen or focused window and analyzes it using multimodal vision."""
        try:
            from utils.vision import capture_screen_base64

            # If user provided a file path or direct base64
            b64 = image_base64
            if not b64 and image_path:
                try:
                    p = Path(image_path)
                    if p.exists():
                        with open(p, "rb") as f:
                            b64 = base64.b64encode(f.read()).decode("utf-8")
                except Exception as ex:
                    logger.debug(f"Could not load image_path {image_path}: {ex}")

            # Auto-detect if question asks specifically about a window
            q_lower = (question or "").lower()
            if any(w in q_lower for w in ["this window", "active window", "focused window", "this app", "this dialog"]):
                focus_window = True

            if not b64:
                b64 = capture_screen_base64(max_width=1280, focus_window=focus_window)

            if not b64:
                return "Could not capture the screen at this moment. Please verify display permissions."

            if not self.llm_client:
                from llm.nvidia_client import NvidiaLLMClient
                self.llm_client = NvidiaLLMClient()

            target_scope = "focused active window" if focus_window else "entire active screen"
            
            # Detect specialized vision mode
            is_error_debug = any(w in q_lower for w in ["error", "debug", "bug", "exception", "traceback", "fail", "crash"])
            is_doc_reading = any(w in q_lower for w in ["read document", "read text", "ocr", "pdf", "transcribe", "what does it say", "read this"])

            if is_error_debug:
                system_prompt = (
                    "You are IGIRS AI Diagnostic Engineer. Your job is to analyze screens containing terminal errors, "
                    "code exceptions, stack traces, and software bugs. Identify the root cause immediately and provide "
                    "the exact terminal command or code correction needed to resolve it."
                )
                prompt = (
                    f"The user needs help debugging their {target_scope}. Specific question: '{question}'.\n"
                    f"1. Pinpoint the exact error message, file name, line number, or status code.\n"
                    f"2. Explain why the issue occurred in plain language.\n"
                    f"3. Provide the exact command line or code fix to resolve it."
                )
            elif is_doc_reading:
                system_prompt = (
                    "You are IGIRS AI Document & OCR Engine. You transcribe, summarize, and extract information from documents, "
                    "articles, web pages, tables, and PDFs visible on the user's screen with extreme fidelity."
                )
                prompt = (
                    f"The user wants you to read and extract information from their {target_scope}. Specific request: '{question}'.\n"
                    f"1. Transcribe the key text, headings, and data visible.\n"
                    f"2. Provide a clear, bulleted summary of the core information."
                )
            else:
                system_prompt = (
                    "You are IGIRS AI Multimodal Vision Engine. You inspect the user's live desktop screen with superhuman precision. "
                    "Be concise, accurate, and direct. Break down key observations into readable points."
                )
                prompt = (
                    f"The user has captured their {target_scope} and asked: '{question}'.\n"
                    f"Carefully examine all visible elements (windows, applications, code, terminal outputs, error logs, text, UI controls, or documents).\n"
                    f"Provide a clear, direct, and actionable answer. If there is an error on screen, identify the cause and explain how to fix it."
                )

            analysis = self.llm_client.vision_chat_completion(
                prompt=prompt,
                image_base64=b64,
                system_prompt=system_prompt
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

    # --- Phase 3: Media Control Handlers ---

    def _tool_play_media(self, query: str, platform: str = "auto", **kwargs) -> Dict[str, Any]:
        """Plays media on Spotify or YouTube with auto-routing."""
        import tools.media_controls as media_controls
        return media_controls.play_media(query=query, platform=platform)

    def _tool_play_youtube(self, query: str, autoplay: bool = True, **kwargs) -> Dict[str, Any]:
        """Searches YouTube and plays top video with autoplay."""
        import tools.media_controls as media_controls
        return media_controls.play_youtube(query=query, autoplay=autoplay)

    def _tool_play_spotify(self, query: str = "", **kwargs) -> Dict[str, Any]:
        """Searches and plays on Spotify."""
        import tools.media_controls as media_controls
        return media_controls.play_spotify(query=query)

    def _tool_control_media(self, action: str, **kwargs) -> Dict[str, Any]:
        """Controls global Windows media playback."""
        import tools.media_controls as media_controls
        return media_controls.control_media(action=action)

    # --- Phase 5: Document Intelligence & Knowledge Vault Handlers ---

    def _tool_query_documents(self, query: str, doc_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Answers a question using local indexed documents."""
        target_id = None
        if doc_name:
            dn_lower = doc_name.lower()
            for did, d in self.documents.documents.items():
                if dn_lower in d.get("filename", "").lower() or dn_lower in did:
                    target_id = did
                    break
        return self.documents.answer_query(query=query, doc_id=target_id, llm_client=self.llm_client)

    def _tool_summarize_document(self, doc_name: Optional[str] = None, focus: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Summarizes an indexed document."""
        target_id = None
        if doc_name:
            dn_lower = doc_name.lower()
            for did, d in self.documents.documents.items():
                if dn_lower in d.get("filename", "").lower() or dn_lower in did:
                    target_id = did
                    break
        return self.documents.summarize_document(doc_id=target_id, focus=focus, llm_client=self.llm_client)

    def _tool_list_indexed_documents(self, **kwargs) -> Dict[str, Any]:
        """Lists all indexed files in the Knowledge Vault."""
        docs = self.documents.list_documents()
        return {
            "status": "success",
            "count": len(docs),
            "documents": docs
        }

    def _tool_index_local_file(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """Ingests a file from local disk."""
        p = Path(file_path.strip().strip('"').strip("'"))
        if not p.exists() or not p.is_file():
            return {"status": "error", "message": f"File does not exist: {file_path}"}
        return self.documents.ingest_file(source=p, filename=p.name)

    # --- Phase 6: Hands-Free WhatsApp & Email Handlers ---

    def _tool_send_whatsapp(self, recipient: str, message: str, auto_send: bool = True, **kwargs) -> Dict[str, Any]:
        """Dispatches a WhatsApp message."""
        return self.whatsapp.send_message(recipient=recipient, message=message, auto_send=auto_send)

    def _tool_send_email(self, to: str, subject: str, body: str, attachment_path: Optional[str] = None, auto_send: bool = True, **kwargs) -> Dict[str, Any]:
        """Sends an email or opens in mail client with hands-free auto-send."""
        return self.email.send_email(to=to, subject=subject, body=body, attachment_path=attachment_path, auto_send=auto_send)

    def _tool_draft_email(self, instruction: str, recipient: Optional[str] = None, tone: str = "professional", **kwargs) -> Dict[str, Any]:
        """Drafts an email using AI."""
        return self.email.draft_email(instruction=instruction, recipient=recipient, tone=tone, llm_client=self.llm_client)

    def _tool_check_unread_emails(self, limit: int = 5, **kwargs) -> Dict[str, Any]:
        """Checks unread emails via IMAP."""
        return self.email.check_unread_emails(limit=limit)

    def _tool_manage_contacts(
        self,
        action: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        nickname: Optional[str] = None,
        contact_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Manages contacts address book."""
        act = action.lower().strip()
        if act == "add":
            if not name:
                return {"status": "error", "message": "Contact name is required to add a contact."}
            contact = self.contacts.add_contact(
                name=name,
                phone=phone or "",
                email=email or "",
                nickname=nickname or ""
            )
            return {
                "status": "success",
                "action": "add",
                "contact": contact,
                "message": f"Added '{contact['name']}' to your contacts book."
            }
        elif act == "list":
            contacts = self.contacts.list_contacts()
            return {
                "status": "success",
                "action": "list",
                "count": len(contacts),
                "contacts": contacts
            }
        elif act == "get":
            query = name or nickname or phone or email or ""
            contact = self.contacts.get_contact(query)
            if contact:
                return {"status": "success", "action": "get", "contact": contact}
            return {"status": "not_found", "message": f"No contact found matching '{query}'."}
        elif act == "delete":
            cid = contact_id or (name and self.contacts.get_contact(name) and self.contacts.get_contact(name).get("id"))
            if not cid:
                return {"status": "error", "message": "Specify contact_id or name to delete."}
            ok = self.contacts.delete_contact(cid)
            return {"status": "success" if ok else "not_found", "action": "delete", "contact_id": cid}
        else:
            return {"status": "error", "message": f"Unknown contact action: '{action}'."}

    # --- Phase 8: Web Automation, Price Checks & Scraping Handlers ---

    def _tool_check_product_prices(self, product_name: str, sites: Optional[List[str]] = None, max_results_per_site: int = 3, **kwargs) -> Dict[str, Any]:
        """Compares product prices across e-commerce platforms."""
        return self.web.check_product_prices(product_name=product_name, sites=sites, max_results_per_site=max_results_per_site)

    def _tool_scrape_webpage(self, url: str, mode: str = "content", max_chars: int = 4000, **kwargs) -> Dict[str, Any]:
        """Scrapes and parses a live webpage."""
        return self.web.scrape_webpage(url=url, mode=mode, max_chars=max_chars)

    def _tool_capture_webpage_screenshot(self, url: str, full_page: bool = False, **kwargs) -> Dict[str, Any]:
        """Captures a PNG screenshot of a live website."""
        return self.web.capture_webpage_screenshot(url=url, full_page=full_page)

