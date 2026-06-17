"""
EntryActivator: activates lore entries based on keywords in recent history.

Keywords are case‑insensitive substrings (not individual words).
Supports logic: ANY (at least one keyword matches) or ALL (all keywords match).
"""

import re
from typing import List, Dict, Any, Set


class EntryActivator:
    """
    Activates lorebook entries based on:
    - state == "always_active" → always included
    - state == "activate_on_keyword" → check keyword matching in history
    - state == "deactivated" → never included
    """

    def __init__(self, lorebook_storage):
        """
        Args:
            lorebook_storage: LorebookStorage instance to read entries.
        """
        self.lorebook = lorebook_storage

    def activate(self, history_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Return a list of activated entries (full dicts).

        Args:
            history_messages: List of message dicts with 'content' field.
                              Typically from timeline (non‑system messages).

        Returns:
            List of entry dicts that are active.
        """
        all_entries = self.lorebook.get_collection("entries")
        if not all_entries:
            return []

        # Combine all history text into one string for keyword searching
        combined_text = " ".join(msg.get("content", "") for msg in history_messages)
        combined_text_lower = combined_text.lower()

        result = []
        for entry in all_entries:
            state = entry.get("state", "deactivated")
            if state == "always_active":
                result.append(entry)
            elif state == "activate_on_keyword":
                if self._matches(entry, combined_text_lower):
                    result.append(entry)
            # state == "deactivated" → skip
        return result

    def _matches(self, entry: Dict[str, Any], text_lower: str) -> bool:
        """
        Check if the entry's keywords match the given text (case‑insensitive).
        """
        keywords = entry.get("keywords", [])
        if not keywords:
            return False

        # Clean keywords: strip whitespace, ignore empty strings
        cleaned = [kw.strip() for kw in keywords if kw.strip()]
        if not cleaned:
            return False

        logic = entry.get("logic", "ANY")

        if logic == "ANY":
            # At least one keyword must appear in the text
            for kw in cleaned:
                if kw.lower() in text_lower:
                    return True
            return False

        elif logic == "ALL":
            # All keywords must appear in the text
            for kw in cleaned:
                if kw.lower() not in text_lower:
                    return False
            return True

        # Fallback: ANY
        return False