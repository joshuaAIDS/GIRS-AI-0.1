"""
Hands-Free Email Automation & AI Drafting Engine for IGIRS AI.
Supports direct SMTP dispatch, IMAP unread checking, AI-powered smart drafting,
and automatic fallback to native Windows mail clients via mailto: protocols.
"""
import os
import re
import json
import smtplib
import imaplib
import email
import logging
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import decode_header
from typing import Dict, Any, List, Optional
from pathlib import Path

import config
from tools.contacts_manager import ContactsManager

logger = logging.getLogger("IGIRS.EmailEngine")

class EmailEngine:
    def __init__(self, contacts_manager: Optional[ContactsManager] = None):
        self.contacts = contacts_manager or ContactsManager()
        self.config_file = config.EMAIL_CONFIG_FILE
        self.config: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Loads email credentials and server configuration."""
        defaults = {
            "smtp_server": os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
            "smtp_port": int(os.environ.get("SMTP_PORT", 587)),
            "smtp_use_tls": True,
            "imap_server": os.environ.get("IMAP_SERVER", "imap.gmail.com"),
            "imap_port": int(os.environ.get("IMAP_PORT", 993)),
            "email_address": os.environ.get("SMTP_EMAIL", ""),
            "email_password": os.environ.get("SMTP_PASSWORD", ""),
            "display_name": "Joshua"
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    defaults.update(saved)
            except Exception as e:
                logger.error(f"Failed to read email config file: {e}")

        return defaults

    def save_config(
        self,
        email_address: str,
        email_password: str,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
        imap_server: str = "imap.gmail.com",
        imap_port: int = 993,
        display_name: str = "Joshua"
    ) -> Dict[str, Any]:
        """Saves updated email credentials to disk."""
        self.config.update({
            "email_address": email_address.strip(),
            "email_password": email_password.strip(),
            "smtp_server": smtp_server.strip(),
            "smtp_port": int(smtp_port),
            "imap_server": imap_server.strip(),
            "imap_port": int(imap_port),
            "display_name": display_name.strip()
        })
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
            logger.info("Saved email configuration.")
            return {"status": "success", "message": "Email settings saved successfully."}
        except Exception as e:
            logger.error(f"Failed to write email config: {e}")
            return {"status": "error", "message": str(e)}

    def is_smtp_configured(self) -> bool:
        """Returns True if sender email and password are provided."""
        return bool(self.config.get("email_address") and self.config.get("email_password"))

    def resolve_recipient_email(self, target: str) -> Dict[str, str]:
        """Resolves contact name/nickname or raw email string."""
        target = target.strip()
        contact = self.contacts.get_contact(target)
        if contact and contact.get("email"):
            return {
                "name": contact.get("name", target),
                "email": contact["email"]
            }

        # Check if target is directly an email address
        if "@" in target and "." in target:
            return {"name": target.split("@")[0].title(), "email": target}

        return {"name": target, "email": ""}

    def draft_email(
        self,
        instruction: str,
        recipient: Optional[str] = None,
        tone: str = "professional",
        llm_client = None
    ) -> Dict[str, Any]:
        """
        Uses NVIDIA NIM LLM to draft a structured subject and body from user instructions.
        """
        instruction = instruction.strip()
        rec_info = self.resolve_recipient_email(recipient) if recipient else {"name": "Recipient", "email": ""}

        system_prompt = (
            "You are IGIRS AI Email Assistant. Given a brief request, draft a complete, polished email.\n"
            f"Tone: {tone}.\n"
            f"Recipient Name: {rec_info['name']}\n"
            "Respond strictly in this JSON format without markdown ticks:\n"
            "{\n"
            '  "subject": "Clear, concise subject line",\n'
            '  "body": "Complete, polite email body including salutation and sign-off from Joshua"\n'
            "}"
        )

        user_content = f"Instruction: {instruction}"

        # If LLM client available, invoke LLM
        if llm_client:
            try:
                raw = ""
                if hasattr(llm_client, "chat_completion"):
                    resp = llm_client.chat_completion(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content}
                        ],
                        max_tokens=400
                    )
                    choices = resp.get("choices", [])
                    if choices:
                        raw = choices[0].get("message", {}).get("content", "").strip()
                elif hasattr(llm_client, "chat"):
                    raw = str(llm_client.chat(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content}
                        ],
                        max_tokens=400
                    )).strip()

                if raw:
                    if "```json" in raw:
                        raw = raw.split("```json")[1].split("```")[0].strip()
                    elif "```" in raw:
                        raw = raw.split("```")[1].split("```")[0].strip()

                    try:
                        parsed = json.loads(raw, strict=False)
                    except Exception:
                        sub_match = re.search(r'"subject"\s*:\s*"([^"]+)"', raw)
                        body_match = re.search(r'"body"\s*:\s*"([\s\S]*?)"\s*\}', raw)
                        parsed = {
                            "subject": sub_match.group(1) if sub_match else f"Regarding {instruction[:40]}",
                            "body": body_match.group(1).replace('\\n', '\n').replace('\\"', '"') if body_match else instruction
                        }

                    return {
                        "status": "success",
                        "subject": parsed.get("subject", "Regarding your request"),
                        "body": parsed.get("body", instruction),
                        "recipient_name": rec_info["name"],
                        "recipient_email": rec_info["email"]
                    }
            except Exception as e:
                logger.warning(f"LLM email drafting failed: {e}. Falling back to rule-based draft.")

        # Rule-based fallback draft
        subject = f"Regarding {instruction[:40]}"
        body = (
            f"Hi {rec_info['name']},\n\n"
            f"I am writing regarding the following:\n{instruction}\n\n"
            "Please let me know if you have any questions or need further details.\n\n"
            "Best regards,\nJoshua"
        )
        return {
            "status": "success",
            "subject": subject,
            "body": body,
            "recipient_name": rec_info["name"],
            "recipient_email": rec_info["email"]
        }

    def open_in_mail_client(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """
        Opens the system's default email client (e.g. Windows Mail, Outlook) pre-filled via mailto:.
        """
        enc_to = urllib.parse.quote(to)
        enc_sub = urllib.parse.quote(subject)
        enc_body = urllib.parse.quote(body)
        mailto_url = f"mailto:{enc_to}?subject={enc_sub}&body={enc_body}"

        try:
            os.startfile(mailto_url)
            return {
                "status": "success",
                "mode": "mailto_client",
                "to": to,
                "subject": subject,
                "message": f"Opened default email client with draft for {to}."
            }
        except Exception as e:
            try:
                import webbrowser
                webbrowser.open(mailto_url)
                return {
                    "status": "success",
                    "mode": "mailto_browser",
                    "to": to,
                    "subject": subject,
                    "message": f"Opened email draft in browser for {to}."
                }
            except Exception as ex:
                logger.error(f"Failed to open mailto URL: {ex}")
                return {"status": "error", "message": f"Could not launch email client: {ex}"}

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        attachment_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends an email directly via SMTP SSL/TLS if configured, or falls back to the native mail client.
        """
        rec_info = self.resolve_recipient_email(to)
        target_email = rec_info["email"]

        if not target_email:
            return {
                "status": "error",
                "message": f"Recipient '{to}' does not have a valid email address."
            }

        # If SMTP credentials are NOT configured, launch native mail client directly
        if not self.is_smtp_configured():
            logger.info("SMTP credentials not configured in email_config.json. Launching native mail client.")
            res = self.open_in_mail_client(target_email, subject, body)
            res["summary"] = f"Opened email draft to {rec_info['name']} ({target_email}) in default mail client."
            return res

        # Attempt direct SMTP dispatch
        sender_email = self.config["email_address"]
        sender_pass = self.config["email_password"]
        smtp_host = self.config.get("smtp_server", "smtp.gmail.com")
        smtp_port = int(self.config.get("smtp_port", 587))
        display_name = self.config.get("display_name", "Joshua")

        try:
            msg = MIMEMultipart()
            msg["From"] = f"{display_name} <{sender_email}>"
            msg["To"] = target_email
            msg["Subject"] = subject

            # Plain text body
            msg.attach(MIMEText(body, "plain", "utf-8"))

            # Handle optional attachment
            if attachment_path and Path(attachment_path).exists():
                p = Path(attachment_path)
                with open(p, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={p.name}")
                msg.attach(part)

            # Send via SMTP
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=12)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=12)
                if self.config.get("smtp_use_tls", True):
                    server.starttls()

            server.login(sender_email, sender_pass)
            server.sendmail(sender_email, [target_email], msg.as_string())
            server.quit()

            logger.info(f"✔ Successfully sent email to {target_email} via SMTP ({smtp_host})")
            return {
                "status": "success",
                "mode": "smtp_direct",
                "to": target_email,
                "recipient_name": rec_info["name"],
                "subject": subject,
                "summary": f"Sent email to {rec_info['name']} ({target_email}) with subject: '{subject}'."
            }
        except Exception as e:
            logger.warning(f"SMTP send failed: {e}. Opening default mail client fallback.")
            # Graceful fallback to mail client
            fallback_res = self.open_in_mail_client(target_email, subject, body)
            fallback_res["smtp_error"] = str(e)
            fallback_res["summary"] = f"SMTP connection failed ({e}). Opened email draft in your default mail client instead."
            return fallback_res

    def check_unread_emails(self, limit: int = 5) -> Dict[str, Any]:
        """
        Connects via IMAP SSL to check recent unread emails.
        """
        if not self.is_smtp_configured():
            return {
                "status": "not_configured",
                "unread_count": 0,
                "emails": [],
                "message": "Email credentials not yet configured in Knowledge Vault or settings. Configure an App Password to enable inbox checks.",
                "summary": "Email credentials are not configured yet, Joshua. You can add them in the Comm settings tab."
            }

        imap_host = self.config.get("imap_server", "imap.gmail.com")
        imap_port = int(self.config.get("imap_port", 993))
        user_email = self.config["email_address"]
        user_pass = self.config["email_password"]

        try:
            mail = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=12)
            mail.login(user_email, user_pass)
            mail.select("INBOX", readonly=True)

            status, search_data = mail.search(None, "UNSEEN")
            if status != "OK":
                mail.logout()
                return {"status": "error", "message": "Could not search inbox."}

            msg_ids = search_data[0].split()
            unread_count = len(msg_ids)

            if unread_count == 0:
                mail.logout()
                return {
                    "status": "success",
                    "unread_count": 0,
                    "emails": [],
                    "summary": "You have no unread emails in your inbox right now, Joshua."
                }

            # Fetch top unread
            recent_ids = msg_ids[-limit:][::-1]
            unread_list = []

            for mid in recent_ids:
                res, data = mail.fetch(mid, "(RFC822.HEADER)")
                if res != "OK":
                    continue
                msg = email.message_from_bytes(data[0][1])

                # Decode subject
                subject_header = decode_header(msg.get("Subject", "No Subject"))[0]
                subject_text = subject_header[0]
                if isinstance(subject_text, bytes):
                    encoding = subject_header[1] or "utf-8"
                    try:
                        subject_text = subject_text.decode(encoding, errors="replace")
                    except Exception:
                        subject_text = subject_text.decode("latin-1", errors="replace")

                # Decode sender
                from_header = msg.get("From", "Unknown Sender")

                unread_list.append({
                    "id": mid.decode("utf-8"),
                    "sender": from_header,
                    "subject": subject_text,
                    "date": msg.get("Date", "")
                })

            mail.logout()

            # Formulate spoken voice summary
            summary = f"You have {unread_count} unread email{'s' if unread_count != 1 else ''}. "
            if unread_list:
                first = unread_list[0]
                clean_sender = first['sender'].split("<")[0].replace('"', '').strip()
                summary += f"The latest is from {clean_sender} regarding '{first['subject']}'."

            return {
                "status": "success",
                "unread_count": unread_count,
                "emails": unread_list,
                "summary": summary
            }
        except Exception as e:
            logger.error(f"IMAP check error: {e}")
            return {
                "status": "error",
                "message": str(e),
                "summary": f"Could not check your inbox: {e}"
            }
