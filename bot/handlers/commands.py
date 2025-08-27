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
        self.users_waiting_for_url = set()
        self._setup_handlers()

    def _setup_handlers(self):
        self.router.message.register(self.start_command, Command("start"))
        self.router.message.register(self.stop_command, Command("stop"))
        self.router.message.register(self.status_command, Command("status"))
        self.router.message.register(self.help_command, Command("help"))
        self.router.message.register(self.seturl_command, Command("seturl"))
        self.router.message.register(
            self.database_stats_command, Command("dbstats")
        )
        self.router.message.register(self.sql_dump_command, Command("sqldump"))
        self.router.message.register(
            self.export_db_command, Command("exportdb")
        )
        self.router.message.register(
            self.handle_url_message,
            lambda message: self._is_url_message(message),
        )
        self.router.message.register(self.handle_text_message)

    def _is_url_message(self, message: Message) -> bool:
        if not message.text:
            return False
        text = message.text.strip()
        return text.startswith("http")

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
            "🔗 /seturl - Установить ссылку для парсинга\n"
            "📊 /dbstats - Статистика базы данных\n"
            "💾 /sqldump - Создать SQL дамп базы\n"
            "📦 /exportdb - Экспорт всех продуктов из БД\n"
            "❓ /help - Показать эту справку\n\n"
            "💡 Просто отправьте ссылку на страницу Mobile.de для парсинга\n"
            "После завершения парсинга вы получите архив с результатами."
        )
        await message.answer(help_text)

    async def seturl_command(self, message: Message):
        self.users_waiting_for_url.add(message.chat.id)
        await message.answer(
            "🔗 Отправьте ссылку на страницу Mobile.de для парсинга.\n"
            "Ссылка должна начинаться с https://mobile.de/ru/\n\n"
            "⏳ Ожидаю ссылку..."
        )

    async def handle_url_message(self, message: Message):
        text = message.text
        if text is None:
            return

        text = text.strip()

        if text.startswith("http"):
            if text.startswith("https://mobile.de/ru/") or text.startswith(
                "https://www.mobile.de/ru/"
            ):
                self.config.parser.base_search_url = text

                self.users_waiting_for_url.discard(message.chat.id)

                await message.answer(
                    f"✅ Ссылка установлена: {text}\n"
                    f"Теперь можете запустить парсинг командой /start"
                )
                logger.bind(
                    service="Commands", chat_id=message.chat.id, url=text
                ).info("URL set by user")
            else:
                await message.answer(
                    "❌ Неверный формат ссылки!\n"
                    "Ссылка должна начинаться с https://mobile.de/ru/\n\n"
                    "🔄 Попробуйте еще раз или отправьте /seturl для отмены"
                )
        else:
            if message.chat.id in self.users_waiting_for_url:
                await message.answer(
                    "❌ Это не похоже на ссылку.\n"
                    "Отправьте ссылку, начинающуюся с https://mobile.de/ru/\n\n"
                    "🔄 Попробуйте еще раз или отправьте /seturl для отмены"
                )

    async def handle_text_message(self, message: Message):
        if message.chat.id in self.users_waiting_for_url:
            await message.answer(
                "❌ Это не похоже на ссылку.\n"
                "Отправьте ссылку, начинающуюся с https://mobile.de/ru/\n\n"
                "🔄 Попробуйте еще раз или отправьте /seturl для отмены"
            )

    async def database_stats_command(self, message: Message):
        try:
            stats = self.parser_manager.get_database_stats()
            if "error" in stats:
                await message.answer(
                    f"❌ Ошибка получения статистики: {stats['error']}"
                )
                return

            stats_text = (
                f"📊 Статистика базы данных:\n\n"
                f"🗄️ Всего продуктов: {stats['total_products']:,}\n"
                f"📁 Путь к БД: {stats['database_path']}\n\n"
                f"💡 База данных автоматически фильтрует дубли при парсинге"
            )
            await message.answer(stats_text)

        except Exception as e:
            await message.answer(f"❌ Ошибка: {str(e)}")

    async def sql_dump_command(self, message: Message):
        try:
            await message.answer("💾 Создаю SQL дамп базы данных...")

            from datetime import datetime

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            dump_path = f"database_dump_{timestamp}.sql"

            success = self.parser_manager.create_sql_dump(dump_path)

            if success:
                await message.answer(
                    f"✅ SQL дамп создан успешно!\n"
                    f"📁 Файл: {dump_path}\n\n"
                    f"💡 Файл содержит все продукты из базы данных"
                )
            else:
                await message.answer("❌ Ошибка при создании SQL дампа")

        except Exception as e:
            await message.answer(f"❌ Ошибка: {str(e)}")

    async def export_db_command(self, message: Message):
        try:
            await message.answer(
                "📦 Экспортирую все продукты из базы данных..."
            )

            result = self.parser_manager.export_from_database()

            if result:
                archive_path, exported_count = result

                from aiogram.types import FSInputFile

                document = FSInputFile(str(archive_path))

                await message.answer_document(
                    document,
                    caption=f"✅ Экспорт завершен!\n"
                    f"📦 Экспортировано: {exported_count:,} продуктов\n"
                    f"📁 Архив: {archive_path.name}\n\n"
                    f"💡 Архив содержит все продукты из базы данных",
                )
            else:
                await message.answer(
                    "❌ Нет данных для экспорта или ошибка при экспорте"
                )

        except Exception as e:
            await message.answer(f"❌ Ошибка: {str(e)}")

    async def setup_commands(self, bot):
        commands = [
            BotCommand(command="start", description="Запустить парсинг"),
            BotCommand(command="stop", description="Остановить парсинг"),
            BotCommand(command="status", description="Статус парсера"),
            BotCommand(command="seturl", description="Установить ссылку"),
            BotCommand(command="dbstats", description="Статистика БД"),
            BotCommand(command="sqldump", description="SQL дамп БД"),
            BotCommand(command="exportdb", description="Экспорт из БД"),
            BotCommand(command="help", description="Справка"),
        ]

        try:
            await bot.set_my_commands(commands)
            logger.bind(service="Commands").info(
                "Bot commands set successfully"
            )
        except Exception as e:
            logger.bind(
                service="Commands",
                error_type=type(e).__name__,
                error_message=str(e),
            ).error("Failed to set bot commands")
