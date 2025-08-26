import asyncio
import platform
import sys

from loguru import logger

from bot.models.bot_config import BotConfig
from bot.utils.lifecycle import BotLifecycle
from shared.config.config import config
from shared.services.logger import setup_default_logger

setup_default_logger(
    config.logging.level,
    config.logging.level,
    config.logging.diagnose,
    config.logging.enqueue,
    config.logging.rotation,
    config.logging.retention,
    config.logging.compression,
    config.logging.serialize,
    config.logging.backtrace,
    config.logging.log_dir,
    config.logging.modules,
)

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def main():
    bot_config = BotConfig.from_config_model(config)
    lifecycle = BotLifecycle(bot_config)

    try:
        await lifecycle.start()
        await lifecycle.wait_for_shutdown()
    except KeyboardInterrupt:
        logger.info("Получен сигнал завершения...")
    finally:
        await lifecycle.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)
