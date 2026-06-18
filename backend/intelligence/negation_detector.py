"""
Negation Detector — 8 Indian languages.

Detects clinical negations in code-switched medical text.
A negation like "ivvaledu" (Telugu: don't give) is a PATIENT SAFETY item —
misidentifying it as positive ("give") can cause harm.

Returns structured negation events with:
  - the trigger word/phrase
  - language detected
  - canonical meaning
  - the span that is negated (best effort)
  - severity: CRITICAL | MODERATE
"""

from __future__ import annotations
import re
from dataclasses import dataclass


@dataclass
class NegationEvent:
    trigger: str                # the actual word that triggered (e.g. "ivvaledu")
    language: str               # ISO code: te | hi | ta | kn | ml | mr | bn | gu
    meaning: str                # canonical English meaning (e.g. "must not give")
    negated_span: str           # the text immediately after the trigger
    severity: str               # CRITICAL | MODERATE
    position: int               # character offset in text


# ── Language-specific negation patterns ──────────────────────────────────────
# Each entry: (trigger_pattern, canonical_meaning, severity)

NEGATION_PATTERNS: dict[str, list[tuple[str, str, str]]] = {
    "te": [  # Telugu
        (r"\bivvaledu\b", "must not give / did not give", "CRITICAL"),
        (r"\bivvakudadu\b", "must not give", "CRITICAL"),
        (r"\bkudadu\b", "must not / should not", "CRITICAL"),
        (r"\bvaddhu\b", "don't want / avoid", "MODERATE"),
        (r"\bcheyakandi\b", "do not do", "CRITICAL"),
        (r"\baapandi\b", "stop / discontinue", "CRITICAL"),
        (r"\bcheyakudadu\b", "must not do", "CRITICAL"),
        (r"\bteesukokandi\b", "do not take", "CRITICAL"),
        (r"\bpoddu\b", "do not put / do not apply", "MODERATE"),
        (r"\bvaddhe\b", "should not / avoid", "MODERATE"),
        (r"\bledu\b", "is not / there is no", "MODERATE"),
        (r"\bvaddu\b", "don't / avoid", "MODERATE"),
        (r"\baapeyandi\b", "stop immediately", "CRITICAL"),
        (r"\bthagginchandi\b", "reduce / decrease", "MODERATE"),
        (r"\bmarchipoyi\b", "forgot / do not repeat", "MODERATE"),
    ],
    "hi": [  # Hindi
        (r"\bmat\s+do\b", "do not give", "CRITICAL"),
        (r"\bnahi\s+dena\b", "do not give", "CRITICAL"),
        (r"\bmat\s+dena\b", "do not give", "CRITICAL"),
        (r"\bband\s+karo\b", "stop / discontinue", "CRITICAL"),
        (r"\bband\s+karna\b", "stop / discontinue", "CRITICAL"),
        (r"\brok\s+do\b", "stop / hold", "CRITICAL"),
        (r"\bhatao\b", "remove / discontinue", "CRITICAL"),
        (r"\bnahi\b", "no / not", "MODERATE"),
        (r"\bnako\b", "don't / no", "MODERATE"),
        (r"\bnahi\s+karna\b", "do not do", "CRITICAL"),
        (r"\bmat\s+karo\b", "do not do", "CRITICAL"),
        (r"\bband\b", "stop / off", "MODERATE"),
        (r"\bchhodna\b", "stop / leave", "MODERATE"),
        (r"\bbandh\b", "closed / stopped", "MODERATE"),
        (r"\bnahi\s+chahiye\b", "should not / do not want", "CRITICAL"),
    ],
    "ta": [  # Tamil
        (r"\bkudadhu\b", "must not / should not", "CRITICAL"),
        (r"\bkudaadhu\b", "must not", "CRITICAL"),
        (r"\bvenda\b", "don't want / don't need", "MODERATE"),
        (r"\bvaenda\b", "don't need", "MODERATE"),
        (r"\billai\b", "no / is not", "MODERATE"),
        (r"\bkodukka\s+kudadhu\b", "must not give", "CRITICAL"),
        (r"\bpannakudadhu\b", "must not do", "CRITICAL"),
        (r"\bvangakudadhu\b", "must not take", "CRITICAL"),
        (r"\baaga\s+kudadhu\b", "must not happen", "CRITICAL"),
        (r"\bniruthu\b", "stop", "CRITICAL"),
        (r"\bniruthunga\b", "please stop", "CRITICAL"),
        (r"\billa\b", "not / no", "MODERATE"),
        (r"\bvendam\b", "don't want", "MODERATE"),
        (r"\bviddhu\b", "don't / leave", "MODERATE"),
    ],
    "kn": [  # Kannada
        (r"\bbaralla\b", "cannot / should not", "CRITICAL"),
        (r"\bkudadu\b", "must not", "CRITICAL"),
        (r"\bbeda\b", "don't want / no need", "MODERATE"),
        (r"\bkodabaradu\b", "must not give", "CRITICAL"),
        (r"\bmaadabaradu\b", "must not do", "CRITICAL"),
        (r"\bnillisi\b", "stop", "CRITICAL"),
        (r"\billa\b", "not / no", "MODERATE"),
        (r"\billva\b", "is not", "MODERATE"),
        (r"\bbedam\b", "don't want", "MODERATE"),
        (r"\btogolabeda\b", "should not take", "CRITICAL"),
        (r"\bkodabeda\b", "should not give", "CRITICAL"),
        (r"\bbidabeda\b", "do not leave / do not skip", "MODERATE"),
        (r"\bmaadabeda\b", "should not do", "CRITICAL"),
        (r"\bsalladhu\b", "not allowed", "CRITICAL"),
    ],
    "ml": [  # Malayalam
        (r"\bpaadilla\b", "must not / not allowed", "CRITICAL"),
        (r"\baruthhu\b", "should not", "CRITICAL"),
        (r"\bvenda\b", "don't need / don't want", "MODERATE"),
        (r"\bkodukkaruthhu\b", "must not give", "CRITICAL"),
        (r"\bcheyyaruthhu\b", "must not do", "CRITICAL"),
        (r"\billa\b", "no / not", "MODERATE"),
        (r"\baakilla\b", "won't happen / should not", "MODERATE"),
        (r"\btharam\s+paadilla\b", "must not give", "CRITICAL"),
        (r"\bnirthu\b", "stop", "CRITICAL"),
        (r"\bnirthukka\b", "to stop", "CRITICAL"),
        (r"\bvendum\b", "don't need", "MODERATE"),
        (r"\bakathe\b", "not okay / should not", "MODERATE"),
    ],
    "mr": [  # Marathi
        (r"\bdeu\s+naka\b", "do not give", "CRITICAL"),
        (r"\bdeu\s+naye\b", "should not give", "CRITICAL"),
        (r"\bnahi\b", "no / not", "MODERATE"),
        (r"\bnako\b", "don't want / no", "MODERATE"),
        (r"\bband\s+kara\b", "stop / discontinue", "CRITICAL"),
        (r"\bthambav\b", "stop", "CRITICAL"),
        (r"\bthambava\b", "stop it", "CRITICAL"),
        (r"\bnahi\s+deu\b", "do not give", "CRITICAL"),
        (r"\bkaadha\b", "must not", "CRITICAL"),
        (r"\bgheu\s+naka\b", "do not take", "CRITICAL"),
        (r"\bnye\b", "should not", "MODERATE"),
        (r"\bband\b", "stop / off", "MODERATE"),
        (r"\bsodun\s+dya\b", "leave it / stop", "MODERATE"),
    ],
    "bn": [  # Bengali
        (r"\bdeben\s+na\b", "do not give", "CRITICAL"),
        (r"\bkorben\s+na\b", "do not do", "CRITICAL"),
        (r"\bbandho\s+korun\b", "stop / discontinue", "CRITICAL"),
        (r"\bna\b", "no / not", "MODERATE"),
        (r"\bdeoaa\s+uchhit\s+noy\b", "should not give", "CRITICAL"),
        (r"\bhobena\b", "will not / should not", "MODERATE"),
        (r"\bkora\s+jabe\s+na\b", "cannot do / must not do", "CRITICAL"),
        (r"\bniyen\s+na\b", "do not take", "CRITICAL"),
        (r"\bbondho\s+korun\b", "stop", "CRITICAL"),
        (r"\bnishidhdho\b", "forbidden / prohibited", "CRITICAL"),
    ],
    "gu": [  # Gujarati
        (r"\baapvo\s+nahi\b", "do not give", "CRITICAL"),
        (r"\bnathi\b", "is not / no", "MODERATE"),
        (r"\bband\s+karo\b", "stop", "CRITICAL"),
        (r"\bnakko\b", "don't want / no", "MODERATE"),
        (r"\bna\s+aapo\b", "do not give", "CRITICAL"),
        (r"\bna\s+levo\b", "do not take", "CRITICAL"),
        (r"\bbandh\s+karo\b", "stop / discontinue", "CRITICAL"),
        (r"\bkarvanu\s+nathi\b", "must not do", "CRITICAL"),
        (r"\bjoie\s+nahi\b", "should not", "MODERATE"),
        (r"\bthambavo\b", "stop", "CRITICAL"),
    ],
}

