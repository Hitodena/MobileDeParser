from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from bot.handlers.commands import CommandHandlers
from bot.middleware.middleware import AuthMiddleware
from bot.models.bot_config import BotConfig
from bot.services.parser_manager import ParserManager


class TelegramBot:
    def __init__(self, config: BotConfig):
        self.config = config
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self.parser_manager: Optional[ParserManager] = None
        self.command_handlers: Optional[CommandHandlers] = None

    async def initialize(self):

        self.bot = Bot(
            token=self.config.token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

        self.dp = Dispatcher()

        auth_middleware = AuthMiddleware(self.config)
        self.dp.message.middleware(auth_middleware)

        self.parser_manager = ParserManager(self.config, self.bot)
        await self.parser_manager.initialize()

        self.command_handlers = CommandHandlers(
            self.config, self.parser_manager
        )

        self.dp.include_router(self.command_handlers.router)

        await self.command_handlers.setup_commands(self.bot)

        logger.info("Telegram bot initialized successfully")

    async def start(self):
        if not self.bot or not self.dp:
            raise RuntimeError("Bot not initialized. Call initialize() first.")

        await self.dp.start_polling(self.bot)
        logger.info("Telegram bot started")

    async def stop(self):
        logger.info("Stopping Telegram bot...")

        if self.parser_manager:
            await self.parser_manager.close()

        if self.dp:
            try:
                await self.dp.stop_polling()
                logger.info("Polling stopped successfully")
            except Exception as e:
                logger.warning(f"Error stopping polling: {e}")

        if self.bot:
            try:
                await self.bot.session.close()
                logger.info("Bot session closed successfully")
            except Exception as e:
                logger.warning(f"Error closing bot session: {e}")

        logger.info("Telegram bot stopped")

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
