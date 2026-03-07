"""Voice service for text-to-speech and speech-to-text conversion.

This module provides voice interface capabilities with:
- Confidence checking for STT results
- Concise response generation
- Language detection
- Error handling
"""

from __future__ import annotations

import base64
import logging
import os
import re
from typing import Any

import httpx

from bracc.config import settings

logger = logging.getLogger(__name__)

# Voice service configuration from environment
TTS_MAX_LENGTH = int(os.environ.get("BRACC_TTS_MAX_LENGTH", "2000"))
STT_MIN_CONFIDENCE = float(os.environ.get("BRACC_STT_MIN_CONFIDENCE", "0.6"))
VOICE_LANGUAGE_DETECTION = os.environ.get("BRACC_VOICE_LANG_DETECTION", "true").lower() == "true"


class VoiceServiceError(Exception):
    """Base exception for voice service errors."""

    pass


class ConfidenceTooLowError(VoiceServiceError):
    """Raised when STT confidence is below threshold."""

    pass


class ConfigurationError(VoiceServiceError):
    """Raised when voice service is not properly configured."""

    pass


def _detect_language(text: str) -> str:
    """Detect the primary language of text using simple heuristics.

    This is a lightweight language detection that checks for common
    Portuguese and English patterns. For production, consider using
    a dedicated library like langdetect.

    Args:
        text: Text to analyze.

    Returns:
        Language code ("pt" or "en").
    """
    if not text:
        return "pt"

    text_lower = text.lower()

    # Portuguese indicators
    pt_indicators = [
        " e ", " o ", " a ", " os ", " as ", " de ", " da ", " do ",
        " em ", " para ", " com ", " um ", " uma ", " não ", " sim ",
        "ção", "mente", "ismo", "ista", "ente", "ável", "ível",
    ]

    # English indicators
    en_indicators = [
        " the ", " a ", " an ", " and ", " or ", " but ", " in ",
        " on ", " at ", " to ", " for ", " with ", " of ", " from ",
        "ing ", "ed ", "tion", "ness", "ment",
    ]

    pt_score = sum(1 for ind in pt_indicators if ind in text_lower)
    en_score = sum(1 for ind in en_indicators if ind in text_lower)

    return "pt" if pt_score >= en_score else "en"


def _make_concise(text: str, max_length: int = TTS_MAX_LENGTH) -> str:
    """Make text concise for voice output.

    Truncates text to max_length while preserving complete sentences.
    Prioritizes the first sentences which usually contain key information.

    Args:
        text: Original text.
        max_length: Maximum length for output.

    Returns:
        Concise version of text.
    """
    if len(text) <= max_length:
        return text

    # Try to break at sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)
    concise = ""

    for sentence in sentences:
        if len(concise) + len(sentence) + 1 > max_length:
            break
        concise += sentence + " "

    result = concise.strip()

    # If still too long (no sentence breaks), truncate with ellipsis
    if len(result) > max_length:
        result = text[: max_length - 3].rsplit(" ", 1)[0] + "..."

    return result


async def text_to_speech(
    text: str,
    voice: str = "alloy",
    speed: float = 1.0,
    format: str = "mp3",
) -> tuple[str, float]:
    """Convert text to speech using OpenAI's TTS API.

    Args:
        text: Text to convert (max 5000 chars).
        voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer).
        speed: Speech speed multiplier (0.25 to 4.0).
        format: Output format (mp3, opus, aac, flac).

    Returns:
        Tuple of (base64-encoded audio, duration in seconds).

    Raises:
        ConfigurationError: If API key not configured.
        VoiceServiceError: If TTS request fails.
    """
    api_key = settings.ai_provider_api_key
    if not api_key:
        raise ConfigurationError("AI_PROVIDER_API_KEY not configured")

    # Make text concise for better audio experience
    concise_text = _make_concise(text[:5000])

    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "tts-1",
        "input": concise_text,
        "voice": voice,
        "speed": speed,
        "response_format": format,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            audio_bytes = response.content
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

            # Estimate duration based on audio size and format
            # These are rough estimates
            bytes_per_second = {
                "mp3": 16000,
                "opus": 12000,
                "aac": 18000,
                "flac": 88000,
            }.get(format, 16000)

            duration = len(audio_bytes) / bytes_per_second

            return audio_base64, round(duration, 2)

    except httpx.HTTPStatusError as e:
        logger.error("TTS HTTP error: %s", e)
        raise VoiceServiceError(f"TTS request failed: {e.response.status_code}") from e
    except Exception as e:
        logger.exception("TTS error")
        raise VoiceServiceError(f"TTS failed: {str(e)}") from e