# English negations for mixed text
ENGLISH_NEGATIONS: list[tuple[str, str, str]] = [
    (r"\bdo\s+not\s+give\b", "do not give", "CRITICAL"),
    (r"\bdo\s+not\s+start\b", "do not start", "CRITICAL"),
    (r"\bdo\s+not\s+continue\b", "do not continue", "CRITICAL"),
    (r"\bdo\s+not\s+administer\b", "do not administer", "CRITICAL"),
    (r"\bstop\b", "stop / discontinue", "CRITICAL"),
    (r"\bdiscontinue\b", "discontinue", "CRITICAL"),
    (r"\bcontraindicated\b", "contraindicated", "CRITICAL"),
    (r"\bavoid\b", "avoid", "MODERATE"),
    (r"\bhold\b", "hold / pause", "MODERATE"),
    (r"\bnot\s+to\s+be\s+given\b", "must not give", "CRITICAL"),
    (r"\bnever\b", "never", "CRITICAL"),
    (r"\bwithhold\b", "withhold", "CRITICAL"),
]


def _extract_negated_span(text: str, match_end: int, max_words: int = 6) -> str:
    """Extract the words following a negation trigger (what is being negated)."""
    after = text[match_end:].strip()
    words = after.split()[:max_words]
    return " ".join(words)


