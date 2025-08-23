import asyncio

from shared.config.config import config
from shared.services.http_client import HTTPClient
from shared.services.logger import setup_default_logger
from shared.utils.proxy_manager import ProxyManager

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
)

proxy_manager = ProxyManager(
    config.parser.proxy_file,
    config.parser.proxy_timeout,
    config.parser.check_url,
)
