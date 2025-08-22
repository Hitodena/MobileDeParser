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
)
