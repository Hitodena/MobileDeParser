import asyncio
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

from loguru import logger
from typing_extensions import Type

from core.models.product_model import ProductModel
from core.parsers.base_parser import BaseParser
from core.parsers.mobilede_ru_parser import MobileDeRuParser
from core.services.parser_service import ParserService
from shared.config.config_model import ConfigModel
from shared.exceptions.request_exceptions import OutOfProxiesException


class SchedulerService:
    def __init__(self, config_obj: ConfigModel):
        self.parser_service = ParserService(config_obj)
        self.is_running = False
        self.current_task: Optional[asyncio.Task] = None
        self.config_obj = config_obj
        self.progress_callback: Optional[Callable[[int, int, int], None]] = (
            None
        )

        self.scheduler_logger = logger.bind(
            service="SchedulerService",
            interval=config_obj.parser.interval_between_parse,
            cycle_enabled=config_obj.parser.cycle,
        )

    async def initialize(self) -> None:
        await self.parser_service.initialize()
        self.scheduler_logger.info("Scheduler service initialized")

    def set_progress_callback(self, callback: Callable[[int, int, int], None]):
        self.progress_callback = callback
        if self.parser_service:
            self.parser_service.set_progress_callback(callback)

    async def start_cyclic_parsing(
        self,
        start_urls: List[str],
        callback: Optional[
            Callable[[Tuple[List[ProductModel], int]], None]
        ] = None,
        error_callback: Optional[Callable[[Exception], None]] = None,
        parser_class: Type[BaseParser] = MobileDeRuParser,
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
    ):
        if self.is_running:
            self.scheduler_logger.warning("Scheduler is already running")
            return

        self.is_running = True
        self.scheduler_logger.info("Starting cyclic parsing scheduler")

        if progress_callback:
            self.set_progress_callback(progress_callback)

        try:
            while self.is_running:
                cycle_start = datetime.now()
                self.scheduler_logger.bind(
                    cycle_start=cycle_start.isoformat()
                ).info("Starting parsing cycle")

                try:
                    result = await self.parser_service.run_full_parsing(
                        start_urls=start_urls,
                        parser_class=parser_class,
                    )

                    cycle_end = datetime.now()
                    cycle_duration = (cycle_end - cycle_start).total_seconds()

                    self.scheduler_logger.bind(
                        cycle_duration=cycle_duration,
                        products_parsed=len(result[0]) if result[0] else 0,
                    ).success("Parsing cycle completed")

                    if callback:
                        try:
                            callback((result[0], result[2]))
                        except Exception as e:
                            self.scheduler_logger.bind(
                                error_type=type(e).__name__,
                                error_message=str(e),
                            ).error("Callback execution failed")

                except OutOfProxiesException as e:
                    self.scheduler_logger.bind(
                        error_type=type(e).__name__, error_message=str(e)
                    ).error("No working proxies available, stopping scheduler")

                    if error_callback:
                        try:
                            error_callback(e)
                            self.scheduler_logger.info(
                                "Sent proxy error to callback"
                            )
                        except Exception as callback_error:
                            self.scheduler_logger.bind(
                                error_type=type(callback_error).__name__,
                                error_message=str(callback_error),
                            ).error("Failed to send proxy error to callback")
                    elif callback:
                        try:
                            empty_result = ([], 0)
                            callback(empty_result)
                            self.scheduler_logger.info(
                                "Sent empty results due to proxy failure"
                            )
                        except Exception as callback_error:
                            self.scheduler_logger.bind(
                                error_type=type(callback_error).__name__,
                                error_message=str(callback_error),
                            ).error("Failed to send empty results to callback")

                    break
                except Exception as e:
                    self.scheduler_logger.bind(
                        error_type=type(e).__name__, error_message=str(e)
                    ).error("Parsing cycle failed")

                    if callback:
                        try:
                            empty_result = ([], 0)
                            callback(empty_result)
                            self.scheduler_logger.info(
                                "Sent empty results due to parsing failure"
                            )
                        except Exception as callback_error:
                            self.scheduler_logger.bind(
                                error_type=type(callback_error).__name__,
                                error_message=str(callback_error),
                            ).error("Failed to send empty results to callback")

                if not self.config_obj.parser.cycle:
                    self.scheduler_logger.info("Cycle mode disabled, stopping")
                    break

                if self.is_running:
                    self.scheduler_logger.bind(
                        wait_time=self.config_obj.parser.interval_between_parse
                    ).info("Waiting for next cycle")

                    await asyncio.sleep(
                        self.config_obj.parser.interval_between_parse
                    )

        except asyncio.CancelledError:
            self.scheduler_logger.info("Scheduler was cancelled")
        except Exception as e:
            self.scheduler_logger.bind(
                error_type=type(e).__name__, error_message=str(e)
            ).error("Scheduler encountered unexpected error")
        finally:
            self.is_running = False
            self.scheduler_logger.info("Scheduler stopped")

    async def stop(self):
        if not self.is_running:
            return

        self.scheduler_logger.info("Stopping scheduler")
        self.is_running = False

        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            try:
                await self.current_task
            except asyncio.CancelledError:
                pass

        await self.parser_service.close()

    async def run_single_cycle(
        self,
        start_urls: List[str],
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
        error_callback: Optional[Callable[[Exception], None]] = None,
    ) -> Tuple[List[ProductModel], Optional[Path], int]:
        self.scheduler_logger.bind(urls_count=len(start_urls)).info(
            "Running single parsing cycle"
        )

        if progress_callback:
            self.set_progress_callback(progress_callback)

        try:
            result = await self.parser_service.run_full_parsing(
                start_urls=start_urls,
                parser_class=MobileDeRuParser,
            )

            self.scheduler_logger.bind(
                products_parsed=len(result[0]) if result[0] else 0,
            ).success("Single cycle completed")

            return result[0], result[1], result[2]

        except OutOfProxiesException as e:
            self.scheduler_logger.bind(
                error_type=type(e).__name__, error_message=str(e)
            ).error("No working proxies available")

            if error_callback:
                try:
                    error_callback(e)
                except Exception as callback_error:
                    self.scheduler_logger.bind(
                        error_type=type(callback_error).__name__,
                        error_message=str(callback_error),
                    ).error("Failed to send proxy error to callback")

            raise
        except Exception as e:
            self.scheduler_logger.bind(
                error_type=type(e).__name__, error_message=str(e)
            ).error("Single cycle failed")
            raise
        finally:
            await self.parser_service.close()

    def get_status(self) -> Dict[str, Union[bool, str, int, float]]:
        return {
            "is_running": self.is_running,
            "cycle_enabled": self.config_obj.parser.cycle,
            "interval_seconds": self.config_obj.parser.interval_between_parse,
            "max_concurrency": self.config_obj.parser.max_concurrency,
        }
