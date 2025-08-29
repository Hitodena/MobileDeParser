import asyncio
from typing import Optional

from aiogram import Bot
from loguru import logger

from bot.models.parsing_progress import ParsingProgress


class ProgressTracker:
    def __init__(self, bot: Bot, chat_id: int):
        self.bot = bot
        self.chat_id = chat_id
        self.progress = ParsingProgress()
        self.progress_message_id: Optional[int] = None
        self.update_interval = 10
        self._update_task: Optional[asyncio.Task] = None
        self.total_links_found = 0
        self.cycle_count = 0
        self.last_message_text: Optional[str] = None
        self._is_running = False

    async def start_tracking(self, total_start_urls: int):
        if self._is_running:
            raise RuntimeError(
                "Парсинг уже запущен. Сначала остановите текущий парсинг командой /stop"
            )

        self._is_running = True
        self.progress = ParsingProgress()
        self.progress.start_tracking(total_start_urls)
        self.total_links_found = 0
        self.cycle_count = 0
        self.last_message_text = None

        self._update_task = asyncio.create_task(self._periodic_update())

        logger.bind(
            service="ProgressTracker",
            total_start_urls=total_start_urls,
            chat_id=self.chat_id,
        ).info("Progress tracking started")

    async def start_new_cycle(self, cycle_number: int):
        self.cycle_count = cycle_number

        self.progress.start_tracking(self.progress.total_urls)

        self.progress_message_id = None
        self.last_message_text = None

        if self._update_task and not self._update_task.done():
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

        self._update_task = asyncio.create_task(self._periodic_update())

        await self._send_progress_message()

        logger.bind(
            service="ProgressTracker",
            cycle_number=cycle_number,
            chat_id=self.chat_id,
        ).info(
            "New cycle started, progress reset and periodic update restarted"
        )

    async def update_progress(
        self,
        processed_urls: Optional[int] = None,
        found_products: Optional[int] = None,
        total_links_found: Optional[int] = None,
    ):
        if total_links_found is not None:
            self.total_links_found = max(
                self.total_links_found, total_links_found
            )
            if self.total_links_found > self.progress.total_urls:
                self.progress.total_urls = self.total_links_found

        self.progress.update_progress(processed_urls, found_products)

        if (
            self.progress.total_urls > 0
            and self.progress.processed_urls >= self.progress.total_urls
        ):
            self.progress.status = "completed"

    async def complete_tracking(
        self, success: bool = True, error_message: Optional[str] = None
    ):
        self.progress.complete_tracking(success, error_message)

        if self._update_task and not self._update_task.done():
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

        await self._send_progress_message(final=True)

        logger.bind(
            service="ProgressTracker",
            chat_id=self.chat_id,
            success=success,
            error_message=error_message,
        ).info("Progress tracking completed")

    async def stop_tracking(self):
        if not self._is_running:
            return

        self._is_running = False

        if self._update_task and not self._update_task.done():
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

        self.progress.status = "error"
        self.progress.error_message = "Парсинг остановлен пользователем"

        await self._send_progress_message(final=True)

        logger.bind(
            service="ProgressTracker",
            chat_id=self.chat_id,
        ).info("Progress tracking stopped by user")

    def is_running(self) -> bool:
        return self._is_running

    async def _send_progress_message(self, final: bool = False):
        message_text = self._format_progress_message(final)

        try:
            if self.progress_message_id and not final:
                if message_text == self.last_message_text:
                    return

                # Обновляем существующее сообщение
                await self.bot.edit_message_text(
                    chat_id=self.chat_id,
                    message_id=self.progress_message_id,
                    text=message_text,
                )
                self.last_message_text = message_text
            else:
                # Отправляем новое сообщение
                message = await self.bot.send_message(
                    chat_id=self.chat_id, text=message_text
                )
                if not final:
                    self.progress_message_id = message.message_id
                    self.last_message_text = message_text

        except Exception as e:
            logger.bind(
                service="ProgressTracker",
                chat_id=self.chat_id,
                error_type=type(e).__name__,
                error_message=str(e),
            ).error("Failed to send progress message")

    def _format_progress_message(self, final: bool = False) -> str:
        status_text = {
            "idle": "Ожидание",
            "running": "Выполняется",
            "completed": "Завершено",
            "error": "Ошибка",
        }

        message = "<b>Парсинг Mobile.de</b>\n\n"

        if self.cycle_count > 0:
            message += f"• Цикл: #{self.cycle_count}\n"

        message += f"• Статус: {status_text[self.progress.status]}\n"

        if self.progress.total_urls > 0:
            message += f"• Прогресс: {self.progress.processed_urls}/{self.progress.total_urls} "
            message += f"({self.progress.progress_percentage:.1f}%)\n"

        if self.total_links_found > 0:
            message += f"• Найдено ссылок: {self.total_links_found}\n"
        message += f"• Найдено товаров: {self.progress.found_products}\n"

        if self.progress.elapsed_time > 0:
            elapsed_minutes = int(self.progress.elapsed_time // 60)
            elapsed_seconds = int(self.progress.elapsed_time % 60)
            message += (
                f"• Время цикла: {elapsed_minutes:02d}:{elapsed_seconds:02d}\n"
            )

        if self.progress.error_message:
            message += f"\n• Ошибка: {self.progress.error_message}"

        return message

    async def _periodic_update(self):
        while self.progress.status == "running":
            try:
                await asyncio.sleep(self.update_interval)
                await self._send_progress_message()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.bind(
                    service="ProgressTracker",
                    chat_id=self.chat_id,
                    error_type=type(e).__name__,
                    error_message=str(e),
                ).error("Error in periodic update")
                break