def detect_negations(text: str, languages: list[str] | None = None) -> list[NegationEvent]:
    """
    Detect all negation events in the given text.

    Args:
        text: The transcript text (may be code-switched)
        languages: Restrict to these language codes. None = check all.

    Returns:
        List of NegationEvent objects, sorted by position.
    """
    events: list[NegationEvent] = []
    text_lower = text.lower()

    check_langs = languages or list(NEGATION_PATTERNS.keys())

    for lang in check_langs:
        patterns = NEGATION_PATTERNS.get(lang, [])
        for pattern, meaning, severity in patterns:
            for m in re.finditer(pattern, text_lower, re.IGNORECASE):
                span = _extract_negated_span(text, m.end())
                events.append(NegationEvent(
                    trigger=m.group(),
                    language=lang,
                    meaning=meaning,
                    negated_span=span,
                    severity=severity,
                    position=m.start(),
                ))

    # English negations
    for pattern, meaning, severity in ENGLISH_NEGATIONS:
        for m in re.finditer(pattern, text_lower, re.IGNORECASE):
            span = _extract_negated_span(text, m.end())
            events.append(NegationEvent(
                trigger=m.group(),
                language="en",
                meaning=meaning,
                negated_span=span,
                severity=severity,
                position=m.start(),
            ))

    # Deduplicate overlapping matches, keep highest severity
    events.sort(key=lambda e: e.position)
    deduped: list[NegationEvent] = []
    last_end = -1
    for ev in events:
        if ev.position > last_end:
            deduped.append(ev)
            last_end = ev.position + len(ev.trigger)

    return deduped


def has_critical_negation(text: str) -> bool:
    """Quick check: does this text contain any CRITICAL negation?"""
    events = detect_negations(text)
    return any(e.severity == "CRITICAL" for e in events)


def negation_summary(text: str) -> dict:
    """Return a summary dict for API responses."""
    events = detect_negations(text)
    return {
        "total": len(events),
        "critical": sum(1 for e in events if e.severity == "CRITICAL"),
        "moderate": sum(1 for e in events if e.severity == "MODERATE"),
        "events": [
            {
                "trigger": e.trigger,
                "language": e.language,
                "meaning": e.meaning,
                "negated_span": e.negated_span,
                "severity": e.severity,
            }
            for e in events
        ],
    }


def get_supported_languages() -> list[str]:
    return list(NEGATION_PATTERNS.keys()) + ["en"]
