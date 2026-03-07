"""Entry point for the BR-ACC Telegram Bot."""

from __future__ import annotations

import logging

from telegram.ext import ApplicationBuilder, CommandHandler

from bracc_telegram.config import get_telegram_token
from bracc_telegram.handlers import (
    busca_command,
    consulta_command,
    help_command,
    start_command,
    stats_command,
)

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Build the Telegram application and start polling."""
    token = get_telegram_token()

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("ajuda", help_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("consulta", consulta_command))
    app.add_handler(CommandHandler("busca", busca_command))
    app.add_handler(CommandHandler("stats", stats_command))

    logger.info("BR-ACC Telegram Bot starting ...")
    app.run_polling()


if __name__ == "__main__":
    main()
