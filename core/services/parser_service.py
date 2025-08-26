import asyncio
from pathlib import Path
from typing import List, Optional, Type

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
            check_url=config_obj.parser.base_url,
        )
        self.http_client = HTTPClient(
            proxy_manager=self.proxy_manager,
            timeout=config_obj.parser.proxy_timeout,
            retries=config_obj.parser.retries,
        )

        self.request_semaphore = asyncio.Semaphore(
            config_obj.parser.max_concurrency
        )

        self.service_logger = logger.bind(
            service="ParserService",
            max_concurrency=config_obj.parser.max_concurrency,
        )
        self.config_obj = config_obj

    async def initialize(self) -> None:
        await self.proxy_manager.initialize()
        self.service_logger.info("Parser service initialized")

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
                if isinstance(result, Exception):
                    self.service_logger.bind(
                        url=batch_urls[j],
                        error_type=type(result).__name__,
                        error_message=str(result),
                    ).error("Task failed during batch product parsing")
                elif isinstance(result, ProductModel):
                    all_products.append(result)

            if i + self.config_obj.parser.max_concurrency < len(urls):
                delay = self.config_obj.parser.delay_min + (
                    self.config_obj.parser.delay_max
                    - self.config_obj.parser.delay_min
                ) * (i // self.config_obj.parser.max_concurrency) / (
                    len(urls) // self.config_obj.parser.max_concurrency
                )

                self.service_logger.bind(
                    delay=delay,
                    batch_number=i // self.config_obj.parser.max_concurrency
                    + 1,
                ).debug(f"Waiting {delay:.2f} seconds between batches")

                await asyncio.sleep(delay)

        self.service_logger.bind(
            total_products=len(all_products), total_urls=len(urls)
        ).success("Batch product parsing completed")

        return all_products

    async def run_full_parsing(
        self,
        start_urls: List[str],
        parser_class: Type[BaseParser],
    ) -> List[ProductModel]:
        self.service_logger.bind(start_urls_count=len(start_urls)).info(
            "Starting full parsing cycle"
        )

        all_links = []
        for i in range(
            0, len(start_urls), self.config_obj.parser.max_concurrency
        ):
            batch_urls = start_urls[
                i : i + self.config_obj.parser.max_concurrency
            ]

            self.service_logger.bind(
                link_batch_number=i // self.config_obj.parser.max_concurrency
                + 1,
                batch_size=len(batch_urls),
            ).info("Processing links batch")

            batch_links = await self.parse_links_batch(
                batch_urls, parser_class
            )
            all_links.extend(batch_links)

            if i + self.config_obj.parser.max_concurrency < len(start_urls):
                delay = self.config_obj.parser.delay_min + (
                    self.config_obj.parser.delay_max
                    - self.config_obj.parser.delay_min
                ) * (i // self.config_obj.parser.max_concurrency) / (
                    len(start_urls) // self.config_obj.parser.max_concurrency
                )

                self.service_logger.bind(
                    delay=delay,
                    batch_number=i // self.config_obj.parser.max_concurrency
                    + 1,
                ).debug(f"Waiting {delay:.2f} seconds between batches")

                await asyncio.sleep(delay)

        unique_links = list(set(all_links))

        self.service_logger.bind(total_links_found=len(unique_links)).info(
            "Link parsing phase completed"
        )

        products = await self.parse_products_batch(unique_links, parser_class)

        self.service_logger.bind(
            total_products=len(products), total_links=len(unique_links)
        ).success("Full parsing cycle completed")

        return products

    async def close(self):
        if hasattr(self.http_client, "_session") and self.http_client._session:
            await self.http_client._session.close()

        self.service_logger.info("Parser service closed")

    def save_products(self, products: List[ProductModel]) -> List[Path]:
        self.service_logger.bind(products_count=len(products)).info(
            "Starting products saving process"
        )

        try:
            created_files = save_products_to_files(products, self.config_obj)

            self.service_logger.bind(
                products_count=len(products), files_created=len(created_files)
            ).success("Products saving completed")

            return created_files

        except Exception as e:
            self.service_logger.bind(
                products_count=len(products),
                error_type=type(e).__name__,
                error_message=str(e),
            ).error("Failed to save products")
            raise
