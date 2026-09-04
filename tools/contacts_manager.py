"""
Contacts Manager for IGIRS AI.
Provides local JSON-backed personal address book with phone normalization,
fuzzy nickname resolution (e.g. 'Mom', 'Boss', 'Karthik'), and full CRUD support.
"""
import re
import json
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import config

logger = logging.getLogger("IGIRS.ContactsManager")

class ContactsManager:
    def __init__(self, store_file: Optional[Path] = None):
        self.store_file = store_file or config.CONTACTS_FILE
        self.contacts: Dict[str, Dict[str, Any]] = {}
        self._load_contacts()

    def _load_contacts(self):
        """Loads contacts from disk or initializes default profile."""
        if self.store_file.exists():
            try:
                with open(self.store_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.contacts = data
                    elif isinstance(data, list):
                        self.contacts = {c.get("id", str(uuid.uuid4())[:8]): c for c in data}
                    logger.info(f"Loaded {len(self.contacts)} contacts from {self.store_file.name}")
                    return
            except Exception as e:
                logger.error(f"Failed to load contacts file: {e}")

        # Default starter contacts
        self.contacts = {
            "c_self": {
                "id": "c_self",
                "name": "Joshua",
                "nickname": "Me",
                "phone": "+919876543210",
                "email": "joshua@example.com",
                "notes": "Primary User Profile"
            }
        }
        self._save_contacts()

    def _save_contacts(self):
        """Saves current contacts dictionary to disk."""
        try:
            with open(self.store_file, "w", encoding="utf-8") as f:
                json.dump(self.contacts, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save contacts: {e}")

    @staticmethod
    def normalize_phone(phone: str, default_country_code: str = config.DEFAULT_COUNTRY_CODE) -> str:
        """
        Cleans and normalizes phone numbers into E.164-compatible format.
        Example: '98765 43210' -> '+919876543210'.
        """
        if not phone:
            return ""
        # Remove all whitespace, dashes, parens
        cleaned = re.sub(r"[^\d+]", "", str(phone).strip())
        if not cleaned:
            return ""

        # If already starts with '+', return
        if cleaned.startswith("+"):
            return cleaned

        # If starts with '00', replace with '+'
        if cleaned.startswith("00"):
            return "+" + cleaned[2:]

        # If 10-digit number (common in India/US), prepend default country code
        if len(cleaned) == 10:
            prefix = default_country_code if default_country_code.startswith("+") else f"+{default_country_code}"
            return f"{prefix}{cleaned}"

        # If 12 digits starting with 91, add '+'
        if len(cleaned) == 12 and cleaned.startswith("91"):
            return f"+{cleaned}"

        # Fallback: add '+' if purely digits
        return f"+{cleaned}"

    def add_contact(
        self,
        name: str,
        phone: str = "",
        email: str = "",
        nickname: str = "",
        notes: str = ""
    ) -> Dict[str, Any]:
        """Adds a new contact to the address book."""
        name = name.strip()
        if not name:
            raise ValueError("Contact name cannot be empty.")

        contact_id = f"c_{uuid.uuid4().hex[:8]}"
        norm_phone = self.normalize_phone(phone)
        clean_email = email.strip().lower()

        contact = {
            "id": contact_id,
            "name": name,
            "nickname": nickname.strip(),
            "phone": norm_phone,
            "email": clean_email,
            "notes": notes.strip()
        }

        self.contacts[contact_id] = contact
        self._save_contacts()
        logger.info(f"Added contact: {name} (Nickname: {nickname}, Phone: {norm_phone}, Email: {clean_email})")
        return contact

    def update_contact(self, contact_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Updates fields of an existing contact."""
        if contact_id not in self.contacts:
            return None

        contact = self.contacts[contact_id]
        if "name" in kwargs and kwargs["name"]:
            contact["name"] = str(kwargs["name"]).strip()
        if "nickname" in kwargs:
            contact["nickname"] = str(kwargs["nickname"]).strip()
        if "phone" in kwargs:
            contact["phone"] = self.normalize_phone(kwargs["phone"])
        if "email" in kwargs:
            contact["email"] = str(kwargs["email"]).strip().lower()
        if "notes" in kwargs:
            contact["notes"] = str(kwargs["notes"]).strip()

        self._save_contacts()
        return contact

    def delete_contact(self, contact_id: str) -> bool:
        """Removes a contact by ID."""
        if contact_id in self.contacts:
            del self.contacts[contact_id]
            self._save_contacts()
            return True
        return False

    def get_contact(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Finds a contact by ID, nickname, name (exact or substring), phone, or email.
        Prioritizes exact nickname matches (e.g. 'Mom', 'Boss', 'Dad').
        """
        if not query or not query.strip():
            return None

        q = query.strip().lower()

        # 1. Exact ID match
        if query in self.contacts:
            return self.contacts[query]

        # 2. Exact nickname match (case-insensitive)
        for c in self.contacts.values():
            if c.get("nickname") and c["nickname"].strip().lower() == q:
                return c

        # 3. Exact full name match
        for c in self.contacts.values():
            if c.get("name") and c["name"].strip().lower() == q:
                return c

        # 4. Normalized phone match
        clean_q_phone = re.sub(r"[^\d+]", "", q)
        if clean_q_phone:
            for c in self.contacts.values():
                c_phone = re.sub(r"[^\d+]", "", c.get("phone", ""))
                if c_phone and (clean_q_phone in c_phone or c_phone in clean_q_phone):
                    return c

        # 5. Email match
        for c in self.contacts.values():
            if c.get("email") and q in c["email"].lower():
                return c

        # 6. Substring name or nickname match
        for c in self.contacts.values():
            if q in c.get("name", "").lower() or q in c.get("nickname", "").lower():
                return c

        return None

    def list_contacts(self, query: str = "") -> List[Dict[str, Any]]:
        """Returns list of contacts sorted by name, optionally filtered by query."""
        all_contacts = list(self.contacts.values())
        all_contacts.sort(key=lambda x: x.get("name", "").lower())

        if not query or not query.strip():
            return all_contacts

        q = query.strip().lower()
        results = []
        for c in all_contacts:
            if (
                q in c.get("name", "").lower()
                or q in c.get("nickname", "").lower()
                or q in c.get("phone", "").lower()
                or q in c.get("email", "").lower()
                or q in c.get("notes", "").lower()
            ):
                results.append(c)
        return results
