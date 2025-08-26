import asyncio
import signal
from typing import Optional

from loguru import logger

from bot.bot import TelegramBot
from bot.models.bot_config import BotConfig


class BotLifecycle:

    def __init__(self, config: BotConfig):
        self.config = config
        self.bot: Optional[TelegramBot] = None
        self._shutdown_event = asyncio.Event()
        self._tasks: list[asyncio.Task] = []
        self._shutdown_in_progress = False

    async def start(self):
        logger.info("Starting bot lifecycle...")

        self.bot = TelegramBot(self.config)
        await self.bot.initialize()

        self._setup_signal_handlers()

        bot_task = asyncio.create_task(self.bot.start())
        self._tasks.append(bot_task)

        logger.info("Bot lifecycle started successfully")

    async def stop(self):
        if self._shutdown_in_progress:
            logger.info("Shutdown already in progress, skipping...")
            return

        self._shutdown_in_progress = True
        logger.info("Stopping bot lifecycle...")

        self._shutdown_event.set()

        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        if self.bot:
            await self.bot.stop()

        logger.info("Bot lifecycle stopped")

    async def wait_for_shutdown(self):
        await self._shutdown_event.wait()

    def _setup_signal_handlers(self):
        def signal_handler(signum, frame):
            if not self._shutdown_in_progress:
                logger.info(
                    f"Received signal {signum}, initiating shutdown..."
                )
                asyncio.create_task(self.stop())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