async def speech_to_text(
    audio_base64: str,
    language: str = "pt",
) -> tuple[str, float]:
    """Convert speech to text using OpenAI's Whisper API.

    Args:
        audio_base64: Base64-encoded audio data.
        language: Expected language code (pt, en, etc.).

    Returns:
        Tuple of (transcribed text, confidence score).

    Raises:
        ConfigurationError: If API key not configured.
        ConfidenceTooLowError: If confidence is below threshold.
        VoiceServiceError: If STT request fails.
    """
    api_key = settings.ai_provider_api_key
    if not api_key:
        raise ConfigurationError("AI_PROVIDER_API_KEY not configured")

    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    try:
        audio_bytes = base64.b64decode(audio_base64)
    except Exception as e:
        raise VoiceServiceError("Invalid audio_base64 encoding") from e

    files: dict[str, tuple[str | None, bytes | str]] = {
        "file": ("audio.mp3", audio_bytes),
        "model": (None, "whisper-1"),
        "language": (None, language),
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, files=files)
            response.raise_for_status()
            result = response.json()

            text = result.get("text", "").strip()

            # Whisper doesn't return confidence directly, so we estimate
            # based on text characteristics and presence of uncertain markers
            confidence = _estimate_confidence(text)

            # Check confidence threshold
            if confidence < STT_MIN_CONFIDENCE:
                raise ConfidenceTooLowError(
                    f"STT confidence {confidence:.2f} below threshold {STT_MIN_CONFIDENCE}"
                )

            return text, confidence

    except ConfidenceTooLowError:
        raise
    except httpx.HTTPStatusError as e:
        logger.error("STT HTTP error: %s", e)
        raise VoiceServiceError(f"STT request failed: {e.response.status_code}") from e
    except Exception as e:
        logger.exception("STT error")
        raise VoiceServiceError(f"STT failed: {str(e)}") from e


def _estimate_confidence(text: str) -> float:
    """Estimate confidence level of transcribed text.

    Whisper doesn't provide confidence scores, so we use heuristics:
    - Presence of uncertain markers ("um", "uh", repetitive words)
    - Text length (too short may be incomplete)
    - Presence of coherent sentence structure

    Args:
        text: Transcribed text.

    Returns:
        Estimated confidence (0.0 to 1.0).
    """
    if not text:
        return 0.0

    base_confidence = 0.85  # Whisper is generally accurate

    # Reduce confidence for uncertain markers
    uncertain_markers = ["um ", "uh ", "er ", "...", "[", "](", "?", "*"]
    for marker in uncertain_markers:
        if marker in text.lower():
            base_confidence -= 0.05

    # Reduce for very short text
    word_count = len(text.split())
    if word_count < 3:
        base_confidence -= 0.1

    # Boost for longer, well-formed text
    if word_count > 10 and any(c in text for c in ".!?"):
        base_confidence += 0.05

    return max(0.0, min(1.0, base_confidence))


async def generate_summary_audio(
    text: str,
    voice: str = "alloy",
    lang: str | None = None,
) -> tuple[str, float, str]:
    """Generate audio summary of investigation findings.

    Creates a concise audio summary suitable for voice playback.

    Args:
        text: Full investigation text.
        voice: Voice to use.
        lang: Optional language override (auto-detected if None).

    Returns:
        Tuple of (base64 audio, duration, detected_language).
    """
    # Detect language if not provided
    detected_lang = lang or _detect_language(text)

    # Create concise summary
    max_length = TTS_MAX_LENGTH
    if len(text) > max_length:
        summary = _create_summary(text, max_length, detected_lang)
    else:
        summary = text

    # Ensure summary is concise
    concise_summary = _make_concise(summary, max_length)

    audio_base64, duration = await text_to_speech(concise_summary, voice=voice)

    return audio_base64, duration, detected_lang


def _create_summary(text: str, max_length: int, lang: str) -> str:
    """Create a summary from longer text.

    Args:
        text: Original text.
        max_length: Maximum summary length.
        lang: Language for summary.

    Returns:
        Summary text.
    """
    if lang == "pt":
        intro = "Resumo da análise: "
    else:
        intro = "Analysis summary: "

    # Take first portion of text, breaking at sentence end
    available_length = max_length - len(intro)
    text_to_summarize = text[:available_length]

    # Find last sentence boundary
    for punct in ".!?":
        if punct in text_to_summarize:
            last_idx = text_to_summarize.rindex(punct)
            if last_idx > len(text_to_summarize) * 0.5:  # At least half used
                return intro + text_to_summarize[: last_idx + 1]

    return intro + text_to_summarize + "..."


async def transcribe_with_fallback(
    audio_base64: str,
    primary_lang: str = "pt",
    fallback_lang: str = "en",
) -> dict[str, Any]:
    """Transcribe audio with language fallback.

    Attempts transcription in primary language, falls back to secondary
    if confidence is low.

    Args:
        audio_base64: Base64-encoded audio.
        primary_lang: Primary language to try.
        fallback_lang: Fallback language if primary fails.

    Returns:
        Dictionary with text, confidence, and language used.
    """
    try:
        text, confidence = await speech_to_text(audio_base64, primary_lang)
        return {
            "text": text,
            "confidence": confidence,
            "language": primary_lang,
            "fallback_used": False,
        }
    except ConfidenceTooLowError:
        logger.info("Primary language %s confidence low, trying %s", primary_lang, fallback_lang)
        try:
            text, confidence = await speech_to_text(audio_base64, fallback_lang)
            return {
                "text": text,
                "confidence": confidence,
                "language": fallback_lang,
                "fallback_used": True,
            }
        except ConfidenceTooLowError as e:
            logger.warning("Both languages failed confidence check")
            raise e
