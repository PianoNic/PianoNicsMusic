import logging
import logging.handlers
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from cogs import COGS

load_dotenv()


class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[35m',
        'RESET': '\033[0m',
    }

    def format(self, record):
        message = super().format(record)
        color = self.COLORS.get(record.levelname)

        if color:
            message = message.replace(
                f"[{record.levelname}]", f"[{color}{record.levelname}{self.COLORS['RESET']}]"
            )

        return message


def setup_logging():
    os.makedirs('logs', exist_ok=True)

    file_handler = logging.handlers.RotatingFileHandler(
        filename='logs/discord.log',
        encoding='utf-8',
        maxBytes=32 * 1024 * 1024,
        backupCount=5,
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColoredFormatter('[{levelname}] {name}: {message}', style='{'))

    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.INFO)
    discord_logger.addHandler(console_handler)
    logging.getLogger('discord.http').setLevel(logging.INFO)

    app_logger = logging.getLogger('PianoNicsMusic')
    app_logger.setLevel(logging.DEBUG)
    app_logger.addHandler(file_handler)
    app_logger.addHandler(console_handler)
    app_logger.propagate = False

    return app_logger


app_logger = setup_logging()

bot = commands.Bot(command_prefix=[".", "!", "$"], intents=discord.Intents.all(), help_command=None)

for cog in COGS:
    try:
        bot.load_extension(cog)
    except Exception as error:
        app_logger.error(f"Failed to load {cog}: {error}")

bot.run(os.getenv('DISCORD_TOKEN'))
