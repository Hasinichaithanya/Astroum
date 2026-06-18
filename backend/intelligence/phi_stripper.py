"""
PHI Stripper — Protected Health Information detection and redaction.

Detects and redacts before sending to external APIs:
  - Patient names
  - Room/bed numbers
  - Specific dates
  - Phone numbers
  - Aadhaar numbers (Indian national ID)
  - Ages (context-dependent)
  - Hospital-specific identifiers

Returns redacted text + log of what was stripped.
"""

from __future__ import annotations
import re
from dataclasses import dataclass


@dataclass
class PHIMatch:
    phi_type: str       # NAME | ROOM | DATE | PHONE | ID | AGE
    original: str
    replacement: str
    start: int
    end: int


# Common Indian first names (subset for detection — not exhaustive, used as signal)
COMMON_FIRST_NAMES = {
    # Telugu names
    "ramaiah", "venkat", "suresh", "krishna", "srinivas", "lakshmi", "padma",
    "ravi", "anand", "prasad", "vijay", "kumar", "naidu", "reddy", "rao",
    # Hindi names
    "ram", "shyam", "mohan", "sohan", "sunita", "priya", "deepa", "amit",
    "rajesh", "rahul", "pooja", "neha", "sharma", "verma", "gupta",
    # Tamil names
    "murugan", "selvam", "arjun", "karthik", "priya", "kavitha", "meena",
    "rajan", "kumar", "natarajan", "venkatesh", "palani",
    # Kannada names
    "suresh", "mahesh", "girish", "nagaraj", "manjunath", "basavaraju",
    # Common across regions
    "arun", "ajay", "vijay", "sanjay", "rohit", "mohit", "sumit",
    "anita", "kavita", "sunita", "geeta", "seema", "reena",
}

# PHI pattern definitions: (pattern, phi_type, replacement_template)
PHI_PATTERNS: list[tuple[str, str, str]] = [
    # Phone numbers (Indian: 10-digit starting with 6-9, or +91)
    (r"(?:\+91[\s-]?)?[6-9]\d{9}", "PHONE", "[PHONE]"),
    # Aadhaar (12 digits, often with spaces in groups of 4)
    (r"\b\d{4}\s?\d{4}\s?\d{4}\b", "ID", "[AADHAAR]"),
    # Room/bed numbers
    (r"\b(?:room|bed|ward|cabin|icu\s+bed)\s*(?:no\.?\s*)?\d+\w*\b", "ROOM", "[ROOM]"),
    (r"\b[A-Z]?\d{1,3}[A-Z]?\b(?=\s+(?:bed|room|ward|icu))", "ROOM", "[ROOM]"),
    # Dates
    (r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", "DATE", "[DATE]"),
    (r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
     r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
     r"\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4}\b", "DATE", "[DATE]"),
    # Ages with genders (common clinical pattern: "45M", "60F", "32 year old")
    (r"\b(\d{1,3})\s*(?:year[s]?\s*old|yr[s]?\s*old|y/o|yrs?)\b", "AGE", r"\1yo"),
    # MRN/patient ID patterns
    (r"\b(?:mrn|uhid|patient\s*id|pid)\s*:?\s*[A-Z0-9-]{4,15}\b", "ID", "[PATIENT_ID]"),
    # IP/OP numbers
    (r"\b(?:ip|op|ipd|opd)\s*(?:no\.?\s*)?\d+\b", "ID", "[ADMISSION_ID]"),
]

# Suffix patterns that indicate a name ("gari" = Mr./respected in Telugu)
NAME_SUFFIX_PATTERNS = [
    r"(\w+)\s+gari\b",          # Telugu honorific
    r"(\w+)\s+ji\b",            # Hindi honorific
    r"(\w+)\s+bhai\b",          # Hindi/Gujarati brother
    r"(\w+)\s+akka\b",          # Telugu sister
    r"(\w+)\s+anna\b",          # Telugu brother
    r"(\w+)\s+sir\b",           # English
    r"(\w+)\s+madam\b",         # English
    r"(\w+)\s+amma\b",          # Telugu/Tamil mother
    r"Mr\.?\s+(\w+)",           # Mr.
    r"Mrs\.?\s+(\w+)",          # Mrs.
    r"Dr\.?\s+(\w+)",           # Dr. (keep role, strip name)
    r"patient\s+(\w+)",         # "patient Ramaiah"
]


def strip_phi(text: str, redact_names: bool = True) -> tuple[str, list[PHIMatch]]:
    """
    Strip PHI from text.

    Args:
        text: Input text
        redact_names: Whether to also attempt name detection (lower confidence)

    Returns:
        (redacted_text, list_of_PHIMatch)
    """
    matches: list[PHIMatch] = []
    result = text

    # Apply pattern-based PHI redaction
    for pattern, phi_type, replacement in PHI_PATTERNS:
        for m in re.finditer(pattern, result, re.IGNORECASE):
            # Handle backreference in replacement
            repl = m.expand(replacement) if "\\" in replacement or r"\1" in replacement else replacement
            matches.append(PHIMatch(
                phi_type=phi_type,
                original=m.group(),
                replacement=repl,
                start=m.start(),
                end=m.end(),
            ))

    # Name detection via honorifics
    if redact_names:
        for pattern in NAME_SUFFIX_PATTERNS:
            for m in re.finditer(pattern, result, re.IGNORECASE):
                name_group = m.group(1) if m.lastindex else m.group()
                # Don't redact if it's a known medical term
                if len(name_group) > 2 and name_group.lower() not in {"the", "and", "for"}:
                    matches.append(PHIMatch(
                        phi_type="NAME",
                        original=m.group(),
                        replacement=m.group().replace(name_group, "[PATIENT]"),
                        start=m.start(),
                        end=m.end(),
                    ))

        # Common first name detection (only if followed by "gari" or similar)
        words = result.split()
        for i, word in enumerate(words):
            if word.lower() in COMMON_FIRST_NAMES:
                # Check context: surrounded by clinical text?
                context = " ".join(words[max(0, i-2):i+3]).lower()
                name_indicators = ["gari", "ji", "bhai", "akka", "anna", "patient", "ki", "ka", "ke", "ne"]
                if any(ind in context for ind in name_indicators):
                    matches.append(PHIMatch(
                        phi_type="NAME",
                        original=word,
                        replacement="[PATIENT]",
                        start=result.lower().find(word.lower()),
                        end=result.lower().find(word.lower()) + len(word),
                    ))

    # Apply replacements in reverse order to preserve positions
    matches_sorted = sorted(set((m.start, m.end, m.replacement, m.original, m.phi_type)
                                 for m in matches), key=lambda x: x[0], reverse=True)

    for start, end, replacement, original, phi_type in matches_sorted:
        result = result[:start] + replacement + result[end:]

    # Return unique matches
    unique_matches = []
    seen = set()
    for m in matches:
        key = (m.original, m.phi_type)
        if key not in seen:
            seen.add(key)
            unique_matches.append(m)

    return result, unique_matches


def phi_summary(text: str) -> dict:
    """Return JSON-serialisable PHI detection results."""
    redacted, matches = strip_phi(text)
    return {
        "original_length": len(text),
        "redacted_text": redacted,
        "phi_found": len(matches),
        "phi_types": list({m.phi_type for m in matches}),
        "items": [
            {"type": m.phi_type, "original": m.original, "replacement": m.replacement}
            for m in matches
        ],
    }
