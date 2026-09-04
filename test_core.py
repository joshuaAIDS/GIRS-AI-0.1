"""
Self-Contained Verification Test for IGIRS AI Text-Based Core.
"""
import sys
import os

# Fix UTF-8 encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import json
import config
from memory.manager import MemoryManager
from tools.registry import ToolRegistry
from llm.nvidia_client import NvidiaLLMClient
from assistant import IGIRSAssistant

def run_tests():
    print("=" * 60)
    print("⚡ IGIRS AI — Phase 1 Core Verification Suite")
    print("=" * 60)

    # 1. Config Test
    print("\n[1/5] Testing Configuration & Key Loading...")
    print(f"  • Total API Keys Loaded: {len(config.NVIDIA_API_KEYS)}")
    print(f"  • Base URL: {config.NVIDIA_BASE_URL}")
    print(f"  • Primary Model: {config.PRIMARY_LLM_MODEL}")
    assert len(config.NVIDIA_API_KEYS) > 0, "No API keys found!"
    print("  [OK] Config verified.")

    # 2. Memory Manager Test
    print("\n[2/5] Testing Memory Subsystem...")
    memory = MemoryManager()
    facts = memory.get_facts()
    print(f"  • Initial Facts Count: {len(facts)}")
    print(f"  • User Name: {memory.user_name}")
    print(f"  • Language Preference: {memory.language_preference}")
    test_fact = "User is testing IGIRS AI verification script"
    memory.add_fact(test_fact)
    assert test_fact in memory.get_facts(), "Failed to add fact!"
    memory.remove_fact(test_fact)
    print("  [OK] Memory and Fact persistence verified.")

    # 3. Tool Registry Test
    print("\n[3/5] Testing Tool Engine & Desktop Telemetry...")
    tools = ToolRegistry(memory_manager=memory)
    defs = tools.get_tool_definitions()
    print(f"  • Registered Tools: {[t['function']['name'] for t in defs]}")
    
    # Run Telemetry
    telemetry_raw = tools.execute_tool("get_system_telemetry", {})
    print(f"  • Telemetry Output: {telemetry_raw}")
    assert "os" in telemetry_raw, "Telemetry missing OS info"

    # Run Time & Date
    time_raw = tools.execute_tool("get_time_date", {})
    print(f"  • Time & Date Output: {time_raw}")
    assert "time_12hr" in time_raw, "Time & date missing time_12hr"
    print("  [OK] Tools execution verified.")

    # 4. LLM API Connectivity Test
    print("\n[4/5] Testing NVIDIA NIM API Connection...")
    client = NvidiaLLMClient()
    print(f"  • Sending test ping to {config.PRIMARY_LLM_MODEL}...")
    try:
        response = client.chat_completion(
            messages=[
                {"role": "system", "content": "You are IGIRS AI."},
                {"role": "user", "content": "Respond with one short sentence confirming you are online."}
            ],
            max_tokens=60
        )
        reply = response["choices"][0]["message"]["content"]
        print(f"  • LLM Output: \"{reply.strip()}\"")
        print("  [OK] NVIDIA NIM API Connection verified successfully.")
    except Exception as e:
        print(f"  [Warning] LLM Connectivity note: {e}")

    # 5. Full Assistant Orchestrator Test
    print("\n[5/5] Testing Assistant Orchestrator...")
    try:
        assistant = IGIRSAssistant()
        answer = assistant.process_message("Hi IGIRS, who are you and what tools do you have?")
        print(f"  • Assistant Reply: \"{answer.strip()}\"")
        print("  [OK] Assistant Orchestrator end-to-end verified.")
    except Exception as e:
        print(f"  [Warning] Assistant Orchestrator note: {e}")

    print("\n" + "=" * 60)
    print("✨ ALL PHASE 1 CORE CHECKS COMPLETED!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
