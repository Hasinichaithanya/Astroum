"""
Accuracy Metrics — WER, MTA, NA, NEA, Composite Score.

Implements the exact formulas from the assessment spec.
"""

from __future__ import annotations
import re
from typing import Optional


# ── WER ───────────────────────────────────────────────────────────────────────

def compute_wer(reference: str, hypothesis: str) -> float:
    """
    Word Error Rate = (S + I + D) / N × 100
    where S = substitutions, I = insertions, D = deletions, N = reference word count.
    Uses dynamic programming (same as Levenshtein but on word sequences).
    """
    ref_words = reference.lower().split()
    hyp_words = hypothesis.lower().split()

    if not ref_words:
        return 0.0 if not hyp_words else 100.0

    N = len(ref_words)
    M = len(hyp_words)

    # DP table
    dp = [[0] * (M + 1) for _ in range(N + 1)]
    for i in range(N + 1):
        dp[i][0] = i
    for j in range(M + 1):
        dp[0][j] = j

    for i in range(1, N + 1):
        for j in range(1, M + 1):
            if ref_words[i-1] == hyp_words[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(
                    dp[i-1][j],    # deletion
                    dp[i][j-1],    # insertion
                    dp[i-1][j-1],  # substitution
                )

    wer = (dp[N][M] / N) * 100
    return round(wer, 2)


# ── MTA ───────────────────────────────────────────────────────────────────────

def compute_mta(
    hypothesis: str,
    drug_list: list[str],
    brand_map: dict[str, str] | None = None,
) -> tuple[float, int, int]:
    """
    Medical Term Accuracy = Correctly Transcribed / Total × 100.
    
    A term is 'correct' if it appears in the hypothesis (exact, brand, or brand map).
    Returns (mta_percent, correct_count, total_count).
    """
    hyp_lower = hypothesis.lower()
    correct = 0
    brand_map = brand_map or {}

    for drug in drug_list:
        drug_lower = drug.lower()
        # Exact match
        if drug_lower in hyp_lower:
            correct += 1
            continue
        # Check if brand name appears
        brands = brand_map.get(drug, [])
        if any(b.lower() in hyp_lower for b in brands):
            correct += 1
            continue

    total = len(drug_list)
    if total == 0:
        return 100.0, 0, 0
    mta = (correct / total) * 100
    return round(mta, 2), correct, total


# ── NA ────────────────────────────────────────────────────────────────────────

def compute_na(
    expected_negations: list[dict],
    hypothesis: str,
    negation_patterns: dict | None = None,
) -> tuple[float, int, int]:
    """
    Negation Accuracy = Preserved / Total × 100.
    
    A negation is 'preserved' if:
      - The negation trigger appears in hypothesis, OR
      - An English equivalent appears ("do not", "must not", "DO NOT", etc.)
    
    Returns (na_percent, preserved, total).
    """
    if not expected_negations:
        return 100.0, 0, 0

    hyp_lower = hypothesis.lower()
    preserved = 0
    english_negation_markers = [
        "do not", "don't", "must not", "cannot", "can't",
        "stop", "discontinue", "contraindicated", "avoid",
        "hold", "withhold", "never give",
    ]

    for neg in expected_negations:
        trigger = neg.get("trigger", "").lower()
        # Check trigger word present
        if trigger and trigger in hyp_lower:
            preserved += 1
            continue
        # Check English equivalent
        if any(marker in hyp_lower for marker in english_negation_markers):
            # Only count if associated with the right drug/context
            negated_span = neg.get("negated_span", "").lower()
            if negated_span and any(word in hyp_lower for word in negated_span.split()[:3]):
                preserved += 1
                continue
        # Check if node type=CONSTRAINT exists (for node-level evaluation)
        if neg.get("type") == "CONSTRAINT" and "do not" in hyp_lower:
            preserved += 1

    total = len(expected_negations)
    na = (preserved / total) * 100
    return round(na, 2), preserved, total


# ── NEA ───────────────────────────────────────────────────────────────────────

def compute_nea(
    expected_nodes: list[dict],
    extracted_nodes: list[dict],
) -> tuple[float, int, int]:
    """
    Node Extraction Accuracy = Correctly Extracted / Expected × 100.
    
    'Correct' means:
      - type matches (CONSTRAINT/DECISION/FACT/ANTI_PATTERN)
      - core clinical content preserved (key terms overlap >= 40%)
      - negation preserved (if expected node is CONSTRAINT, extracted must also be CONSTRAINT)
    
    Returns (nea_percent, correct, total).
    """
    if not expected_nodes:
        return 100.0, 0, 0

    def _key_terms(text: str) -> set[str]:
        """Extract meaningful terms (filter stopwords)."""
        stopwords = {"the", "a", "an", "is", "in", "of", "for", "to", "with", "and", "or",
                     "on", "at", "by", "this", "that", "be", "are", "was", "has", "have"}
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        return {w for w in words if w not in stopwords}

    correct = 0

    for expected in expected_nodes:
        exp_type = expected.get("type", "").upper()
        exp_terms = _key_terms(
            expected.get("title", "") + " " + expected.get("content", "")
        )

        best_overlap = 0.0
        best_type_match = False

        for extracted in extracted_nodes:
            ext_type = extracted.get("type", "").upper()
            ext_terms = _key_terms(
                extracted.get("title", "") + " " + extracted.get("content", "")
            )

            # Type match check (CONSTRAINT must match CONSTRAINT)
            type_match = (exp_type == ext_type)

            # Content overlap
            if exp_terms and ext_terms:
                overlap = len(exp_terms & ext_terms) / len(exp_terms | ext_terms)
            else:
                overlap = 0.0

            if overlap > best_overlap:
                best_overlap = overlap
                best_type_match = type_match

        # Criteria:
        # - CONSTRAINT: must have type match AND >= 30% overlap
        # - Others: >= 40% overlap (type can be close)
        if exp_type == "CONSTRAINT":
            if best_type_match and best_overlap >= 0.30:
                correct += 1
        else:
            if best_overlap >= 0.40:
                correct += 1

    total = len(expected_nodes)
    nea = (correct / total) * 100
    return round(nea, 2), correct, total


# ── Composite Score ───────────────────────────────────────────────────────────

def compute_composite_score(
    wer: float,
    mta: float,
    na: float,
    nea: float,
    safety: float,
) -> float:
    """
    Composite = (WER_inverted × 0.20) + (MTA × 0.25) + (NA × 0.25) + (NEA × 0.20) + (Safety × 0.10)
    WER_inverted = max(0, 100 - WER)
    Safety = 100 if no dangerous errors, 0 if negation-flip or wrong drug name
    """
    wer_inv = max(0.0, 100.0 - wer)
    score = (
        wer_inv * 0.20 +
        mta * 0.25 +
        na * 0.25 +
        nea * 0.20 +
        safety * 0.10
    )
    return round(score, 2)


# ── Full note evaluation ──────────────────────────────────────────────────────

def evaluate_note(
    raw_transcript: str,
    corrected_transcript: str,
    ground_truth: str,
    expected_nodes: list[dict],
    extracted_nodes: list[dict],
    expected_negations: list[dict] | None = None,
    drug_list: list[str] | None = None,
    has_dangerous_error: bool = False,
) -> dict:
    """Full evaluation for a single voice note."""
    from ..intelligence.medical_dictionary import get_drug_names

    drug_list = drug_list or get_drug_names()
    expected_negations = expected_negations or []

    # WER on corrected vs ground truth
    wer_raw = compute_wer(ground_truth, raw_transcript)
    wer_corrected = compute_wer(ground_truth, corrected_transcript)

    # MTA on corrected transcript
    mta, mta_correct, mta_total = compute_mta(corrected_transcript, drug_list)

    # NA
    na, na_preserved, na_total = compute_na(expected_negations, corrected_transcript)

    # NEA
    nea, nea_correct, nea_total = compute_nea(expected_nodes, extracted_nodes)

    # Safety
    safety = 0.0 if has_dangerous_error else 100.0

    # Composite
    composite = compute_composite_score(wer_corrected, mta, na, nea, safety)

    return {
        "wer_raw": wer_raw,
        "wer_corrected": wer_corrected,
        "wer_improvement": round(wer_raw - wer_corrected, 2),
        "mta": mta,
        "mta_correct": mta_correct,
        "mta_total": mta_total,
        "na": na,
        "na_preserved": na_preserved,
        "na_total": na_total,
        "nea": nea,
        "nea_correct": nea_correct,
        "nea_total": nea_total,
        "safety": safety,
        "composite_score": composite,
    }
