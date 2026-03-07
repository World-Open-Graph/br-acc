"""Telegram command handlers."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from telegram.constants import ParseMode

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

from bracc_telegram.api_client import BraccApiClient
from bracc_telegram.formatter import (
    format_company_graph,
    format_error,
    format_meta,
    format_rate_limit_exceeded,
    format_search_results,
)
from bracc_telegram.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

_CNPJ_PATTERN = re.compile(r"^\d{14}$")
_CNPJ_FORMATTED = re.compile(r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$")


def _clean_cnpj(raw: str) -> str:
    return re.sub(r"[.\-/]", "", raw.strip())


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — welcome message."""
    if update.effective_message is None:
        return

    await update.effective_message.reply_text(
        "🇧🇷 *Bem\\-vindo ao BR/ACC Bot\\!*\n\n"
        "Consulte dados públicos do grafo de transparência brasileiro\\.\n\n"
        "*Comandos disponíveis:*\n"
        "🔍 /consulta `<CNPJ>` — Consultar empresa\n"
        "🔎 /busca `<termo>` — Busca textual\n"
        "📊 /stats — Estatísticas do grafo\n"
        "❓ /ajuda — Ajuda completa\n\n"
        "_Dados 100% públicos — projeto open\\-source_\n"
        "[GitHub](https://github.com/World\\-Open\\-Graph/br\\-acc)",
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ajuda — detailed help."""
    if update.effective_message is None:
        return

    await update.effective_message.reply_text(
        "❓ *Ajuda — BR/ACC Bot*\n\n"
        "*Consultar empresa por CNPJ:*\n"
        "`/consulta 00000000000191`\n"
        "`/consulta 00.000.000/0001-91`\n\n"
        "*Busca textual:*\n"
        "`/busca Petrobras`\n"
        "`/busca construtora`\n\n"
        "*Estatísticas:*\n"
        "`/stats`\n\n"
        "*Limites:*\n"
        "Cada usuário tem direito a 10 consultas por mês\\.\n"
        "O limite é renovado no primeiro dia de cada mês\\.\n\n"
        "*Sobre:*\n"
        "Este bot consome dados públicos do "
        "[BR/ACC Open Graph](https://github.com/World\\-Open\\-Graph/br\\-acc)\\.\n"
        "Todos os dados apresentados são de fontes oficiais brasileiras\\.",
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
    )


async def consulta_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    api_client: BraccApiClient | None = None,
    rate_limiter: RateLimiter | None = None,
) -> None:
    """Handle /consulta <CNPJ> — company graph lookup."""
    if update.effective_message is None or update.effective_chat is None:
        return

    args = context.args or []
    if not args:
        await update.effective_message.reply_text(
            "⚠️ Uso: `/consulta <CNPJ>`\n\nExemplo: `/consulta 00000000000191`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    raw_cnpj = args[0]
    cnpj = _clean_cnpj(raw_cnpj)

    if not _CNPJ_PATTERN.match(cnpj):
        await update.effective_message.reply_text(
            "⚠️ CNPJ inválido\\. Use 14 dígitos ou o formato XX\\.XXX\\.XXX/XXXX\\-XX",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # Rate limiting
    limiter = rate_limiter or _get_rate_limiter(context)
    chat_id = update.effective_chat.id
    allowed, remaining = await limiter.check_and_increment(chat_id)
    if not allowed:
        days = limiter.days_until_reset()
        await update.effective_message.reply_text(
            format_rate_limit_exceeded(days),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # Send "typing" indicator
    await update.effective_chat.send_action("typing")

    client = api_client or _get_api_client(context)
    try:
        data = await client.get_company_graph(cnpj)
        message = format_company_graph(data)
    except Exception:
        logger.exception("Error fetching company graph for CNPJ=%s", cnpj)
        message = format_error("Não foi possível consultar esse CNPJ\\.")

    await update.effective_message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
    )

    if allowed and remaining >= 0:
        await update.effective_message.reply_text(
            f"_Consultas restantes este mês: {remaining}_",
            parse_mode=ParseMode.MARKDOWN_V2,
        )


async def busca_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    api_client: BraccApiClient | None = None,
    rate_limiter: RateLimiter | None = None,
) -> None:
    """Handle /busca <query> — text search."""
    if update.effective_message is None or update.effective_chat is None:
        return

    args = context.args or []
    if not args:
        await update.effective_message.reply_text(
            "⚠️ Uso: `/busca <termo>`\n\nExemplo: `/busca Petrobras`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    query = " ".join(args)

    # Rate limiting
    limiter = rate_limiter or _get_rate_limiter(context)
    chat_id = update.effective_chat.id
    allowed, remaining = await limiter.check_and_increment(chat_id)
    if not allowed:
        days = limiter.days_until_reset()
        await update.effective_message.reply_text(
            format_rate_limit_exceeded(days),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    await update.effective_chat.send_action("typing")

    client = api_client or _get_api_client(context)
    try:
        data = await client.search(query)
        message = format_search_results(data)
    except Exception:
        logger.exception("Error searching for query=%s", query)
        message = format_error("Não foi possível realizar a busca\\.")

    await update.effective_message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
    )


async def stats_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    api_client: BraccApiClient | None = None,
) -> None:
    """Handle /stats — graph statistics."""
    if update.effective_message is None or update.effective_chat is None:
        return

    await update.effective_chat.send_action("typing")

    client = api_client or _get_api_client(context)
    try:
        data = await client.get_meta()
        message = format_meta(data)
    except Exception:
        logger.exception("Error fetching meta stats")
        message = format_error("Não foi possível obter as estatísticas\\.")

    await update.effective_message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
    )


# ------------------------------------------------------------------
# Context helpers
# ------------------------------------------------------------------


def _get_api_client(context: ContextTypes.DEFAULT_TYPE) -> BraccApiClient:
    bot_data = context.bot_data
    if "api_client" not in bot_data:
        bot_data["api_client"] = BraccApiClient()
    client: BraccApiClient = bot_data["api_client"]
    return client


def _get_rate_limiter(context: ContextTypes.DEFAULT_TYPE) -> RateLimiter:
    bot_data = context.bot_data
    if "rate_limiter" not in bot_data:
        bot_data["rate_limiter"] = RateLimiter()
    limiter: RateLimiter = bot_data["rate_limiter"]
    return limiter
