"""Entry point for the BR-ACC Telegram bot."""

from __future__ import annotations

import logging
from typing import Any

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from bracc_telegram.config import get_telegram_token
from bracc_telegram.handlers import (
    busca_command,
    consulta_command,
    help_command,
    start_command,
    stats_command,
)

logger = logging.getLogger(__name__)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unsupported commands."""
    del context
    if update.effective_message is not None:
        await update.effective_message.reply_text(
            r"⚠️ Comando não reconhecido\. Use /ajuda para ver os comandos disponíveis\.",
            parse_mode="MarkdownV2",
        )


def build_application(token: str | None = None) -> Application[Any, Any, Any, Any, Any, Any]:
    """Create and configure the Telegram application."""
    bot_token = token or get_telegram_token()
    application = Application.builder().token(bot_token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("ajuda", help_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("consulta", consulta_command))
    application.add_handler(CommandHandler("busca", busca_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    return application


def main() -> None:
    """CLI entrypoint used by `python -m bracc_telegram.bot`."""
    logging.basicConfig(
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        level=logging.INFO,
    )
    application = build_application()
    logger.info("BR-ACC Telegram Bot starting ...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
