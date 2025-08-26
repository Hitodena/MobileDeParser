from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from loguru import logger

from bot.models.bot_config import BotConfig


class AuthMiddleware(BaseMiddleware):
    def __init__(self, config: BotConfig):
        super().__init__()
        self.config = config

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None

            if user_id and not self.config.is_user_allowed(user_id):
                logger.warning(
                    f"Unauthorized access attempt from user {user_id}"
                )
                await event.answer("⛔ У вас нет доступа к этому боту.")
                return

            logger.debug(f"Authorized user {user_id} accessed the bot")

        return await handler(event, data)
