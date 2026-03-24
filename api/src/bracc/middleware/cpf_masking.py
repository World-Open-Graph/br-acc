"""Middleware that masks CPF numbers in API responses to protect personal data.

CPF (Cadastro de Pessoa Fisica) is an 11-digit Brazilian tax ID.
Politically Exposed Persons (PEPs) have their CPFs kept visible.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, StreamingResponse

from bracc.constants import PEP_ROLES

if TYPE_CHECKING:
    from starlette.middleware.base import RequestResponseEndpoint
    from starlette.requests import Request

# Matches 11-digit CPF in formatted (123.456.789-00) or raw (12345678900) form.
# Uses negative lookbehind/lookahead to avoid matching inside longer digit sequences
# (e.g. 14-digit CNPJ).
_CPF_FORMATTED = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
_CPF_RAW = re.compile(r"(?<!\d)\d{11}(?!\d)")


def mask_formatted_cpf(cpf: str) -> str:
    """Mask a formatted CPF, keeping only the last 4 visible digits.

    Example: 123.456.789-00 -> ***.***.789-00
    """
    return f"***.***.{cpf[8:]}"


def mask_raw_cpf(cpf: str) -> str:
    """Mask a raw 11-digit CPF, keeping only the last 4 digits.

    Example: 12345678900 -> *******8900
    """
    return f"*******{cpf[7:]}"


def _is_pep_record(record: dict[str, Any]) -> bool:
    """Determine whether a JSON record describes a PEP.

    Checks for explicit ``is_pep`` boolean or political keywords in the
    ``role`` / ``cargo`` fields.
    """
    if record.get("is_pep") is True:
        return True

    for field in ("role", "cargo"):
        value = record.get(field)
        if isinstance(value, str) and any(kw in value.strip().lower() for kw in PEP_ROLES):
            return True

    return False


def _collect_pep_cpfs(data: Any) -> set[str]:
    """Walk a JSON structure and return the set of CPF strings belonging to PEPs."""
    pep_cpfs: set[str] = set()

    if isinstance(data, dict):
        if _is_pep_record(data):
            cpf_val = data.get("cpf")
            if isinstance(cpf_val, str) and cpf_val:
                # Normalise to digits-only for comparison.
                pep_cpfs.add(re.sub(r"\D", "", cpf_val))
        for value in data.values():
            pep_cpfs |= _collect_pep_cpfs(value)
    elif isinstance(data, list):
        for item in data:
            pep_cpfs |= _collect_pep_cpfs(item)

    return pep_cpfs


def _digits_only(cpf: str) -> str:
    return re.sub(r"\D", "", cpf)


def mask_cpfs_in_json(text: str, pep_cpfs: set[str] | None = None) -> str:
    """Replace CPF patterns in *text* with masked versions.

    CPFs whose digits-only form appears in *pep_cpfs* are left untouched.
    CNPJ (14-digit) numbers are never touched because the regex only
    matches exactly 11 contiguous digits.
    """
    safe: set[str] = pep_cpfs or set()

    def _replace_formatted(m: re.Match[str]) -> str:
        if _digits_only(m.group()) in safe:
            return m.group()
        return mask_formatted_cpf(m.group())

    def _replace_raw(m: re.Match[str]) -> str:
        if m.group() in safe:
            return m.group()
        return mask_raw_cpf(m.group())

    text = _CPF_FORMATTED.sub(_replace_formatted, text)
    text = _CPF_RAW.sub(_replace_raw, text)
    return text


class CPFMaskingMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that masks CPF numbers in JSON responses."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        # Read the full body from the streaming response.
        body_bytes = b""
        if isinstance(response, StreamingResponse):
            chunks: list[bytes] = []
            async for chunk in response.body_iterator:
                if isinstance(chunk, str):
                    chunks.append(chunk.encode("utf-8"))
                elif isinstance(chunk, bytes):
                    chunks.append(chunk)
                else:
                    chunks.append(bytes(chunk))
            body_bytes = b"".join(chunks)
        else:
            body_bytes = getattr(response, "body", b"")

        if not body_bytes:
            return response

        body_text = body_bytes.decode("utf-8")

        # Parse JSON to discover PEP CPFs, then mask the rest.
        pep_cpfs: set[str] = set()
        try:
            data = json.loads(body_text)
            pep_cpfs = _collect_pep_cpfs(data)
        except (json.JSONDecodeError, TypeError):
            pass

        masked_text = mask_cpfs_in_json(body_text, pep_cpfs)
        masked_bytes = masked_text.encode("utf-8")

        return Response(
            content=masked_bytes,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
