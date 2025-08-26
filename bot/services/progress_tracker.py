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
        self.update_interval = 30
        self._update_task: Optional[asyncio.Task] = None
        self.total_links_found = 0

    async def start_tracking(self, total_start_urls: int):
        self.progress = ParsingProgress()
        self.progress.start_tracking(total_start_urls)
        self.total_links_found = 0

        await self._send_progress_message()

        self._update_task = asyncio.create_task(self._periodic_update())

        logger.info(
            f"Progress tracking started for {total_start_urls} start URLs"
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

        logger.info(
            f"Progress tracking completed: {'success' if success else 'error'}"
        )

    async def _send_progress_message(self, final: bool = False):
        message_text = self._format_progress_message(final)

        try:
            if self.progress_message_id:
                await self.bot.edit_message_text(
                    chat_id=self.chat_id,
                    message_id=self.progress_message_id,
                    text=message_text,
                )
            else:
                message = await self.bot.send_message(
                    chat_id=self.chat_id, text=message_text
                )
                self.progress_message_id = message.message_id

        except Exception as e:
            logger.error(f"Failed to send progress message: {e}")

    def _format_progress_message(self, final: bool = False) -> str:
        status_emoji = {
            "idle": "⏸️",
            "running": "🔄",
            "completed": "✅",
            "error": "❌",
        }

        emoji = status_emoji.get(self.progress.status, "❓")
        status_text = {
            "idle": "Ожидание",
            "running": "Выполняется",
            "completed": "Завершено",
            "error": "Ошибка",
        }

        message = f"{emoji} <b>Парсинг Mobile.de</b>\n\n"
        message += f"📊 Статус: {status_text[self.progress.status]}\n"

        if self.progress.total_urls > 0:
            message += f"📈 Прогресс: {self.progress.processed_urls}/{self.progress.total_urls} "
            message += f"({self.progress.progress_percentage:.1f}%)\n"

        if self.total_links_found > 0:
            message += f"🔗 Найдено ссылок: {self.total_links_found}\n"
        message += f"🛒 Найдено товаров: {self.progress.found_products}\n"

        if self.progress.elapsed_time > 0:
            elapsed_minutes = int(self.progress.elapsed_time // 60)
            elapsed_seconds = int(self.progress.elapsed_time % 60)
            message += (
                f"⏱️ Время: {elapsed_minutes:02d}:{elapsed_seconds:02d}\n"
            )

        if self.progress.error_message:
            message += f"\n❌ Ошибка: {self.progress.error_message}"

        if final and self.progress.status == "completed":
            message += "\n\n✅ Парсинг завершен! Результаты будут отправлены отдельным сообщением."

        return message

    async def _periodic_update(self):
        while self.progress.status == "running":
            try:
                await asyncio.sleep(self.update_interval)
                await self._send_progress_message()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic update: {e}")
                break
