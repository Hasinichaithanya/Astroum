"""
Whisper ASR Provider — uses faster-whisper for local, CPU-friendly inference.

Why faster-whisper over openai-whisper:
  - 4x faster on CPU via CTranslate2 backend
  - Lower memory footprint
  - Supports int8 quantisation (fast on CPU)
  - Word-level timestamps + per-segment language detection

Model selection:
  - tiny:   Fastest, lowest accuracy (not recommended for clinical)
  - base:   Good speed/accuracy balance for CPU demo (our default)
  - small:  Better accuracy, 2x slower than base
  - medium: Near large quality, moderate speed
  - large-v3: Best accuracy, GPU recommended
"""

from __future__ import annotations
import os
import time
import tempfile
from dataclasses import dataclass
from typing import Optional, Any
from pathlib import Path


@dataclass
class ASRSegment:
    start: float
    end: float
    text: str
    language: str
    avg_logprob: float      # confidence proxy (higher = more confident)
    no_speech_prob: float   # probability that segment has no speech


@dataclass
class ASRResult:
    transcript: str
    segments: list[ASRSegment]
    detected_language: str
    duration_seconds: float
    processing_seconds: float
    provider: str = "faster-whisper"
    model: str = "base"
    overall_confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "transcript": self.transcript,
            "detected_language": self.detected_language,
            "duration_seconds": self.duration_seconds,
            "processing_seconds": self.processing_seconds,
            "provider": self.provider,
            "model": self.model,
            "overall_confidence": self.overall_confidence,
            "segments": [
                {
                    "start": s.start,
                    "end": s.end,
                    "text": s.text,
                    "language": s.language,
                    "confidence": max(0.0, min(1.0, s.avg_logprob + 1.0)),  # normalise
                }
                for s in self.segments
            ],
        }


class WhisperProvider:
    """
    Wrapper around faster-whisper.

    Initialised lazily (first use) to avoid slow startup.
    Thread-safe for single-worker use.
    """

    def __init__(
        self,
        model_size: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
    ):
        self.model_size = model_size or os.getenv("ASR_WHISPER_MODEL", "base")
        self.device = device or os.getenv("ASR_WHISPER_DEVICE", "cpu")
        self.compute_type = compute_type or os.getenv("ASR_WHISPER_COMPUTE_TYPE", "int8")
        self._model = None

    def _load_model(self):
        """Lazy-load the Whisper model."""
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel
            print(f"[Whisper] Loading model '{self.model_size}' on {self.device} ({self.compute_type})...")
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            print(f"[Whisper] Model loaded.")
        except ImportError:
            raise RuntimeError(
                "faster-whisper not installed. Run: pip install faster-whisper"
            )

    def transcribe_audio(
        self,
        audio_path: str,
        language: str | None = None,
        task: str = "transcribe",
    ) -> ASRResult:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to audio file (wav, mp3, m4a, etc.)
            language: ISO code hint (e.g. "hi", "te"). None = auto-detect.
            task: "transcribe" | "translate" (translate to English)

        Returns:
            ASRResult with full transcript and segment breakdown.
        """
        self._load_model()

        start_time = time.time()

        # faster-whisper returns a generator — collect all segments
        segments_gen, info = self._model.transcribe(
            audio_path,
            language=language,  # None = auto-detect per segment
            task=task,
            beam_size=5,
            vad_filter=True,       # Voice Activity Detection — skip silence
            vad_parameters={"min_silence_duration_ms": 500},
            word_timestamps=False,  # True = slower but per-word confidence
        )

        segments = []
        transcript_parts = []
        total_logprob = 0.0

        for seg in segments_gen:
            asr_seg = ASRSegment(
                start=seg.start,
                end=seg.end,
                text=seg.text.strip(),
                language=getattr(seg, "language", info.language) or info.language,
                avg_logprob=seg.avg_logprob,
                no_speech_prob=seg.no_speech_prob,
            )
            if seg.no_speech_prob < 0.6:  # Filter likely-silent segments
                segments.append(asr_seg)
                transcript_parts.append(seg.text.strip())
                total_logprob += seg.avg_logprob

        full_transcript = " ".join(transcript_parts).strip()
        avg_confidence = max(0.0, min(1.0, (total_logprob / max(len(segments), 1)) + 1.0))
        processing_time = time.time() - start_time

        return ASRResult(
            transcript=full_transcript,
            segments=segments,
            detected_language=info.language,
            duration_seconds=info.duration or 0.0,
            processing_seconds=processing_time,
            provider="faster-whisper",
            model=self.model_size,
            overall_confidence=round(avg_confidence, 3),
        )

    def transcribe_bytes(self, audio_bytes: bytes, suffix: str = ".wav", **kwargs) -> ASRResult:
        """Transcribe raw audio bytes (e.g. from HTTP upload)."""
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            return self.transcribe_audio(tmp_path, **kwargs)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def transcribe_text_mock(self, text: str, language: str = "te") -> ASRResult:
        """
        Mock transcription for testing with pre-written voice notes.
        Simulates ASR output with intentional garbling for realism.

        Use this when you have text test cases (not audio files).
        """
        return ASRResult(
            transcript=text,
            segments=[ASRSegment(
                start=0.0,
                end=30.0,
                text=text,
                language=language,
                avg_logprob=-0.3,
                no_speech_prob=0.02,
            )],
            detected_language=language,
            duration_seconds=30.0,
            processing_seconds=0.001,
            provider="mock",
            model="text_input",
            overall_confidence=0.85,
        )

    @property
    def is_loaded(self) -> bool:
        return self._model is not None


# Singleton instance
_whisper: WhisperProvider | None = None


def get_whisper() -> WhisperProvider:
    global _whisper
    if _whisper is None:
        _whisper = WhisperProvider()
    return _whisper
