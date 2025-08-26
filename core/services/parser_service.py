import asyncio
from pathlib import Path
from typing import Callable, List, Optional, Tuple, Type

from loguru import logger

from core.models.product_model import ProductModel
from core.parsers.base_parser import BaseParser
from shared.config.config_model import ConfigModel
from shared.services.http_client import HTTPClient
from shared.utils.proxy_manager import ProxyManager
from shared.utils.storage_management import save_products_to_files


class ParserService:
    def __init__(self, config_obj: ConfigModel):
        self.proxy_manager = ProxyManager(
            proxy_file=config_obj.parser.proxy_file,
            timeout=config_obj.parser.proxy_timeout,
            check_url=config_obj.parser.check_url,
        )
        self.http_client = HTTPClient(
            proxy_manager=self.proxy_manager,
            timeout=config_obj.parser.proxy_timeout,
            retries=config_obj.parser.retries,
            delay_min=config_obj.parser.delay_min,
            delay_max=config_obj.parser.delay_max,
        )

        self.request_semaphore = asyncio.Semaphore(
            config_obj.parser.max_concurrency
        )

        self.service_logger = logger.bind(
            service="ParserService",
            max_concurrency=config_obj.parser.max_concurrency,
        )
        self.config_obj = config_obj
        self.progress_callback: Optional[Callable[[int, int, int], None]] = (
            None
        )

    async def initialize(self) -> None:
        await self.proxy_manager.initialize()
        self.service_logger.info("Parser service initialized")

    def set_progress_callback(self, callback: Callable[[int, int, int], None]):
        self.progress_callback = callback

    def _update_progress(
        self,
        processed_urls: int,
        found_products: int,
        total_links_found: int = 0,
    ):
        if self.progress_callback:
            try:
                self.progress_callback(
                    processed_urls, found_products, total_links_found
                )
            except Exception as e:
                self.service_logger.error(f"Progress callback error: {e}")

    async def parse_links_from_url(
        self, url: str, parser_class: Type[BaseParser]
    ) -> List[str]:
        async with self.request_semaphore:
            try:
                self.service_logger.bind(url=url).info("Starting link parsing")

                html_content = await self.http_client.get_content(url)

                parser = parser_class(
                    html_content, self.config_obj.parser.base_url, url
                )
                links = parser.parse_for_links()

                self.service_logger.bind(
                    url=url, links_found=len(links)
                ).success("Link parsing completed")

                return links

            except Exception as e:
                self.service_logger.bind(
                    url=url, error_type=type(e).__name__, error_message=str(e)
                ).error("Failed to parse links")
                return []

    async def parse_links_batch(
        self,
        urls: List[str],
        parser_class: Type[BaseParser],
    ) -> List[str]:
        self.service_logger.bind(batch_size=len(urls)).info(
            "Starting batch link parsing"
        )

        tasks = [self.parse_links_from_url(url, parser_class) for url in urls]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_links = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.service_logger.bind(
                    url=urls[i],
                    error_type=type(result).__name__,
                    error_message=str(result),
                ).error("Task failed during batch link parsing")
            elif isinstance(result, list):
                all_links.extend(result)

        unique_links = list(set(all_links))

        self.service_logger.bind(
            total_links=len(all_links),
            unique_links=len(unique_links),
            batch_size=len(urls),
        ).success("Batch link parsing completed")

        return unique_links

    async def parse_product_card(
        self,
        url: str,
        parser_class: Type[BaseParser],
    ) -> Optional[ProductModel]:
        async with self.request_semaphore:
            try:
                self.service_logger.bind(url=url).debug(
                    "Starting product card parsing"
                )

                html_content = await self.http_client.get_content(url)

                parser = parser_class(
                    html_content,
                    self.config_obj.parser.base_url,
                    url,
                )
                product_data = parser.parse_for_data()

                self.service_logger.bind(
                    url=url,
                ).success("Product card parsing completed")

                return product_data

            except Exception as e:
                self.service_logger.bind(
                    url=url, error_type=type(e).__name__, error_message=str(e)
                ).error("Failed to parse product card")
                return None

    async def parse_products_batch(
        self,
        urls: List[str],
        parser_class: Type[BaseParser],
    ) -> List[ProductModel]:
        self.service_logger.bind(
            total_urls=len(urls),
            batch_size=self.config_obj.parser.max_concurrency,
        ).info("Starting batch product parsing")

        all_products = []
        processed_urls = 0

        for i in range(0, len(urls), self.config_obj.parser.max_concurrency):
            batch_urls = urls[i : i + self.config_obj.parser.max_concurrency]

            self.service_logger.bind(
                batch_number=i // self.config_obj.parser.max_concurrency + 1,
                batch_size=len(batch_urls),
            ).info("Processing batch")

            tasks = [
                self.parse_product_card(url, parser_class)
                for url in batch_urls
            ]

            batch_results = await asyncio.gather(
                *tasks, return_exceptions=True
            )

            for j, result in enumerate(batch_results):
                processed_urls += 1
                if isinstance(result, Exception):
                    self.service_logger.bind(
                        url=batch_urls[j],
                        error_type=type(result).__name__,
                        error_message=str(result),
                    ).error("Task failed during batch product parsing")
                elif isinstance(result, ProductModel):
                    all_products.append(result)

            self._update_progress(processed_urls, len(all_products))

        self.service_logger.bind(
            total_products=len(all_products), total_urls=len(urls)
        ).success("Batch product parsing completed")

        return all_products

    async def run_full_parsing(
        self,
        start_urls: List[str],
        parser_class: Type[BaseParser],
    ) -> Tuple[List[ProductModel], Optional[Path], int]:
        self.service_logger.bind(start_urls_count=len(start_urls)).info(
            "Starting full parsing cycle"
        )

        all_links = []
        processed_start_urls = 0
        parsing_errors = []

        try:
            for i in range(
                0, len(start_urls), self.config_obj.parser.max_concurrency
            ):
                batch_urls = start_urls[
                    i : i + self.config_obj.parser.max_concurrency
                ]

                self.service_logger.bind(
                    link_batch_number=i
                    // self.config_obj.parser.max_concurrency
                    + 1,
                    batch_size=len(batch_urls),
                ).info("Processing links batch")

                try:
                    batch_links = await self.parse_links_batch(
                        batch_urls, parser_class
                    )
                    all_links.extend(batch_links)
                    processed_start_urls += len(batch_urls)

                    self._update_progress(
                        processed_start_urls, 0, len(all_links)
                    )

                except Exception as e:
                    error_msg = f"Failed to parse links batch: {str(e)}"
                    parsing_errors.append(error_msg)
                    self.service_logger.bind(
                        batch_urls=batch_urls,
                        error_type=type(e).__name__,
                        error_message=str(e),
                    ).error(
                        "Batch link parsing failed, continuing with next batch"
                    )

        except Exception as e:
            error_msg = f"Critical error during link parsing: {str(e)}"
            parsing_errors.append(error_msg)
            self.service_logger.bind(
                error_type=type(e).__name__,
                error_message=str(e),
            ).error("Critical error during link parsing phase")

        unique_links = list(set(all_links))

        self.service_logger.bind(
            total_links_found=len(unique_links),
            parsing_errors=len(parsing_errors),
        ).info("Link parsing phase completed")

        products = []
        if unique_links:
            try:
                products = await self.parse_products_batch(
                    unique_links, parser_class
                )
            except Exception as e:
                error_msg = f"Failed to parse products: {str(e)}"
                parsing_errors.append(error_msg)
                self.service_logger.bind(
                    error_type=type(e).__name__,
                    error_message=str(e),
                ).error("Product parsing failed")

        self.service_logger.bind(
            total_products=len(products),
            total_links=len(unique_links),
            total_errors=len(parsing_errors),
        ).success("Full parsing cycle completed")

        archive_path = None
        saved_count = 0
        try:
            result = self.save_products(products)
            if result is not None:
                archive_path, saved_count = result
        except Exception as e:
            error_msg = f"Failed to save products: {str(e)}"
            parsing_errors.append(error_msg)
            self.service_logger.bind(
                error_type=type(e).__name__,
                error_message=str(e),
            ).error("Failed to save products to archive")

        if parsing_errors:
            self.service_logger.bind(
                error_count=len(parsing_errors), errors=parsing_errors
            ).warning("Parsing completed with errors")

        return products, archive_path, saved_count

    async def close(self):
        if hasattr(self.http_client, "_session") and self.http_client._session:
            await self.http_client._session.close()

        self.service_logger.info("Parser service closed")

    def save_products(
        self, products: List[ProductModel]
    ) -> Optional[Tuple[Path, int]]:
        self.service_logger.bind(products_count=len(products)).info(
            "Starting products saving process"
        )

        try:
            result = save_products_to_files(products, self.config_obj)
            if result is not None:
                archive_path, saved_count = result
                self.service_logger.bind(
                    products_count=len(products),
                    saved_count=saved_count,
                    archive_path=archive_path,
                ).success("Products saving completed")
                return archive_path, saved_count
            else:
                self.service_logger.bind(
                    products_count=len(products),
                ).warning("No products were saved")
                return None

        except Exception as e:
            self.service_logger.bind(
                products_count=len(products),
                error_type=type(e).__name__,
                error_message=str(e),
            ).error("Failed to save products")
            raise
