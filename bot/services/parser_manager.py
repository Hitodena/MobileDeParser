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
from shared.exceptions.request_exceptions import OutOfProxiesException


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
        logger.bind(service="ParserManager").info("Parser manager initialized")

    async def start_parsing(
        self, chat_id: int, start_urls: Optional[List[str]] = None
    ):
        try:
            if self.current_task and not self.current_task.done():
                return "Парсинг уже запущен"

            self.notification_chat_id = chat_id

            if start_urls is None:
                start_urls = self.config.parser.links

            for url in start_urls:
                if not url.startswith(
                    "https://mobile.de/ru/"
                ) and not url.startswith("https://www.mobile.de/ru/"):
                    error_msg = f"• Ошибка: Неверный формат URL. Ожидается URL начинающийся с 'https://mobile.de/ru/', получен: {url}"
                    await self.bot.send_message(chat_id, error_msg)
                    return "Парсинг не запущен из-за ошибки в URL"

            self.progress_tracker = ProgressTracker(self.bot, chat_id)

            await self.progress_tracker.start_tracking(len(start_urls))

            def parsing_callback(
                result_tuple: Tuple[List[ProductModel], int],
            ):
                asyncio.create_task(
                    self._handle_parsing_result(chat_id, result_tuple)
                )

            def error_callback(error: Exception):
                asyncio.create_task(self._handle_parsing_error(chat_id, error))

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
                        error_callback=error_callback,
                        parser_class=MobileDeRuParser,
                        progress_callback=progress_callback,
                    )
                )

            logger.bind(chat_id=chat_id).info("Parsing started for chat")
            return "Парсинг запущен"

        except OutOfProxiesException as e:
            error_msg = (
                f"• Ошибка: Не осталось рабочих прокси!\n\n"
                f"• Парсинг остановлен из-за отсутствия рабочих прокси.\n"
                f"• Необходимо обновить список прокси в конфигурации.\n"
                f"• Проверьте файл: {self.config.parser.proxy_file}\n\n"
                f"• После обновления прокси перезапустите парсинг командой /start"
            )
            await self.bot.send_message(chat_id, error_msg)
            logger.bind(
                chat_id=chat_id,
                error_type=type(e).__name__,
                error_message=str(e),
            ).error("No working proxies available for chat")
            return "Парсинг не запущен из-за отсутствия рабочих прокси"
        except Exception as e:
            error_msg = f"• Ошибка при запуске парсинга: {str(e)}"
            await self.bot.send_message(chat_id, error_msg)
            logger.bind(
                chat_id=chat_id,
                error_type=type(e).__name__,
                error_message=str(e),
            ).error("Failed to start parsing for chat")
            return "Парсинг не запущен из-за ошибки"

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

        logger.bind(service="ParserManager").info("Parsing stopped")
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
        result_tuple: Tuple[List[ProductModel], int],
    ):
        products, saved_count = result_tuple

        if self.progress_tracker:
            await self.progress_tracker.complete_tracking(success=True)

        try:
            if not products:
                await self.bot.send_message(
                    chat_id, "• Парсинг завершен, но результаты не найдены"
                )
                return

            await self.bot.send_message(
                chat_id,
                f"• Парсинг завершен!\n"
                f"• Найдено товаров: {len(products)}\n"
                f"• Новых сохранено: {saved_count}\n"
                f"• Все продукты сохранены в базу данных\n\n"
                f"• Используйте /exportdb для создания архива всех продуктов",
            )
            logger.bind(chat_id=chat_id, products_count=len(products)).info(
                "Parsing completed for chat"
            )

        except Exception as e:
            logger.bind(
                chat_id=chat_id,
                error_type=type(e).__name__,
                error_message=str(e),
            ).error("Failed to send results")
            await self.bot.send_message(
                chat_id, f"• Ошибка при отправке результатов: {str(e)}"
            )

    async def _handle_parsing_error(
        self,
        chat_id: int,
        error: Exception,
    ):
        if self.progress_tracker:
            await self.progress_tracker.complete_tracking(
                success=False, error_message="Ошибка парсинга"
            )

        if isinstance(error, OutOfProxiesException):
            error_msg = (
                f"• Ошибка: Не осталось рабочих прокси!\n\n"
                f"• Парсинг остановлен из-за отсутствия рабочих прокси.\n"
                f"• Необходимо обновить список прокси в конфигурации.\n"
                f"• Проверьте файл: {self.config.parser.proxy_file}\n\n"
                f"• После обновления прокси перезапустите парсинг командой /start"
            )
        else:
            error_msg = f"• Ошибка парсинга: {str(error)}"

        await self.bot.send_message(chat_id, error_msg)
        logger.bind(
            chat_id=chat_id,
            error_type=type(error).__name__,
            error_message=str(error),
        ).error("Parsing error occurred for chat")

    async def close(self):
        await self.stop_parsing()
        logger.bind(service="ParserManager").info("Parser manager closed")

    def get_database_stats(self) -> dict:
        if self.scheduler and self.scheduler.parser_service:
            return self.scheduler.parser_service.get_database_stats()
        return {"error": "Parser service not available"}

    def create_sql_dump(self, output_path: str) -> bool:
        if self.scheduler and self.scheduler.parser_service:
            return self.scheduler.parser_service.create_sql_dump(output_path)
        return False

    def export_from_database(self) -> Optional[Tuple[Path, int]]:
        if self.scheduler and self.scheduler.parser_service:
            return self.scheduler.parser_service.export_from_database()
        return None
