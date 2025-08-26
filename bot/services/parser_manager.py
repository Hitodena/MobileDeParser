import asyncio
from pathlib import Path
from typing import List, Optional, Tuple

from aiogram import Bot
from loguru import logger

from bot.models.bot_config import BotConfig
from bot.models.parser_status import ParserStatus
from bot.services.progress_tracker import ProgressTracker
from core.models.product_model import ProductModel
from core.parsers.mobilede_ru_parser import MobileDeRuParser
from core.services.scheduler_service import SchedulerService


class ParserManager:
    def __init__(self, config: BotConfig, bot: Bot):
        self.config = config
        self.bot = bot
        self.scheduler: Optional[SchedulerService] = None
        self.current_task: Optional[asyncio.Task] = None
        self.progress_tracker: Optional[ProgressTracker] = None
        self.notification_chat_id: Optional[int] = None

        self.scheduler_config = config

    async def initialize(self):
        self.scheduler = SchedulerService(self.scheduler_config)
        await self.scheduler.initialize()
        logger.info("Parser manager initialized")

    async def start_parsing(
        self, chat_id: int, start_urls: Optional[List[str]] = None
    ):
        if self.current_task and not self.current_task.done():
            return "Парсинг уже запущен"

        self.notification_chat_id = chat_id

        if start_urls is None:
            start_urls = self.config.parser.links

        self.progress_tracker = ProgressTracker(self.bot, chat_id)

        await self.progress_tracker.start_tracking(len(start_urls))

        def parsing_callback(
            result_tuple: Tuple[List[ProductModel], Optional[Path], int],
        ):
            asyncio.create_task(
                self._handle_parsing_result(chat_id, result_tuple)
            )

        def progress_callback(
            processed_urls: int,
            found_products: int,
            total_links_found: int = 0,
        ):
            if self.progress_tracker:
                asyncio.create_task(
                    self.progress_tracker.update_progress(
                        processed_urls, found_products, total_links_found
                    )
                )

        if self.scheduler:
            self.current_task = asyncio.create_task(
                self.scheduler.start_cyclic_parsing(
                    start_urls=start_urls,
                    callback=parsing_callback,
                    parser_class=MobileDeRuParser,
                    progress_callback=progress_callback,
                )
            )

        logger.info(f"Parsing started for chat {chat_id}")
        return "Парсинг запущен"

    async def stop_parsing(self):
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            try:
                await self.current_task
            except asyncio.CancelledError:
                pass

        if self.progress_tracker:
            await self.progress_tracker.complete_tracking(
                success=False, error_message="Парсинг остановлен пользователем"
            )

        if self.scheduler:
            await self.scheduler.stop()

        logger.info("Parsing stopped")
        return "Парсинг остановлен"

    def get_status(self) -> ParserStatus:
        if self.scheduler:
            status_dict = self.scheduler.get_status()
            return ParserStatus(
                is_running=bool(status_dict["is_running"]),
                cycle_enabled=bool(status_dict["cycle_enabled"]),
                interval_seconds=int(status_dict["interval_seconds"]),
                max_concurrency=int(status_dict["max_concurrency"]),
            )
        return ParserStatus.create_default()

    async def _handle_parsing_result(
        self,
        chat_id: int,
        result_tuple: Tuple[List[ProductModel], Optional[Path], int],
    ):
        products, archive_path, saved_count = result_tuple

        if self.progress_tracker:
            await self.progress_tracker.complete_tracking(success=True)

        try:
            if not products:
                await self.bot.send_message(
                    chat_id, "❌ Парсинг завершен, но результаты не найдены"
                )
                return

            if archive_path and archive_path.exists():
                await self._send_existing_archive(
                    chat_id, archive_path, saved_count
                )
                logger.info(
                    f"Sent existing archive to chat {chat_id}: {saved_count} products"
                )
            else:
                await self.bot.send_message(
                    chat_id,
                    f"📦 Парсинг завершен!\n"
                    f"✅ Найдено товаров: {len(products)}\n"
                    f"📁 Архив не был создан из-за ошибки сохранения.",
                )
                logger.warning(
                    f"No archive available for chat {chat_id}, sent message only"
                )

        except Exception as e:
            logger.error(f"Failed to send results: {e}")
            await self.bot.send_message(
                chat_id, f"❌ Ошибка при отправке результатов: {str(e)}"
            )

    async def _send_existing_archive(
        self, chat_id: int, archive_path: Path, products_count: int
    ):
        from aiogram.types import FSInputFile

        document = FSInputFile(str(archive_path))
        await self.bot.send_document(
            chat_id,
            document,
            caption=f"📦 Результаты парсинга: {products_count} товаров",
        )

    async def close(self):
        await self.stop_parsing()
        logger.info("Parser manager closed")
