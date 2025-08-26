from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BotCommand, Message
from loguru import logger

from bot.models.bot_config import BotConfig
from bot.services.parser_manager import ParserManager


class CommandHandlers:
    def __init__(self, config: BotConfig, parser_manager: ParserManager):
        self.config = config
        self.parser_manager = parser_manager
        self.router = Router()
        self._setup_handlers()

    def _setup_handlers(self):
        self.router.message.register(self.start_command, Command("start"))
        self.router.message.register(self.stop_command, Command("stop"))
        self.router.message.register(self.status_command, Command("status"))
        self.router.message.register(self.help_command, Command("help"))

    async def start_command(self, message: Message):
        result = await self.parser_manager.start_parsing(message.chat.id)
        await message.answer(f"🚀 {result}")

    async def stop_command(self, message: Message):
        await self.parser_manager.stop_parsing()
        await message.answer("⏹️ Парсинг остановлен")

    async def status_command(self, message: Message):
        status = self.parser_manager.get_status()
        status_text = (
            f"📊 Статус парсера:\n\n"
            f"🔄 Работает: {'Да' if status.is_running else 'Нет'}\n"
            f"⏱️ Интервал: {status.interval_seconds} сек\n"
            f"🔄 Цикл: {'Включен' if status.cycle_enabled else 'Отключен'}\n"
            f"⚡ Макс. потоков: {status.max_concurrency}"
        )
        await message.answer(status_text)

    async def help_command(self, message: Message):
        help_text = (
            "📖 Справка по командам:\n\n"
            "🚀 /start - Запустить парсинг Mobile.de\n"
            "⏹️ /stop - Остановить текущий парсинг\n"
            "📊 /status - Показать статус парсера\n"
            "❓ /help - Показать эту справку\n\n"
            "После завершения парсинга вы получите архив с результатами."
        )
        await message.answer(help_text)

    async def setup_commands(self, bot):
        commands = [
            BotCommand(command="start", description="Запустить парсинг"),
            BotCommand(command="stop", description="Остановить парсинг"),
            BotCommand(command="status", description="Статус парсера"),
            BotCommand(command="help", description="Справка"),
        ]

        try:
            await bot.set_my_commands(commands)
            logger.info("Bot commands set successfully")
        except Exception as e:
            logger.error(f"Failed to set bot commands: {e}")
