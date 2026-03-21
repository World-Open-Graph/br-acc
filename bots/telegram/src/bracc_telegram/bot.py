"""Telegram bot entrypoint and baseline handlers."""

from __future__ import annotations

from typing import Any

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from bracc_telegram.config import get_telegram_token


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    del context
    if update.message is not None:
        await update.message.reply_text(
            "BR-ACC bot is online. Use /help to see available commands."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    del context
    if update.message is not None:
        await update.message.reply_text(
            "Available commands:\n"
            "/start - Check bot status\n"
            "/help - Show this help message"
        )


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unsupported commands."""
    del context
    if update.message is not None:
        await update.message.reply_text("Unsupported command. Use /help.")


def build_application(token: str | None = None) -> Application[Any, Any, Any, Any, Any, Any]:
    """Create and configure the Telegram application."""
    bot_token = token or get_telegram_token()
    application = Application.builder().token(bot_token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    return application


def main() -> None:
    """CLI entrypoint used by `python -m bracc_telegram.bot`."""
    application = build_application()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
