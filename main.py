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
  {C_CYAN}/screen window [q]{C_RESET}     - Multimodal Vision: inspect only the active foreground window
  {C_CYAN}/doc load <path>{C_RESET}        - Ingest local PDF, resume, notes, or code into Knowledge Vault
  {C_CYAN}/doc ask <question>{C_RESET}     - Search & answer questions from indexed documents
  {C_CYAN}/doc summary [file]{C_RESET}     - Generate structured executive summary of a document
  {C_CYAN}/doc list{C_RESET}               - List all documents indexed in the Knowledge Vault
  {C_CYAN}/doc clear{C_RESET}              - Clear all documents from Knowledge Vault
  {C_CYAN}/wa <recipient> <msg>{C_RESET}   - Hands-free WhatsApp message dispatch (e.g. /wa Mom Heading home!)
  {C_CYAN}/mail send <to> <sub|msg>{C_RESET}- Send email via SMTP or native mail client
  {C_CYAN}/mail draft <prompt>{C_RESET}    - Draft a polished email using AI
  {C_CYAN}/mail check{C_RESET}             - Check unread emails via IMAP
  {C_CYAN}/contact <list|add|del>{C_RESET}  - Manage personal contacts and phone numbers
  {C_CYAN}/play <media title>{C_RESET}    - Search & play music on YouTube or Spotify
  {C_PURPLE}{C_BOLD}[Web Automation & Price Intelligence]{C_RESET}
  {C_CYAN}/price <product name>{C_RESET}     - Compare prices on Amazon & Flipkart with best deal finder
  {C_CYAN}/scrape <url> [mode]{C_RESET}      - Clean article/content scraper (modes: content, tables, links)
  {C_CYAN}/webscreen <url>{C_RESET}          - Capture headless webpage screenshot
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
        print(f"  • Speed Rate: {C_CYAN}{tts.rate}{C_RESET}")
        print(f"  • Barge-In Profile: {C_CYAN}{tts.get_barge_in_mode().upper()}{C_RESET}\n")

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

    elif sub in ("barge", "bargein", "barge_in"):
        if not val:
            print(f"{C_YELLOW}Current Barge-In Profile: {tts.get_barge_in_mode().upper()}{C_RESET}")
            print(f"{C_DIM}Usage: /voice bargein off | headphones | speakers{C_RESET}")
        else:
            tts.set_barge_in_mode(val)
            print(f"{C_GREEN}✔ Barge-In profile set to '{tts.get_barge_in_mode().upper()}'.{C_RESET}")

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
        print(f"{C_RED}Unknown voice command '{sub}'. Use /voice on|off|volume|rate|bargein|voice|list{C_RESET}")

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

    # Hook Voice Barge-In callback to immediately notify console
    def on_barge_in_triggered():
        print(f"\n{C_CYAN}⚡ [VOICE BARGE-IN DETECTED]{C_RESET} {C_YELLOW}Halted speech! Listening to you now...{C_RESET}")

    assistant.tts.set_on_barge_in(on_barge_in_triggered)

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

            # Wait for speech playback cleanly
            time.sleep(0.15)
            while assistant.tts.is_speaking():
                time.sleep(0.04)

            # If interrupted by voice barge-in, skip echo pause and listen immediately!
            if not assistant.tts.was_interrupted():
                time.sleep(0.35)

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
        focus_win = False
        q = arg.strip()
        if q.lower().startswith("window"):
            focus_win = True
            q = q[6:].strip() or "Describe what is currently visible in this active window."
        elif not q:
            q = "Describe what is currently on my screen in detail."

        target_name = "active window" if focus_win else "full screen"
        print(f"\n{C_YELLOW}👁️ Capturing {target_name} & analyzing with Llama-3.2-11B Vision...{C_RESET}")
        analysis = assistant.tools._tool_analyze_screen(question=q, focus_window=focus_win)
        print(f"\n{C_CYAN}{C_BOLD}IGIRS Vision:{C_RESET} {analysis}\n")
        if assistant.tts.enabled:
            paragraphs = [p for p in analysis.split("\n\n") if p.strip()]
            spoken = paragraphs[0].replace("*", "").replace("#", "").strip() if paragraphs else analysis
            if len(spoken) > 280:
                spoken = spoken[:280] + "..."
            assistant.tts.speak(spoken)
        return True

    elif action in ("/doc", "/docs"):
        parts = arg.strip().split(maxsplit=1)
        sub = parts[0].lower() if parts else ""
        sub_arg = parts[1] if len(parts) > 1 else ""

        if not sub or sub == "list":
            docs = assistant.tools.documents.list_documents()
            print(f"\n{C_PURPLE}{C_BOLD}📚 Knowledge Vault Documents ({len(docs)}):{C_RESET}")
            if not docs:
                print("  (No documents indexed yet. Use /doc load <file_path>)")
            for d in docs:
                cat = d.get('category', 'doc').upper()
                print(f"  • {C_CYAN}[{cat}]{C_RESET} {C_BOLD}{d.get('filename')}{C_RESET} — {d.get('total_pages')} pages, {d.get('total_words')} words (ID: {d.get('id')})")
            print()
            return True

        elif sub in ("load", "add", "ingest"):
            if not sub_arg:
                print(f"{C_RED}Usage: /doc load <path/to/file.pdf or .py or .docx>{C_RESET}")
            else:
                p = Path(sub_arg.strip('"').strip("'"))
                if not p.exists():
                    print(f"{C_RED}File not found: {p}{C_RESET}")
                else:
                    print(f"{C_YELLOW}📄 Ingesting and indexing '{p.name}'...{C_RESET}")
                    res = assistant.tools.documents.ingest_file(source=p, filename=p.name)
                    if res.get("status") == "success":
                        print(f"{C_GREEN}✔ Successfully indexed {p.name}! ({res.get('total_pages')} pages, {res.get('total_chunks')} chunks){C_RESET}")
                    else:
                        print(f"{C_RED}Failed: {res.get('message')}{C_RESET}")
            return True

        elif sub in ("ask", "query"):
            if not sub_arg:
                print(f"{C_RED}Usage: /doc ask <your question about the documents>{C_RESET}")
            else:
                print(f"{C_YELLOW}🔍 Searching Knowledge Vault with local RAG...{C_RESET}")
                res = assistant.tools.documents.answer_query(query=sub_arg, llm_client=assistant.llm)
                print(f"\n{C_CYAN}{C_BOLD}IGIRS Document Intelligence:{C_RESET}\n{res.get('answer')}\n")
                if res.get("citations"):
                    sources = ", ".join(f"{c['filename']} [{c['page']}]" for c in res["citations"])
                    print(f"{C_DIM}Sources: {sources}{C_RESET}\n")
                if assistant.tts.enabled:
                    paragraphs = [p for p in res.get('answer', '').split("\n\n") if p.strip()]
                    spoken = paragraphs[0].replace("*", "").replace("#", "").strip() if paragraphs else res.get('answer', '')
                    if len(spoken) > 280:
                        spoken = spoken[:280] + "..."
                    assistant.tts.speak(spoken)
            return True

        elif sub in ("summary", "summarize"):
            print(f"{C_YELLOW}📑 Generating document summary...{C_RESET}")
            res = assistant.tools.documents.summarize_document(focus=sub_arg if sub_arg else None, llm_client=assistant.llm)
            print(f"\n{C_CYAN}{C_BOLD}Document Summary:{C_RESET}\n{res.get('summary')}\n")
            if assistant.tts.enabled:
                paragraphs = [p for p in res.get('summary', '').split("\n\n") if p.strip()]
                spoken = paragraphs[0].replace("*", "").replace("#", "").strip() if paragraphs else res.get('summary', '')
                if len(spoken) > 280:
                    spoken = spoken[:280] + "..."
                assistant.tts.speak(spoken)
            return True

        elif sub == "clear":
            assistant.tools.documents.clear_all()
            print(f"{C_GREEN}✔ Knowledge Vault cleared.{C_RESET}")
            return True

        else:
            query_text = arg
            print(f"{C_YELLOW}🔍 Searching Knowledge Vault with local RAG...{C_RESET}")
            res = assistant.tools.documents.answer_query(query=query_text, llm_client=assistant.llm)
            print(f"\n{C_CYAN}{C_BOLD}IGIRS Document Intelligence:{C_RESET}\n{res.get('answer')}\n")
            if res.get("citations"):
                sources = ", ".join(f"{c['filename']} [{c['page']}]" for c in res["citations"])
                print(f"{C_DIM}Sources: {sources}{C_RESET}\n")
            if assistant.tts.enabled:
                paragraphs = [p for p in res.get('answer', '').split("\n\n") if p.strip()]
                spoken = paragraphs[0].replace("*", "").replace("#", "").strip() if paragraphs else res.get('answer', '')
                if len(spoken) > 280:
                    spoken = spoken[:280] + "..."
                assistant.tts.speak(spoken)
            return True

    elif action in ("/wa", "/whatsapp"):
        parts = arg.strip().split(maxsplit=1)
        if len(parts) < 2:
            print(f"{C_RED}Usage: /wa <recipient_or_phone> <message>{C_RESET} (e.g. /wa Mom Heading home now!)")
        else:
            rec, msg = parts[0], parts[1]
            print(f"{C_YELLOW}📱 Dispatching WhatsApp message to '{rec}'...{C_RESET}")
            res = assistant.tools.whatsapp.send_message(recipient=rec, message=msg, auto_send=True)
            if res.get("status") == "success":
                print(f"{C_GREEN}✔ {res.get('summary')}{C_RESET}")
                if assistant.tts.enabled:
                    assistant.tts.speak(f"Dispatched WhatsApp to {res.get('recipient_name', rec)}.")
            else:
                print(f"{C_RED}Failed: {res.get('message')}{C_RESET}")
        return True

    elif action in ("/mail", "/email"):
        parts = arg.strip().split(maxsplit=2)
        sub = parts[0].lower() if parts else ""

        if sub == "check":
            print(f"{C_YELLOW}📥 Checking unread emails via IMAP...{C_RESET}")
            res = assistant.tools.email.check_unread_emails()
            if res.get("status") == "success":
                print(f"\n{C_CYAN}{C_BOLD}Inbox Status ({res.get('unread_count')} unread):{C_RESET}")
                for em in res.get("emails", []):
                    print(f"  • {C_BOLD}{em.get('sender')}{C_RESET}: {em.get('subject')}")
                print()
                if assistant.tts.enabled and res.get("summary"):
                    assistant.tts.speak(res["summary"])
            else:
                print(f"{C_YELLOW}{res.get('message', 'Could not check inbox.')}{C_RESET}")
            return True

        elif sub == "draft":
            inst = parts[1] if len(parts) > 1 else ""
            if not inst:
                print(f"{C_RED}Usage: /mail draft <brief instructions for email>{C_RESET}")
            else:
                print(f"{C_YELLOW}✍️ AI Drafting email...{C_RESET}")
                res = assistant.tools.email.draft_email(instruction=inst, llm_client=assistant.llm)
                print(f"\n{C_CYAN}{C_BOLD}Subject:{C_RESET} {res.get('subject')}")
                print(f"\n{C_CYAN}{C_BOLD}Body:{C_RESET}\n{res.get('body')}\n")
            return True

        elif sub == "send":
            if len(parts) < 3:
                print(f"{C_RED}Usage: /mail send <to_email_or_contact> <subject | body>{C_RESET}")
            else:
                to_addr = parts[1]
                content = parts[2]
                if "|" in content:
                    subj, body = content.split("|", 1)
                else:
                    subj = "Message from Joshua"
                    body = content
                print(f"{C_YELLOW}✉️ Sending email to '{to_addr}'...{C_RESET}")
                res = assistant.tools.email.send_email(to=to_addr, subject=subj.strip(), body=body.strip())
                if res.get("status") == "success":
                    print(f"{C_GREEN}✔ {res.get('summary')}{C_RESET}")
                    if assistant.tts.enabled:
                        assistant.tts.speak(f"Email processed for {to_addr}.")
                else:
                    print(f"{C_RED}Failed: {res.get('message')}{C_RESET}")
            return True

        else:
            print(f"{C_RED}Usage: /mail <send|draft|check>{C_RESET}")
            return True

    elif action in ("/contact", "/contacts"):
        parts = arg.strip().split(maxsplit=4)
        sub = parts[0].lower() if parts else ""

        if not sub or sub == "list":
            contacts = assistant.tools.contacts.list_contacts()
            print(f"\n{C_PURPLE}{C_BOLD}📇 Personal Contacts ({len(contacts)}):{C_RESET}")
            for c in contacts:
                nick = f" ({c['nickname']})" if c.get("nickname") else ""
                print(f"  • {C_BOLD}{c.get('name')}{nick}{C_RESET} — Phone: {C_GREEN}{c.get('phone') or 'None'}{C_RESET} | Email: {C_CYAN}{c.get('email') or 'None'}{C_RESET} (ID: {c.get('id')})")
            print()
            return True

        elif sub == "add":
            if len(parts) < 3:
                print(f"{C_RED}Usage: /contact add <Name> <Phone> [Email] [Nickname]{C_RESET}")
            else:
                c_name = parts[1]
                c_phone = parts[2]
                c_email = parts[3] if len(parts) > 3 else ""
                c_nick = parts[4] if len(parts) > 4 else ""
                contact = assistant.tools.contacts.add_contact(name=c_name, phone=c_phone, email=c_email, nickname=c_nick)
                print(f"{C_GREEN}✔ Added contact '{contact['name']}' ({contact['phone']}) to address book.{C_RESET}")
            return True

        elif sub in ("del", "delete", "remove"):
            if len(parts) < 2:
                print(f"{C_RED}Usage: /contact del <name_or_id>{C_RESET}")
            else:
                target = parts[1]
                contact = assistant.tools.contacts.get_contact(target)
                if contact:
                    assistant.tools.contacts.delete_contact(contact["id"])
                    print(f"{C_GREEN}✔ Deleted contact '{contact['name']}'.{C_RESET}")
                else:
                    print(f"{C_RED}Contact not found: {target}{C_RESET}")
            return True

        else:
            print(f"{C_RED}Usage: /contact <list|add|del>{C_RESET}")
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

    elif action in ("/price", "/prices", "/deal"):
        if not arg:
            print(f"{C_RED}Usage: /price <product name>{C_RESET} (e.g. /price iPhone 15 128GB)")
        else:
            print(f"\n{C_YELLOW}🛒 Scanning live prices across Amazon & Flipkart for '{arg}'...{C_RESET}")
            res = assistant.tools.web.check_product_prices(product_name=arg)
            print(f"\n{C_CYAN}{C_BOLD}IGIRS Price Intelligence:{C_RESET} {res.get('summary')}\n")
            for p in res.get("products", []):
                store_badge = f"{C_GREEN}[{p.get('store')}]{C_RESET}"
                rating_badge = f" ({p.get('rating')})" if p.get("rating") else ""
                print(f"  • {store_badge} {C_BOLD}{p.get('title')}{C_RESET}: {C_YELLOW}{p.get('price')}{C_RESET}{rating_badge}")
                if p.get("url"):
                    print(f"    {C_DIM}{p.get('url')}{C_RESET}")
            print()
            if assistant.tts.enabled and res.get("summary"):
                assistant.tts.speak(res["summary"])
        return True

    elif action in ("/scrape", "/extract"):
        parts = arg.strip().split(maxsplit=1)
        if not parts:
            print(f"{C_RED}Usage: /scrape <url> [mode: content|tables|links]{C_RESET}")
        else:
            target_url = parts[0]
            mode = parts[1] if len(parts) > 1 else "content"
            print(f"\n{C_YELLOW}🌐 Scraping '{target_url}' (mode: {mode})...{C_RESET}")
            res = assistant.tools.web.scrape_webpage(url=target_url, mode=mode)
            if res.get("status") == "success":
                print(f"\n{C_CYAN}{C_BOLD}Title:{C_RESET} {res.get('title')}")
                print(f"{C_DIM}Word count: {res.get('word_count')}{C_RESET}\n")
                if mode == "tables" and res.get("tables"):
                    print(f"{C_PURPLE}{C_BOLD}Extracted Tables:{C_RESET}")
                    for t_idx, tbl in enumerate(res["tables"], 1):
                        print(f"  Table #{t_idx}:")
                        for r in tbl[:5]:
                            print(f"    {' | '.join(r)}")
                elif mode == "links" and res.get("links"):
                    print(f"{C_PURPLE}{C_BOLD}Extracted Links:{C_RESET}")
                    for lnk in res["links"][:10]:
                        print(f"  • {lnk.get('text')}: {C_DIM}{lnk.get('url')}{C_RESET}")
                else:
                    preview = res.get("content", "")
                    if len(preview) > 1000:
                        preview = preview[:1000] + "\n...(use GUI reader mode to view full text)..."
                    print(f"{preview}\n")
                if assistant.tts.enabled and res.get("summary"):
                    assistant.tts.speak(res["summary"])
            else:
                print(f"{C_RED}Scrape Failed: {res.get('message')}{C_RESET}")
        return True

    elif action in ("/webscreen", "/webcap"):
        if not arg:
            print(f"{C_RED}Usage: /webscreen <url>{C_RESET}")
        else:
            print(f"\n{C_YELLOW}📸 Capturing web screenshot of '{arg}'...{C_RESET}")
            res = assistant.tools.web.capture_webpage_screenshot(url=arg)
            if res.get("status") == "success":
                print(f"{C_GREEN}✔ Saved web screenshot to {res.get('screenshot_path')}{C_RESET}")
                if assistant.tts.enabled:
                    assistant.tts.speak(f"Captured screenshot of {res.get('title', arg)}.")
            else:
                print(f"{C_RED}Capture Failed: {res.get('message')}{C_RESET}")
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

    def global_barge_in():
        print(f"\n{C_CYAN}⚡ [VOICE BARGE-IN DETECTED]{C_RESET} {C_YELLOW}Speech halted! Listening to you now...{C_RESET}")

    assistant.tts.set_on_barge_in(global_barge_in)

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
