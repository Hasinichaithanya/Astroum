"""
Medical Intelligence Pipeline — orchestrator.

Runs the full intelligence stack on a raw ASR transcript:
  1. PHI strip (before any external call)
  2. Drug name correction (phonetic + Levenshtein)
  3. Negation detection
  4. Dosage extraction
  5. Assemble corrected transcript with metadata

All processing is local — no external API calls in this layer.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any

from .medical_dictionary import correct_transcript, Correction
from .negation_detector import detect_negations, NegationEvent, negation_summary
from .dosage_extractor import extract_dosages, DosageInfo, dosage_summary
from .phi_stripper import strip_phi, PHIMatch, phi_summary


@dataclass
class PipelineResult:
    raw_transcript: str
    phi_redacted_transcript: str
    corrected_transcript: str
    corrections: list[Correction]
    negations: list[NegationEvent]
    dosages: list[DosageInfo]
    phi_items: list[PHIMatch]
    has_critical_negation: bool
    processing_ms: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "raw_transcript": self.raw_transcript,
            "corrected_transcript": self.corrected_transcript,
            "phi_redacted_transcript": self.phi_redacted_transcript,
            "corrections_applied": [
                {
                    "original": c.original,
                    "corrected": c.corrected,
                    "term_type": c.term_type,
                    "method": c.method,
                    "confidence": c.confidence,
                }
                for c in self.corrections
            ],
            "negations": [
                {
                    "trigger": n.trigger,
                    "language": n.language,
                    "meaning": n.meaning,
                    "negated_span": n.negated_span,
                    "severity": n.severity,
                    "position": n.position,
                }
                for n in self.negations
            ],
            "dosages": [
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
                for d in self.dosages
            ],
            "phi_items": [
                {"type": p.phi_type, "original": p.original, "replacement": p.replacement}
                for p in self.phi_items
            ],
            "has_critical_negation": self.has_critical_negation,
            "processing_ms": self.processing_ms,
            "metadata": self.metadata,
        }


def run_pipeline(
    raw_transcript: str,
    language_code: str | None = None,
    redact_names: bool = True,
) -> PipelineResult:
    """
    Full medical intelligence pipeline.

    Args:
        raw_transcript: Raw text from ASR
        language_code: ISO code hint (te|hi|ta|kn|ml|mr|bn|gu) or None for auto-detect
        redact_names: Whether to redact patient names

    Returns:
        PipelineResult with all enrichments
    """
    start = time.time()

    # Step 1: PHI redaction (before any external processing)
    phi_redacted, phi_items = strip_phi(raw_transcript, redact_names=redact_names)

    # Step 2: Drug name correction on PHI-redacted text
    corrected, corrections = correct_transcript(phi_redacted)

    # Step 3: Negation detection
    lang_hints = [language_code] if language_code else None
    negations = detect_negations(corrected, languages=lang_hints)

    # Step 4: Dosage extraction
    dosages = extract_dosages(corrected)

    # Step 5: Safety flag
    has_critical = any(n.severity == "CRITICAL" for n in negations)

    elapsed_ms = int((time.time() - start) * 1000)

    return PipelineResult(
        raw_transcript=raw_transcript,
        phi_redacted_transcript=phi_redacted,
        corrected_transcript=corrected,
        corrections=corrections,
        negations=negations,
        dosages=dosages,
        phi_items=phi_items,
        has_critical_negation=has_critical,
        processing_ms=elapsed_ms,
        metadata={
            "language_hint": language_code,
            "correction_count": len(corrections),
            "negation_count": len(negations),
            "dosage_count": len(dosages),
            "phi_count": len(phi_items),
        },
    )


def quick_stats(raw: str) -> dict:
    """Lightweight stats without full pipeline (for UI preview)."""
    _, corrections = correct_transcript(raw)
    negations = detect_negations(raw)
    return {
        "corrections": len(corrections),
        "negations": len(negations),
        "critical_negations": sum(1 for n in negations if n.severity == "CRITICAL"),
        "has_drug_names": len(corrections) > 0,
    }
