"""
JavaScript-Python Bridge API for IGIRS AI Desktop GUI.
Exposes assistant methods, live telemetry, Fact Vault, and voice controls to pywebview.
Uses private attributes to prevent pywebview from recursively introspecting native window objects.
"""
import logging
import base64
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
        if self._window:
            try:
                self._window.evaluate_js("if (window.onBargeInTriggered) window.onBargeInTriggered()")
            except Exception as e:
                logger.debug(f"Error notifying barge-in to JS: {e}")

    def trigger_barge_in(self) -> bool:
        """Manually triggers barge-in interrupt from GUI (Spacebar, Orb click)."""
        if self._assistant and hasattr(self._assistant, "tts") and self._assistant.tts.is_speaking():
            self._assistant.tts.trigger_barge_in()
            self._on_barge_in_fired()
            return True
        return False

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
            "barge_in_mode": tts.get_barge_in_mode(),
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
        if "barge_in_mode" in settings:
            tts.set_barge_in_mode(settings["barge_in_mode"])
        elif "barge_in" in settings:
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

    def speak_text(self, text: str) -> bool:
        """
        Speaks the provided text aloud using the active TTS voice and manages GUI states.
        """
        if not text or not text.strip():
            return False
        try:
            # Stop any currently playing audio first
            if self._assistant.tts.is_speaking():
                self._assistant.tts.stop()

            # Clean markdown formatting for clean spoken narration
            clean_text = text.replace("*", "").replace("#", "").replace("`", "").strip()
            paragraphs = [p.strip() for p in clean_text.split("\n\n") if p.strip()]
            spoken = " ".join(paragraphs[:2]) if paragraphs else clean_text
            if len(spoken) > 350:
                spoken = spoken[:350] + "..."

            self.notify_state("speaking")
            self._assistant.tts.speak(
                spoken,
                blocking=False,
                on_complete=lambda: self.notify_state("standby")
            )
            return True
        except Exception as e:
            logger.error(f"Bridge speak_text error: {e}")
            self.notify_state("standby")
            return False

    def respeak(self, text: str) -> bool:
        """Alias for speak_text called by UI Re-speak buttons."""
        return self.speak_text(text)

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

    # --- Screen Vision Bridge ---

    def analyze_screen(
        self,
        question: str = "Describe what is currently on the screen",
        focus_window: bool = False,
        speak_response: bool = True
    ) -> Dict[str, Any]:
        """
        Captures active screen or focused window and generates multimodal AI vision analysis.
        Returns analysis text and a base64 preview thumbnail for the GUI.
        """
        self.notify_state("thinking")
        try:
            from utils.vision import get_screen_preview_path
            import base64

            # Run analysis through registry
            analysis = self._assistant.tools._tool_analyze_screen(
                question=question,
                focus_window=focus_window
            )

            # Get base64 preview thumbnail if available
            preview_b64 = ""
            prev_path = get_screen_preview_path()
            if prev_path and prev_path.exists():
                try:
                    with open(prev_path, "rb") as f:
                        preview_b64 = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('utf-8')}"
                except Exception as ex:
                    logger.debug(f"Preview load error: {ex}")

            if speak_response and self._assistant.tts.enabled:
                # Provide a natural spoken summary (first 2 sentences or first bullet)
                paragraphs = [p for p in analysis.split("\n\n") if p.strip()]
                first_para = paragraphs[0] if paragraphs else analysis
                spoken_text = first_para.replace("*", "").replace("#", "").strip()
                if len(spoken_text) > 280:
                    spoken_text = spoken_text[:280] + "..."
                self._assistant.tts.speak(spoken_text)
                self.notify_state("speaking")
            else:
                self.notify_state("standby")

            return {
                "status": "success",
                "question": question,
                "analysis": analysis,
                "preview_base64": preview_b64,
                "focus_window": focus_window
            }
        except Exception as e:
            self.notify_state("standby")
            logger.error(f"Bridge screen analysis error: {e}")
            return {
                "status": "error",
                "message": str(e),
                "analysis": f"Screen analysis encountered an error: {e}",
                "preview_base64": ""
            }

    def analyze_uploaded_image(
        self,
        image_base64: str,
        question: str = "Analyze this image in detail",
        speak_response: bool = True
    ) -> Dict[str, Any]:
        """
        Analyzes a user-uploaded image or screenshot using multimodal AI vision.
        """
        self.notify_state("thinking")
        try:
            raw_b64 = image_base64
            if "base64," in raw_b64:
                raw_b64 = raw_b64.split("base64,")[1]

            analysis = self._assistant.tools._tool_analyze_screen(
                question=question,
                image_base64=raw_b64
            )

            preview_b64 = image_base64 if image_base64.startswith("data:") else f"data:image/jpeg;base64,{raw_b64}"

            if speak_response and self._assistant.tts.enabled:
                paragraphs = [p for p in analysis.split("\n\n") if p.strip()]
                first_para = paragraphs[0] if paragraphs else analysis
                spoken_text = first_para.replace("*", "").replace("#", "").strip()
                if len(spoken_text) > 280:
                    spoken_text = spoken_text[:280] + "..."
                self._assistant.tts.speak(spoken_text)
                self.notify_state("speaking")
            else:
                self.notify_state("standby")

            return {
                "status": "success",
                "question": question,
                "analysis": analysis,
                "preview_base64": preview_b64,
                "is_upload": True
            }
        except Exception as e:
            self.notify_state("standby")
            logger.error(f"Bridge image analysis error: {e}")
            return {
                "status": "error",
                "message": str(e),
                "analysis": f"Image analysis encountered an error: {e}",
                "preview_base64": image_base64
            }

    # --- Phase 5: Knowledge Vault & Document Intelligence Bridge ---

    def ingest_document(self, base64_data: str, filename: str) -> Dict[str, Any]:
        """
        Ingests and indexes a local document (PDF, DOCX, Code, Text, Resume) into the Knowledge Vault.
        """
        try:
            raw_b64 = base64_data
            if "base64," in raw_b64:
                raw_b64 = raw_b64.split("base64,")[1]
            file_bytes = base64.b64decode(raw_b64)

            result = self._assistant.tools.documents.ingest_file(
                source=file_bytes,
                filename=filename,
                save_copy=True
            )
            return result
        except Exception as e:
            logger.error(f"Bridge document ingestion error: {e}")
            return {"status": "error", "message": str(e)}

    def get_documents(self) -> List[Dict[str, Any]]:
        """Returns list of indexed documents in the Knowledge Vault."""
        try:
            return self._assistant.tools.documents.list_documents()
        except Exception as e:
            logger.error(f"Bridge get_documents error: {e}")
            return []

    def delete_document(self, doc_id: str) -> Dict[str, Any]:
        """Removes a document from the Knowledge Vault."""
        try:
            success = self._assistant.tools.documents.delete_document(doc_id)
            return {"status": "success" if success else "not_found", "doc_id": doc_id}
        except Exception as e:
            logger.error(f"Bridge delete_document error: {e}")
            return {"status": "error", "message": str(e)}

    def query_document(
        self,
        query: str,
        doc_id: Optional[str] = None,
        speak_response: bool = True
    ) -> Dict[str, Any]:
        """
        Queries indexed documents using local RAG.
        """
        self.notify_state("thinking")
        try:
            result = self._assistant.tools.documents.answer_query(
                query=query,
                doc_id=doc_id,
                llm_client=self._assistant.llm
            )

            answer = result.get("answer", "")
            if speak_response and self._assistant.tts.enabled and answer:
                paragraphs = [p for p in answer.split("\n\n") if p.strip()]
                first_para = paragraphs[0] if paragraphs else answer
                spoken = first_para.replace("*", "").replace("#", "").strip()
                if len(spoken) > 280:
                    spoken = spoken[:280] + "..."
                self._assistant.tts.speak(spoken)
                self.notify_state("speaking")
            else:
                self.notify_state("standby")

            return result
        except Exception as e:
            self.notify_state("standby")
            logger.error(f"Bridge query_document error: {e}")
            return {"status": "error", "answer": f"Error querying documents: {e}", "citations": []}

    def summarize_document(
        self,
        doc_id: Optional[str] = None,
        focus: Optional[str] = None,
        speak_response: bool = True
    ) -> Dict[str, Any]:
        """
        Generates an executive summary of an indexed document.
        """
        self.notify_state("thinking")
        try:
            result = self._assistant.tools.documents.summarize_document(
                doc_id=doc_id,
                focus=focus,
                llm_client=self._assistant.llm
            )

            summary = result.get("summary", "")
            if speak_response and self._assistant.tts.enabled and summary:
                paragraphs = [p for p in summary.split("\n\n") if p.strip()]
                first_para = paragraphs[0] if paragraphs else summary
                spoken = first_para.replace("*", "").replace("#", "").strip()
                if len(spoken) > 280:
                    spoken = spoken[:280] + "..."
                self._assistant.tts.speak(spoken)
                self.notify_state("speaking")
            else:
                self.notify_state("standby")

            return result
        except Exception as e:
            self.notify_state("standby")
            logger.error(f"Bridge summarize_document error: {e}")
            return {"status": "error", "summary": f"Failed to summarize document: {e}"}

    # --- Phase 6: Hands-Free WhatsApp & Email Bridge ---

    def send_whatsapp(self, recipient: str, message: str, auto_send: bool = True) -> Dict[str, Any]:
        """Dispatches a WhatsApp message."""
        try:
            res = self._assistant.tools.whatsapp.send_message(
                recipient=recipient,
                message=message,
                auto_send=auto_send
            )
            if res.get("status") == "success" and self._assistant.tts.enabled:
                self._assistant.tts.speak(f"Dispatched WhatsApp to {res.get('recipient_name', recipient)}.")
                self.notify_state("speaking")
            return res
        except Exception as e:
            logger.error(f"Bridge send_whatsapp error: {e}")
            return {"status": "error", "message": str(e)}

    def send_email(self, to: str, subject: str, body: str, attachment_path: Optional[str] = None, auto_send: bool = True) -> Dict[str, Any]:
        """Sends an email via SMTP or opens default email client with hands-free dispatch."""
        try:
            res = self._assistant.tools.email.send_email(
                to=to,
                subject=subject,
                body=body,
                attachment_path=attachment_path,
                auto_send=auto_send
            )
            if res.get("status") == "success" and self._assistant.tts.enabled:
                to_name = res.get("recipient_name", to)
                mode = res.get("mode", "")
                if mode == "smtp_direct":
                    self._assistant.tts.speak(f"Email sent successfully to {to_name}.")
                else:
                    if auto_send:
                        self._assistant.tts.speak(f"Sent email to {to_name} regarding {subject}.")
                    else:
                        self._assistant.tts.speak(f"Opened email draft to {to_name} in your mail client.")
                self.notify_state("speaking")
            return res
        except Exception as e:
            logger.error(f"Bridge send_email error: {e}")
            return {"status": "error", "message": str(e)}

    def draft_email(self, instruction: str, recipient: Optional[str] = None, tone: str = "professional") -> Dict[str, Any]:
        """Drafts an email using AI."""
        self.notify_state("thinking")
        try:
            res = self._assistant.tools.email.draft_email(
                instruction=instruction,
                recipient=recipient,
                tone=tone,
                llm_client=self._assistant.llm
            )
            self.notify_state("standby")
            return res
        except Exception as e:
            self.notify_state("standby")
            logger.error(f"Bridge draft_email error: {e}")
            return {"status": "error", "message": str(e)}

    def check_unread_emails(self, limit: int = 5, speak_response: bool = True) -> Dict[str, Any]:
        """Checks unread emails via IMAP."""
        self.notify_state("thinking")
        try:
            res = self._assistant.tools.email.check_unread_emails(limit=limit)
            summary = res.get("summary", "")
            if speak_response and self._assistant.tts.enabled and summary:
                self._assistant.tts.speak(summary)
                self.notify_state("speaking")
            else:
                self.notify_state("standby")
            return res
        except Exception as e:
            self.notify_state("standby")
            logger.error(f"Bridge check_unread_emails error: {e}")
            return {"status": "error", "message": str(e), "summary": f"Could not check email: {e}"}

    def get_contacts(self, query: str = "") -> List[Dict[str, Any]]:
        """Returns list of contacts."""
        try:
            return self._assistant.tools.contacts.list_contacts(query=query)
        except Exception as e:
            logger.error(f"Bridge get_contacts error: {e}")
            return []

    def save_contact(
        self,
        name: str,
        phone: str = "",
        email: str = "",
        nickname: str = "",
        notes: str = "",
        contact_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Adds or updates a contact."""
        try:
            if contact_id:
                c = self._assistant.tools.contacts.update_contact(
                    contact_id=contact_id,
                    name=name,
                    phone=phone,
                    email=email,
                    nickname=nickname,
                    notes=notes
                )
                if c:
                    return {"status": "success", "action": "updated", "contact": c}
                return {"status": "not_found", "message": "Contact ID not found."}
            else:
                c = self._assistant.tools.contacts.add_contact(
                    name=name,
                    phone=phone,
                    email=email,
                    nickname=nickname,
                    notes=notes
                )
                return {"status": "success", "action": "added", "contact": c}
        except Exception as e:
            logger.error(f"Bridge save_contact error: {e}")
            return {"status": "error", "message": str(e)}

    def delete_contact(self, contact_id: str) -> Dict[str, Any]:
        """Deletes a contact."""
        try:
            ok = self._assistant.tools.contacts.delete_contact(contact_id)
            return {"status": "success" if ok else "not_found", "contact_id": contact_id}
        except Exception as e:
            logger.error(f"Bridge delete_contact error: {e}")
            return {"status": "error", "message": str(e)}

    def get_email_config(self) -> Dict[str, Any]:
        """Returns email configuration with password masked."""
        cfg = dict(self._assistant.tools.email.config)
        if cfg.get("email_password"):
            cfg["email_password"] = "••••••••"
            cfg["has_password"] = True
        else:
            cfg["has_password"] = False
        return cfg

    def save_email_config(
        self,
        email_address: str,
        email_password: str,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
        imap_server: str = "imap.gmail.com",
        imap_port: int = 993,
        display_name: str = "Joshua"
    ) -> Dict[str, Any]:
        """Saves updated email credentials."""
        try:
            # If user didn't change masked password, keep existing
            if email_password == "••••••••":
                email_password = self._assistant.tools.email.config.get("email_password", "")
            return self._assistant.tools.email.save_config(
                email_address=email_address,
                email_password=email_password,
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                imap_server=imap_server,
                imap_port=imap_port,
                display_name=display_name
            )
        except Exception as e:
            logger.error(f"Bridge save_email_config error: {e}")
            return {"status": "error", "message": str(e)}

    # --- Phase 8: Web Automation & Live Price Checks ---

    def check_prices(self, query: str, sites: Optional[List[str]] = None, speak: bool = True) -> Dict[str, Any]:
        """Compares product prices across e-commerce platforms."""
        self.notify_state("thinking")
        try:
            res = self._assistant.tools.web.check_product_prices(product_name=query, sites=sites)
            if res.get("status") == "success" and speak and self._assistant.tts.enabled:
                self._assistant.tts.speak(res.get("summary", f"Finished price check for {query}."))
                self.notify_state("speaking")
            else:
                self.notify_state("standby")
            return res
        except Exception as e:
            self.notify_state("standby")
            logger.error(f"Bridge check_prices error: {e}")
            return {"status": "error", "message": str(e)}

    def scrape_url(self, url: str, mode: str = "content", speak: bool = True) -> Dict[str, Any]:
        """Scrapes text, markdown, or tables from a live URL."""
        self.notify_state("thinking")
        try:
            res = self._assistant.tools.web.scrape_webpage(url=url, mode=mode)
            if res.get("status") == "success" and speak and self._assistant.tts.enabled:
                self._assistant.tts.speak(res.get("summary", f"Extracted content from {url}."))
                self.notify_state("speaking")
            else:
                self.notify_state("standby")
            return res
        except Exception as e:
            self.notify_state("standby")
            logger.error(f"Bridge scrape_url error: {e}")
            return {"status": "error", "message": str(e)}

    def capture_web_screenshot(self, url: str, full_page: bool = False) -> Dict[str, Any]:
        """Captures a screenshot of a live webpage."""
        self.notify_state("thinking")
        try:
            res = self._assistant.tools.web.capture_webpage_screenshot(url=url, full_page=full_page)
            if res.get("status") == "success" and res.get("screenshot_path"):
                p = Path(res["screenshot_path"])
                if p.exists():
                    import base64
                    with open(p, "rb") as f:
                        res["preview_base64"] = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"
            self.notify_state("standby")
            return res
        except Exception as e:
            self.notify_state("standby")
            logger.error(f"Bridge capture_web_screenshot error: {e}")
            return {"status": "error", "message": str(e)}
