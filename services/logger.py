import sys
from typing import Dict, Literal, Optional

from loguru import logger

from utils.config import config

def init_logger(
    console_level: Literal[
        "INFO", "DEBUG", "ERROR", "WARNING", "CRITICAL"
    ] = "INFO",
    file_level: Literal[
        "INFO", "DEBUG", "ERROR", "WARNING", "CRITICAL"
    ] = "DEBUG",
    rotation: str = "10 MB",
    retention: str = "30 days",
    compression: str = "zip",
    serialize: bool = False,
    backtrace: bool = True,
    diagnose: bool = False,
    enqueue: bool = True,
    modules: Optional[Dict[str, str]] = None,
) -> None:

    logger.remove()

    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
        " <dim>({extra})</dim>"
    )

    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message} | {extra}"
    )

    logger.add(
        sys.stderr,
        level=console_level,
        format=console_format,
        colorize=True,
        backtrace=backtrace,
        diagnose=diagnose,
        enqueue=enqueue,
    )

    logger.add(
        config.logging.log_dir / "app.log",
        level=file_level,
        format=file_format,
        rotation=rotation,
        retention=retention,
        compression=compression,
        serialize=serialize,
        backtrace=backtrace,
        diagnose=diagnose,
        enqueue=enqueue,
    )

    logger.add(
        config.logging.log_dir / "errors.log",
        level="ERROR",
        format=file_format,
        rotation="5 MB",
        retention="90 days",
        compression=compression,
        serialize=serialize,
        backtrace=backtrace,
        diagnose=diagnose,
        enqueue=enqueue,
    )

    if modules:
        for module_name, level in modules.items():
            logger.add(
                config.logging.log_dir / f"{module_name}.log",
                level=level,
                format=file_format,
                filter=lambda record: record["name"] == module_name,
                rotation=rotation,
                retention=retention,
                compression=compression,
                serialize=serialize,
                backtrace=backtrace,
                diagnose=diagnose,
                enqueue=enqueue,
            )


def setup_default_logger() -> None:
    init_logger(
        console_level=config.logging.level,
        file_level=config.logging.level,
        diagnose=config.logging.diagnose,
        enqueue=config.logging.enqueue,
        rotation=config.logging.rotation,
        retention=config.logging.retention,
        compression=config.logging.compression,
        serialize=config.logging.serialize,
        backtrace=config.logging.backtrace,
    )
