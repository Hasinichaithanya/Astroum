"""
Dosage Extractor — parses dosage from code-mixed clinical text.

Handles:
  - Regional number words: "rendu tablet" → 2 tablets
  - Mixed: "ek tablet BD" → 1 tablet twice-daily
  - Fractional: "dedh tablet" (Hindi 1.5) → 1.5 tablets
  - Units: tablet, capsule, ml, mg, drop, puff, unit
  - Frequency: OD, BD, TDS, QDS, PRN, SOS, HS
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DosageInfo:
    quantity: Optional[float]        # numeric quantity (1, 2, 0.5, etc.)
    unit: Optional[str]              # tablet | capsule | ml | mg | drop | puff | unit
    frequency: Optional[str]         # once_daily | twice_daily | thrice_daily | four_times | as_needed | etc.
    frequency_raw: Optional[str]     # original token that gave frequency
    duration: Optional[str]          # "3 days" | "1 week" | "1 month" etc.
    route: Optional[str]             # oral | iv | im | sc | sublingual | topical
    raw_text: str = ""               # the matched text fragment
    confidence: float = 1.0


# ── Regional number word tables ───────────────────────────────────────────────

NUMBER_WORDS: dict[str, dict[str, float]] = {
    "te": {  # Telugu
        "oka": 1, "rendu": 2, "moodu": 3, "naalugu": 4, "aidu": 5,
        "aaru": 6, "edu": 7, "enimidi": 8, "thommidi": 9, "padhi": 10,
        "iravai": 20, "nooru": 100, "ardha": 0.5,
    },
    "hi": {  # Hindi
        "ek": 1, "do": 2, "teen": 3, "chaar": 4, "paanch": 5,
        "chhe": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10,
        "bees": 20, "sau": 100, "dedh": 1.5, "dhai": 2.5, "adha": 0.5,
        "aadha": 0.5, "savaa": 1.25, "paune": 0.75,
    },
    "ta": {  # Tamil
        "onnu": 1, "rendu": 2, "moonu": 3, "naalu": 4, "anju": 5,
        "aaru": 6, "ezhu": 7, "ettu": 8, "onpathu": 9, "pathu": 10,
        "iruvathu": 20, "nooru": 100, "arai": 0.5,
    },
    "kn": {  # Kannada
        "ondu": 1, "eradu": 2, "mooru": 3, "nalku": 4, "aidu": 5,
        "aaru": 6, "elu": 7, "entu": 8, "ombattu": 9, "hathu": 10,
        "ippathu": 20, "nooru": 100, "ardha": 0.5,
    },
    "ml": {  # Malayalam
        "onnu": 1, "randu": 2, "moonnu": 3, "naalu": 4, "anchu": 5,
        "aaru": 6, "ezhu": 7, "ettu": 8, "onpathu": 9, "pathu": 10,
        "iruppathu": 20, "nooru": 100, "ardham": 0.5,
    },
    "mr": {  # Marathi
        "ek": 1, "don": 2, "teen": 3, "chaar": 4, "paach": 5,
        "saha": 6, "saat": 7, "aath": 8, "nau": 9, "daha": 10,
        "vees": 20, "saha": 6, "dedh": 1.5, "adha": 0.5,
    },
    "bn": {  # Bengali
        "ek": 1, "dui": 2, "tin": 3, "char": 4, "panch": 5,
        "chhoy": 6, "shaat": 7, "aat": 8, "noy": 9, "dosh": 10,
        "bish": 20,
    },
    "gu": {  # Gujarati
        "ek": 1, "be": 2, "tran": 3, "char": 4, "panch": 5,
        "chha": 6, "saat": 7, "aath": 8, "nav": 9, "das": 10,
        "vis": 20, "dhoram": 0.5,
    },
}

# Flat lookup (language-agnostic, for code-mixed text)
FLAT_NUMBER_MAP: dict[str, float] = {}
for lang_words in NUMBER_WORDS.values():
    FLAT_NUMBER_MAP.update(lang_words)

# Unit patterns
UNIT_PATTERNS: dict[str, str] = {
    r"\btablets?\b": "tablet",
    r"\btabs?\b": "tablet",
    r"\tcap(?:sules?)?\b": "capsule",
    r"\bcaps?\b": "capsule",
    r"\bml\b": "ml",
    r"\bcc\b": "ml",
    r"\bmg\b": "mg",
    r"\bdrops?\b": "drop",
    r"\bpuffs?\b": "puff",
    r"\bunits?\b": "unit",
    r"\biu\b": "IU",
    r"\bspray\b": "spray",
    r"\bpatch\b": "patch",
    r"\bsachets?\b": "sachet",
    r"\bvials?\b": "vial",
    r"\bampules?\b": "ampule",
    r"\binjections?\b": "injection",
    r"\btablet\b": "tablet",
    r"\bgoli\b": "tablet",      # Hindi
    r"\bgollu\b": "tablet",     # Telugu
    r"\bmaathai\b": "tablet",   # Tamil
    r"\bmaatra\b": "tablet",    # Gujarati/Hindi
    r"\bmatra\b": "tablet",     # variant
    r"\bgolikalu\b": "tablet",  # Kannada plural
}

# Frequency patterns
FREQUENCY_MAP: dict[str, str] = {
    r"\bQDS\b": "four_times_daily",
    r"\bq\.?d\.?s\.?\b": "four_times_daily",
    r"\bTDS\b": "thrice_daily",
    r"\bt\.?d\.?s\.?\b": "thrice_daily",
    r"\bBD\b": "twice_daily",
    r"\bb\.?d\.?\b": "twice_daily",
    r"\bOD\b": "once_daily",
    r"\bo\.?d\.?\b": "once_daily",
    r"\bonce\s+daily\b": "once_daily",
    r"\btwice\s+daily\b": "twice_daily",
    r"\bthrice\s+daily\b": "thrice_daily",
    r"\bPRN\b": "as_needed",
    r"\bp\.?r\.?n\.?\b": "as_needed",
    r"\bSOS\b": "as_needed",
    r"\bHS\b": "at_bedtime",
    r"\bh\.?s\.?\b": "at_bedtime",
    r"\bSTAT\b": "immediately",
    r"\bimmediately\b": "immediately",
    r"\bat\s+bedtime\b": "at_bedtime",
    r"\bnightly\b": "at_bedtime",
    r"\bevery\s+(\d+)\s+hours?\b": "every_{n}_hours",
    r"\bthrice\s+a\s+week\b": "thrice_weekly",
    r"\bonce\s+a\s+week\b": "once_weekly",
    r"\bweekly\b": "once_weekly",
    r"\bmonthly\b": "once_monthly",
    r"\bdin\s+mein\s+teen\s+baar\b": "thrice_daily",   # Hindi
    r"\bdin\s+mein\s+do\s+baar\b": "twice_daily",       # Hindi
    r"\bdin\s+mein\s+ek\s+baar\b": "once_daily",        # Hindi
    r"\broju\s+moodu\b": "thrice_daily",                  # Telugu
    r"\broju\s+rendu\b": "twice_daily",                   # Telugu
    r"\broju\s+oka\s+sarI\b": "once_daily",              # Telugu
}

# Route patterns
ROUTE_MAP: dict[str, str] = {
    r"\boral(ly)?\b": "oral",
    r"\bpo\b": "oral",
    r"\bby\s+mouth\b": "oral",
    r"\biv\b": "iv",
    r"\bintravenous(ly)?\b": "iv",
    r"\bim\b": "im",
    r"\bintramuscular(ly)?\b": "im",
    r"\bsc\b": "sc",
    r"\bsubcutaneous(ly)?\b": "sc",
    r"\btopical(ly)?\b": "topical",
    r"\blocal(ly)?\b": "topical",
    r"\bsublingual(ly)?\b": "sublingual",
    r"\bsl\b": "sublingual",
    r"\binhaled\b": "inhaled",
    r"\brectal(ly)?\b": "rectal",
    r"\bpr\b": "rectal",
    r"\btransdermal(ly)?\b": "transdermal",
    r"\binhalation\b": "inhaled",
    r"\bnebulisation\b": "nebulised",
    r"\bnebulized\b": "nebulised",
}

# Duration patterns
DURATION_RE = re.compile(
    r"(?:for\s+)?(\d+)\s*(days?|weeks?|months?|years?|din|hafte|mahine|naal|varams?|maadham)",
    re.IGNORECASE,
)

ENGLISH_DURATION = {
    "day": "day", "days": "day", "din": "day",
    "week": "week", "weeks": "week", "hafte": "week", "varams": "week", "varam": "week",
    "month": "month", "months": "month", "mahine": "month", "maadham": "month",
    "year": "year", "years": "year",
    "naal": "day",  # Tamil
}


def _parse_number(token: str) -> Optional[float]:
    """Parse a number from a token — numeric or regional word."""
    token = token.strip().lower()
    try:
        return float(token)
    except ValueError:
        pass
    # Fraction
    if "/" in token:
        parts = token.split("/")
        try:
            return float(parts[0]) / float(parts[1])
        except Exception:
            pass
    return FLAT_NUMBER_MAP.get(token)


def extract_dosages(text: str) -> list[DosageInfo]:
    """
    Extract all dosage mentions from text.
    Returns list of DosageInfo objects.
    """
    results: list[DosageInfo] = []
    text_lower = text.lower()
    words = text.split()

    i = 0
    while i < len(words):
        word = words[i].lower().strip(".,;:()")
        qty = _parse_number(word)

        if qty is not None:
            # Found a number — look ahead for unit + frequency
            unit = None
            freq = None
            freq_raw = None
            duration = None
            route = None
            raw_parts = [words[i]]

            # Look at next 1-4 tokens for unit
            j = i + 1
            while j < min(i + 3, len(words)):
                next_word = words[j].lower().strip(".,;:()")
                for pat, u in UNIT_PATTERNS.items():
                    if re.search(pat, next_word, re.IGNORECASE):
                        unit = u
                        raw_parts.append(words[j])
                        j += 1
                        break
                else:
                    break

            # Look at next 1-3 tokens for frequency
            while j < min(i + 5, len(words)):
                next_word = words[j].strip(".,;:()")
                for pat, f in FREQUENCY_MAP.items():
                    if re.search(pat, next_word, re.IGNORECASE):
                        freq = f
                        freq_raw = next_word
                        raw_parts.append(words[j])
                        j += 1
                        break
                else:
                    break

            if unit or freq:  # Only record if we found something meaningful
                # Look for duration in remaining nearby text
                nearby = " ".join(words[i:min(i+8, len(words))])
                dur_m = DURATION_RE.search(nearby)
                if dur_m:
                    n = dur_m.group(1)
                    unit_str = ENGLISH_DURATION.get(dur_m.group(2).lower(), dur_m.group(2))
                    duration = f"{n} {unit_str}{'s' if int(n) > 1 else ''}"

                # Look for route
                for pat, r in ROUTE_MAP.items():
                    if re.search(pat, nearby, re.IGNORECASE):
                        route = r
                        break

                results.append(DosageInfo(
                    quantity=qty,
                    unit=unit,
                    frequency=freq,
                    frequency_raw=freq_raw,
                    duration=duration,
                    route=route,
                    raw_text=" ".join(raw_parts),
                    confidence=0.9 if unit and freq else 0.7,
                ))
        i += 1

    # Also scan for frequency patterns without explicit number (e.g. "TDS" alone)
    for pat, f in FREQUENCY_MAP.items():
        for m in re.finditer(pat, text, re.IGNORECASE):
            # Check not already captured
            already = any(d.frequency == f for d in results)
            if not already:
                results.append(DosageInfo(
                    quantity=None,
                    unit=None,
                    frequency=f,
                    frequency_raw=m.group(),
                    duration=None,
                    route=None,
                    raw_text=m.group(),
                    confidence=0.6,
                ))

    return results


def dosage_summary(text: str) -> list[dict]:
    """Return JSON-serialisable list of dosage info dicts."""
    dosages = extract_dosages(text)
    return [
        {
            "quantity": d.quantity,
            "unit": d.unit,
            "frequency": d.frequency,
            "frequency_raw": d.frequency_raw,
            "duration": d.duration,
            "route": d.route,
            "raw_text": d.raw_text,
            "confidence": d.confidence,
        }
        for d in dosages
    ]
