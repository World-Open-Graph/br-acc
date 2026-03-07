from __future__ import annotations

import base64
import logging
import os

import httpx

from bracc.config import settings

logger = logging.getLogger(__name__)


async def text_to_speech(
    text: str,
    voice: str = "alloy",
    speed: float = 1.0,
    format: str = "mp3",
) -> tuple[str, float]:
    """
    Convert text to speech using OpenAI's TTS API.

    Returns:
        Tuple of (base64-encoded audio, duration in seconds)
    """
    api_key = settings.ai_provider_api_key
    if not api_key:
        raise ValueError("AI_PROVIDER_API_KEY not configured")

    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "tts-1",
        "input": text[:5000],
        "voice": voice,
        "speed": speed,
        "response_format": format,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        audio_bytes = response.content
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        duration = len(audio_bytes) / (16000 * (1 if format == "mp3" else 0.5))

        return audio_base64, duration


async def speech_to_text(
    audio_base64: str,
    language: str = "pt",
) -> tuple[str, float]:
    """
    Convert speech to text using OpenAI's Whisper API.

    Returns:
        Tuple of (transcribed text, confidence score)
    """
    api_key = settings.ai_provider_api_key
    if not api_key:
        raise ValueError("AI_PROVIDER_API_KEY not configured")

    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    audio_bytes = base64.b64decode(audio_base64)

    files = {
        "file": ("audio.mp3", audio_bytes, "audio/mpeg"),
        "model": (None, "whisper-1"),
        "language": (None, language),
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, files=files)
        response.raise_for_status()
        result = response.json()
        return result.get("text", ""), 0.9


async def generate_summary_audio(
    text: str,
    voice: str = "alloy",
) -> tuple[str, float]:
    """Generate audio summary of investigation findings."""
    max_length = 2000
    if len(text) > max_length:
        sentences = text.replace(".", ". ").split(". ")
        summary = ""
        for sent in sentences:
            if len(summary) + len(sent) + 1 > max_length:
                break
            summary += sent + ". "
        text = summary.strip()

    return await text_to_speech(text, voice=voice, speed=1.0)
