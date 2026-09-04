"""
IGIRS AI — Interactive Desktop Speech-to-Speech & Text Assistant Console.
Features live voice listening (Push-to-Talk and Hands-Free Continuous Voice Mode),
Voice output controls, and full tool integration.
"""
import sys
import os

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import time
from datetime import datetime
import config
from assistant import IGIRSAssistant

# ANSI Color Codes for Terminal UI
C_CYAN = "\033[96m"
C_BLUE = "\033[94m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_PURPLE = "\033[95m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_RESET = "\033[0m"

def print_banner(assistant: IGIRSAssistant):
    tts = assistant.tts
    voice_status = f"{C_GREEN}ON{C_RESET}" if tts.enabled else f"{C_RED}OFF{C_RESET}"
    vol_pct = int(tts.volume * 100)
    
    banner = f"""
{C_BLUE}{C_BOLD}╔════════════════════════════════════════════════════════════════════╗
║                      ⚡ IGIRS AI ASSISTANT ⚡                      ║
║            Intelligent Guardian & Interactive Realtime System      ║
╚════════════════════════════════════════════════════════════════════╝{C_RESET}
{C_DIM}• Core Brain:{C_RESET}     {C_CYAN}{config.PRIMARY_LLM_MODEL}{C_RESET}
{C_DIM}• Mode:{C_RESET}           {C_GREEN}Speech-to-Speech (STT + LLM + TTS Active){C_RESET}
{C_DIM}• Voice Output:{C_RESET}   {voice_status} {C_DIM}| Eng: {C_PURPLE}{tts.english_voice}{C_DIM} | Vol: {C_YELLOW}{vol_pct}%{C_DIM} | Rate: {C_CYAN}{tts.rate}{C_RESET}
{C_DIM}• Tamil Voice:{C_RESET}    {C_PURPLE}{tts.tamil_voice}{C_RESET}
{C_DIM}• Quick Start:{C_RESET}    Type {C_YELLOW}/listen{C_RESET}{C_DIM} for Push-to-Talk or {C_YELLOW}/voice_mode{C_RESET}{C_DIM} for Hands-Free mode.{C_RESET}
──────────────────────────────────────────────────────────────────────
"""
    print(banner)

def print_help():
    help_text = f"""
{C_YELLOW}{C_BOLD}Available Commands:{C_RESET}

  {C_PURPLE}{C_BOLD}[Voice & Speech-to-Speech]{C_RESET}
  {C_CYAN}/listen{C_RESET}                - Push-to-Talk: Listen to mic and reply with voice
  {C_CYAN}/voice_mode on | off{C_RESET}   - Start/Stop Hands-Free continuous voice conversation loop
  {C_CYAN}/voice on | off{C_RESET}        - Enable or mute spoken audio output
  {C_CYAN}/voice volume <0-100>{C_RESET}  - Set voice volume (e.g. /voice volume 80)
  {C_CYAN}/voice rate <rate>{C_RESET}     - Set speech speed (e.g. /voice rate +15% or 1.2x)
  {C_CYAN}/voice voice <name>{C_RESET}    - Change neural voice (e.g. /voice voice Christopher)
  {C_CYAN}/voice list{C_RESET}            - List all available English & Tamil neural voices
  {C_CYAN}/stop{C_RESET}                  - Instantly stop current voice playback

  {C_PURPLE}{C_BOLD}[System & Assistant Tools]{C_RESET}
  {C_CYAN}/screen [question]{C_RESET}     - Multimodal Screen Vision: inspect/explain your screen
  {C_CYAN}/play <media title>{C_RESET}    - Search & play music on YouTube or Spotify
  {C_CYAN}/briefing{C_RESET}              - Daily morning briefing (weather, time, battery, reminders)
  {C_CYAN}/telemetry{C_RESET}             - Inspect computer CPU, RAM, and Battery status
  {C_CYAN}/gui{C_RESET}                   - Launch the 3D Cyber Command Center Desktop Window
  {C_CYAN}/facts{C_RESET}                 - View all persistent facts stored in memory
  {C_CYAN}/addfact <text>{C_RESET}        - Manually add a new fact to memory
  {C_CYAN}/notes{C_RESET}                 - View saved notes and reminders
  {C_CYAN}/clear{C_RESET}                 - Reset active short-term conversation context
  {C_CYAN}/help{C_RESET}                  - Show this help menu
  {C_CYAN}/exit{C_RESET} or {C_CYAN}/quit{C_RESET}         - Exit the assistant
"""
    print(help_text)

def handle_voice_commands(arg: str, assistant: IGIRSAssistant):
    tts = assistant.tts
    parts = arg.strip().split(maxsplit=1)
    sub = parts[0].lower() if parts else ""
    val = parts[1] if len(parts) > 1 else ""

    if not sub or sub == "status":
        state = "ENABLED" if tts.enabled else "MUTED"
        print(f"\n{C_YELLOW}{C_BOLD}🔊 Voice Settings:{C_RESET}")
        print(f"  • State: {C_GREEN if tts.enabled else C_RED}{state}{C_RESET}")
        print(f"  • English Voice: {C_PURPLE}{tts.english_voice}{C_RESET}")
        print(f"  • Tamil Voice: {C_PURPLE}{tts.tamil_voice}{C_RESET}")
        print(f"  • Volume: {C_YELLOW}{int(tts.volume * 100)}%{C_RESET}")
        print(f"  • Speed Rate: {C_CYAN}{tts.rate}{C_RESET}\n")

    elif sub in ("on", "enable"):
        tts.set_enabled(True)
        print(f"{C_GREEN}✔ Voice output enabled.{C_RESET}")

    elif sub in ("off", "disable", "mute"):
        tts.set_enabled(False)
        print(f"{C_RED}✔ Voice output muted.{C_RESET}")

    elif sub == "toggle":
        new_state = tts.toggle()
        msg = f"{C_GREEN}enabled{C_RESET}" if new_state else f"{C_RED}muted{C_RESET}"
        print(f"✔ Voice output is now {msg}.")

    elif sub in ("vol", "volume"):
        if not val:
            print(f"{C_YELLOW}Current Volume: {int(tts.volume * 100)}%{C_RESET} (Usage: /voice volume 80)")
        else:
            new_vol = tts.set_volume(val)
            print(f"{C_GREEN}✔ Voice volume set to {int(new_vol * 100)}%{C_RESET}")

    elif sub in ("rate", "speed"):
        if not val:
            print(f"{C_YELLOW}Current Speed Rate: {tts.rate}{C_RESET} (Usage: /voice rate +15% or 1.2x)")
        else:
            new_rate = tts.set_rate(val)
            print(f"{C_GREEN}✔ Speech rate set to {new_rate}{C_RESET}")

    elif sub in ("voice", "setvoice"):
        if not val:
            print(f"{C_RED}Usage: /voice voice <name or ID>{C_RESET} (Use /voice list to see options)")
        else:
            tts.set_voice(val)
            print(f"{C_GREEN}✔ Voice updated. English: {tts.english_voice} | Tamil: {tts.tamil_voice}{C_RESET}")

    elif sub == "list":
        print(f"\n{C_PURPLE}{C_BOLD}🎙️ Available Neural Voices:{C_RESET}")
        for v in tts.list_voices():
            is_active = (v['id'] == tts.english_voice or v['id'] == tts.tamil_voice)
            tag = f" {C_GREEN}[ACTIVE]{C_RESET}" if is_active else ""
            print(f"  • {C_CYAN}{v['id']}{C_RESET} - {v['name']}{tag}")
        print()
    else:
        print(f"{C_RED}Unknown voice command '{sub}'. Use /voice on|off|volume|rate|voice|list{C_RESET}")

def run_single_voice_turn(assistant: IGIRSAssistant):
    """Executes a single push-to-talk voice turn."""
    print(f"\n{C_GREEN}🎙️  [LISTENING... Speak into your microphone now]{C_RESET}")
    
    def on_transcribing():
        print(f"{C_YELLOW}📝  [TRANSCRIBING AUDIO...]{C_RESET}")

    user_text, reply = assistant.listen_and_respond(
        on_transcribing=on_transcribing,
        on_tool_call=tool_call_callback,
        on_tool_result=tool_result_callback,
        speak_response=True
    )

    if not user_text:
        print(f"{C_DIM}(No speech detected or timed out. Try /listen again){C_RESET}\n")
        return

    print(f"\n{C_BOLD}{assistant.memory.user_name} (Voice) > {C_RESET}{user_text}")
    voice_tag = f" {C_PURPLE}🔊 Speaking...{C_RESET}" if assistant.tts.enabled else ""
    print(f"{C_CYAN}{C_BOLD}IGIRS AI:{C_RESET}{voice_tag} {reply}\n")

def run_continuous_voice_mode(assistant: IGIRSAssistant):
    """Runs a continuous hands-free voice loop."""
    print(f"\n{C_PURPLE}{C_BOLD}╔══════════════════════════════════════════════════════════════════╗")
    print(f"║             🎙️  HANDS-FREE CONTINUOUS VOICE MODE ACTIVE           ║")
    print(f"║     Speak anytime. Say your question or request naturally.       ║")
    print(f"║              Press Ctrl+C anytime to exit Voice Mode             ║")
    print(f"╚══════════════════════════════════════════════════════════════════╝{C_RESET}\n")

    assistant.stt.calibrate_microphone()

    while True:
        try:
            print(f"{C_GREEN}🟢 [LISTENING...]{C_RESET}", end="\r", flush=True)

            def on_transcribing():
                print(f"{C_YELLOW}📝 [Processing Speech...]{C_RESET}", end="\r", flush=True)

            user_text, reply = assistant.listen_and_respond(
                timeout=5,
                phrase_time_limit=15,
                on_transcribing=on_transcribing,
                on_tool_call=tool_call_callback,
                on_tool_result=tool_result_callback,
                speak_response=True
            )

            if not user_text:
                continue

            # Clear status line
            print(" " * 35, end="\r")
            print(f"\n{C_BOLD}{assistant.memory.user_name} 🎙️ > {C_RESET}{user_text}")
            voice_tag = f" {C_PURPLE}🔊 Speaking...{C_RESET}" if assistant.tts.enabled else ""
            print(f"{C_CYAN}{C_BOLD}IGIRS AI:{C_RESET}{voice_tag} {reply}\n")

            # Wait for speech playback while barge-in monitor is armed
            time.sleep(0.12)
            while assistant.tts.is_speaking():
                time.sleep(0.05)

            # Ultra-short echo prevention pause
            time.sleep(0.2)

        except KeyboardInterrupt:
            assistant.tts.stop()
            print(f"\n{C_YELLOW}✔ Exited Hands-Free Voice Mode. Returned to console.{C_RESET}\n")
            break
        except Exception as e:
            print(f"\n{C_RED}[Voice Error]{C_RESET} {e}")
            time.sleep(1)

def handle_slash_command(command: str, assistant: IGIRSAssistant) -> bool:
    """Handles slash commands. Returns True if handled, False if regular message."""
    cmd_parts = command.strip().split(maxsplit=1)
    action = cmd_parts[0].lower()
    arg = cmd_parts[1] if len(cmd_parts) > 1 else ""

    if action in ("/exit", "/quit", "exit", "quit"):
        assistant.tts.stop()
        print(f"\n{C_BLUE}IGIRS AI: Goodbye, {assistant.memory.user_name}! Shutting down.{C_RESET}\n")
        sys.exit(0)

    elif action == "/help":
        print_help()
        return True

    elif action in ("/listen", "/mic", "/ptt"):
        run_single_voice_turn(assistant)
        return True

    elif action in ("/voice_mode", "/voicemode", "/handsfree"):
        if arg.lower() in ("off", "disable", "stop"):
            print(f"{C_YELLOW}Voice mode is currently idle.{C_RESET}")
        else:
            run_continuous_voice_mode(assistant)
        return True

    elif action in ("/stop", "stop"):
        assistant.tts.stop()
        print(f"{C_YELLOW}⏹ Speech stopped.{C_RESET}")
        return True

    elif action == "/voice":
        handle_voice_commands(arg, assistant)
        return True

    elif action in ("/gui", "/app", "/overlay"):
        print(f"{C_GREEN}🚀 Launching 3D Cyber Command Center GUI...{C_RESET}")
        from gui import run_gui
        run_gui(assistant=assistant)
        return True

    elif action == "/facts":
        facts = assistant.memory.get_facts()
        print(f"\n{C_PURPLE}{C_BOLD}🧠 Persistent Memory Facts ({len(facts)}):{C_RESET}")
        for i, fact in enumerate(facts, 1):
            print(f"  {C_DIM}{i}.{C_RESET} {fact}")
        print()
        return True

    elif action == "/addfact":
        if not arg:
            print(f"{C_RED}Usage: /addfact <fact to store>{C_RESET}")
        else:
            assistant.memory.add_fact(arg)
            print(f"{C_GREEN}✔ Stored fact:{C_RESET} {arg}")
        return True

    elif action == "/telemetry":
        telemetry = assistant.tools._tool_system_telemetry()
        print(f"\n{C_YELLOW}{C_BOLD}⚡ System Diagnostics:{C_RESET}")
        for k, v in telemetry.items():
            print(f"  • {C_CYAN}{k}:{C_RESET} {v}")
        print()
        return True

    elif action in ("/screen", "/vision"):
        q = arg if arg else "Describe what is currently on my screen in detail."
        print(f"\n{C_YELLOW}👁️ Capturing screen & analyzing with Llama-3.2-11B Vision...{C_RESET}")
        analysis = assistant.tools._tool_analyze_screen(question=q)
        print(f"\n{C_CYAN}{C_BOLD}IGIRS Vision:{C_RESET} {analysis}\n")
        if assistant.tts.enabled:
            assistant.tts.speak(analysis)
        return True

    elif action in ("/play", "/music"):
        if not arg:
            print(f"{C_RED}Usage: /play <song or video name>{C_RESET}")
        else:
            res = assistant.tools._tool_play_media(query=arg)
            print(f"{C_GREEN}🎵 {res}{C_RESET}")
            if assistant.tts.enabled:
                assistant.tts.speak(res)
        return True

    elif action in ("/briefing", "/morning"):
        print(f"\n{C_YELLOW}🌅 Compiling Daily Briefing...{C_RESET}")
        briefing = assistant.tools._tool_daily_briefing()
        text_out = (
            f"{briefing['greeting']}\n"
            f"Today is {briefing['date']} at {briefing['time']}.\n"
            f"Weather: {briefing['weather']}.\n"
            f"Battery: {briefing['battery']} | CPU Load: {briefing['cpu_load']}.\n"
            f"Pending Reminders: {', '.join(briefing['notes'])}."
        )
        print(f"\n{C_CYAN}{C_BOLD}IGIRS Daily Briefing:{C_RESET}\n{text_out}\n")
        if assistant.tts.enabled:
            assistant.tts.speak(text_out)
        return True

    elif action == "/notes":
        result = assistant.tools._tool_manage_notes(action="list")
        notes = result.get("notes", [])
        print(f"\n{C_YELLOW}{C_BOLD}📝 Saved Notes ({len(notes)}):{C_RESET}")
        if not notes:
            print("  (No notes saved yet)")
        for n in notes:
            print(f"  • [{n.get('created_at', '')}] #{n.get('id')}: {n.get('note')}")
        print()
        return True

    elif action == "/clear":
        assistant.memory.clear_history()
        print(f"{C_GREEN}✔ Conversation history cleared.{C_RESET}")
        return True

    return False

def tool_call_callback(name: str, args: dict):
    print(f"\n{C_YELLOW}⚙️  Invoking Tool:{C_RESET} {C_BOLD}{name}{C_RESET}({args})")

def tool_result_callback(name: str, result: str):
    preview = result[:120] + "..." if len(result) > 120 else result
    print(f"{C_GREEN}✔  Tool Output:{C_RESET} {C_DIM}{preview}{C_RESET}")

def main():
    if "--gui" in sys.argv or "-g" in sys.argv:
        from gui import run_gui
        run_gui()
        return

    assistant = IGIRSAssistant()
    print_banner(assistant)

    print(f"{C_GREEN}✔ Online & Connected to NVIDIA NIM API.{C_RESET}")
    print(f"{C_DIM}Welcome back, {assistant.memory.user_name}. Ready for voice or text commands.{C_RESET}\n")

    while True:
        try:
            user_input = input(f"{C_BOLD}{assistant.memory.user_name} > {C_RESET}").strip()
            if not user_input:
                continue

            if user_input.startswith("/"):
                if handle_slash_command(user_input, assistant):
                    continue

            print(f"{C_DIM}Thinking...{C_RESET}", end="\r", flush=True)
            
            response = assistant.process_message(
                user_input=user_input,
                on_tool_call=tool_call_callback,
                on_tool_result=tool_result_callback,
                speak_response=True
            )

            # Clear "Thinking..."
            print(" " * 20, end="\r")
            voice_tag = f" {C_PURPLE}🔊 Speaking...{C_RESET}" if assistant.tts.enabled else ""
            print(f"\n{C_CYAN}{C_BOLD}IGIRS AI:{C_RESET}{voice_tag} {response}\n")

        except KeyboardInterrupt:
            assistant.tts.stop()
            print(f"\n\n{C_BLUE}IGIRS AI: Session paused. Type /exit to quit.{C_RESET}\n")
        except Exception as e:
            print(f"\n{C_RED}[Error]{C_RESET} {e}\n")

if __name__ == "__main__":
    main()
