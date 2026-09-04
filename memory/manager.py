"""
Memory Management Subsystem for IGIRS AI.
Handles short-term conversation history and long-term user facts.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import config

logger = logging.getLogger("IGIRS.Memory")

class MemoryManager:
    def __init__(
        self,
        facts_file: Path = config.FACTS_FILE,
        memory_file: Path = config.MEMORY_FILE,
        max_turns: int = 12
    ):
        self.facts_file = facts_file
        self.memory_file = memory_file
        self.max_turns = max_turns
        
        self.user_name = config.DEFAULT_USER_NAME
        self.language_preference = config.LANGUAGE_PREFERENCE
        self.facts: List[str] = []
        self.history: List[Dict[str, Any]] = []

        self._load_facts()
        self._load_history()

    def _load_facts(self):
        """Loads persistent user facts from JSON."""
        if self.facts_file.exists():
            try:
                with open(self.facts_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.user_name = data.get("name", config.DEFAULT_USER_NAME)
                    self.language_preference = data.get("language_preference", config.LANGUAGE_PREFERENCE)
                    raw_facts = data.get("facts", [])
                    # Clean facts list and remove duplicates
                    self.facts = list(dict.fromkeys([f.strip() for f in raw_facts if f and isinstance(f, str)]))
            except Exception as e:
                logger.error(f"Error loading facts from {self.facts_file}: {e}")
                self._initialize_default_facts()
        else:
            self._initialize_default_facts()

    def _initialize_default_facts(self):
        """Creates initial facts store."""
        self.facts = [
            f"User's name is {config.DEFAULT_USER_NAME}",
            "User is building the IGIRS AI desktop voice and text assistant",
            f"User prefers {config.LANGUAGE_PREFERENCE}"
        ]
        self.save_facts()

    def save_facts(self):
        """Persists user facts to JSON."""
        data = {
            "name": self.user_name,
            "language_preference": self.language_preference,
            "facts": self.facts
        }
        try:
            with open(self.facts_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save facts to {self.facts_file}: {e}")

    def add_fact(self, fact: str) -> bool:
        """Adds a new fact to long-term memory."""
        fact = fact.strip()
        if fact and fact not in self.facts:
            self.facts.append(fact)
            self.save_facts()
            return True
        return False

    def remove_fact(self, fact_or_index: Any) -> bool:
        """Removes a fact by exact string or index."""
        if isinstance(fact_or_index, int) and 0 <= fact_or_index < len(self.facts):
            self.facts.pop(fact_or_index)
            self.save_facts()
            return True
        elif isinstance(fact_or_index, str) and fact_or_index in self.facts:
            self.facts.remove(fact_or_index)
            self.save_facts()
            return True
        return False

    def get_facts(self) -> List[str]:
        return self.facts

    def _load_history(self):
        """Loads recent conversation history."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.history = data[- (self.max_turns * 2):]
            except Exception as e:
                logger.error(f"Error loading history: {e}")
                self.history = []

    def save_history(self):
        """Persists short-term history to disk."""
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def add_user_message(self, content: str):
        """Records a user message."""
        self.history.append({"role": "user", "content": content})
        self._trim_history()
        self.save_history()

    def add_assistant_message(self, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None):
        """Records an assistant response."""
        msg: Dict[str, Any] = {"role": "assistant", "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self.history.append(msg)
        self._trim_history()
        self.save_history()

    def add_tool_response(self, tool_call_id: str, tool_name: str, content: str):
        """Records a tool output in the conversation history."""
        self.history.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": content
        })
        self._trim_history()
        self.save_history()

    def _trim_history(self):
        """Keeps history within max_turns limit."""
        if len(self.history) > self.max_turns * 2:
            self.history = self.history[-(self.max_turns * 2):]

    def clear_history(self):
        """Clears short-term conversation history."""
        self.history = []
        self.save_history()

    def get_messages_for_llm(self, system_prompt: str) -> List[Dict[str, Any]]:
        """Constructs full message list for LLM context."""
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.history)
        return messages
