import sys
from pathlib import Path
from typing import List, Literal, Optional

from loguru import logger


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
    modules: Optional[List[str]] = None,
    log_dir: Path = Path("logs"),
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
        log_dir / "app.log",
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
        log_dir / "errors.log",
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
        for module_name in modules:
            logger.add(
                log_dir / f"{module_name}.log",
                level="DEBUG",
                format=file_format,
                filter=module_name,
                rotation=rotation,
                retention=retention,
                compression=compression,
                serialize=serialize,
                backtrace=backtrace,
                diagnose=diagnose,
                enqueue=enqueue,
            )


def setup_default_logger(
    console_level,
    file_level,
    diagnose,
    enqueue,
    rotation,
    retention,
    compression,
    serialize,
    backtrace,
    log_dir,
    modules,
) -> None:
    init_logger(
        console_level=console_level,
        file_level=file_level,
        diagnose=diagnose,
        enqueue=enqueue,
        rotation=rotation,
        retention=retention,
        compression=compression,
        serialize=serialize,
        backtrace=backtrace,
        log_dir=log_dir,
        modules=modules,
    )
