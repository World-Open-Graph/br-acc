from __future__ import annotations

from telegram.ext import CommandHandler

from bracc_telegram.bot import build_application


def test_build_application_registers_core_commands() -> None:
    application = build_application("123456:TEST_TOKEN")

    command_names: set[str] = set()
    for handler in application.handlers.get(0, []):
        if isinstance(handler, CommandHandler):
            command_names.update(handler.commands)

    assert "start" in command_names
    assert "help" in command_names
