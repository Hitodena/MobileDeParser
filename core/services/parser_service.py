import asyncio
from pathlib import Path
from typing import Callable, List, Optional, Tuple, Type

from loguru import logger

from core.models.product_model import ProductModel
from core.parsers.base_parser import BaseParser
from shared.config.config_model import ConfigModel
from shared.exceptions.request_exceptions import OutOfProxiesException
from shared.services.database_service import DatabaseService
from shared.services.http_client import HTTPClient
from shared.utils.proxy_manager import ProxyManager
from shared.utils.storage_management import (
    save_products_from_database,
)


class ParserService:
    def __init__(self, config_obj: ConfigModel):
        self.proxy_manager = ProxyManager(
            check_retries=config_obj.parser.proxy_check_retries,
            check_interval=config_obj.parser.proxy_check_interval,
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

        self.database_service = DatabaseService(config_obj)

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

    async def check_and_refresh_proxies(self) -> bool:
        try:
            self.service_logger.info(
                "Checking and refreshing proxies from file"
            )

            old_proxy_count = self.proxy_manager.proxy_count

            await self.proxy_manager.load_and_verify_proxies()

            new_proxy_count = self.proxy_manager.proxy_count

            if new_proxy_count > 0:
                self.service_logger.bind(
                    old_count=old_proxy_count,
                    new_count=new_proxy_count,
                    added_proxies=new_proxy_count - old_proxy_count,
                ).success("Proxies refreshed successfully")
                return True
            else:
                self.service_logger.bind(
                    old_count=old_proxy_count, new_count=new_proxy_count
                ).warning("No working proxies found after refresh")
                return False

        except Exception as e:
            self.service_logger.bind(
                error_type=type(e).__name__, error_message=str(e)
            ).error("Failed to refresh proxies")
            return False

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

    def _update_search_progress(
        self, processed_start_urls: int, total_start_urls: int
    ):
        self._update_progress(processed_start_urls, 0, total_start_urls)

    def _update_parsing_progress(
        self,
        processed_products: int,
        found_products: int,
        total_links_to_parse: int,
    ):
        self._update_progress(
            processed_products, found_products, total_links_to_parse
        )

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

            except OutOfProxiesException as e:
                self.service_logger.bind(
                    url=url, error_type=type(e).__name__, error_message=str(e)
                ).error("No working proxies available")
                raise
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

        filtered_links = await self._filter_links_by_existing_skus(
            unique_links
        )

        self.service_logger.bind(
            total_links=len(all_links),
            unique_links=len(unique_links),
            filtered_links=len(filtered_links),
            batch_size=len(urls),
        ).success("Batch link parsing completed with SKU filtering")

        return filtered_links

    async def _filter_links_by_existing_skus(
        self, links: List[str]
    ) -> List[str]:
        try:
            existing_skus = self.database_service.get_all_existing_skus()
            existing_count = len(existing_skus)

            self.service_logger.bind(
                total_links=len(links), existing_skus_count=existing_count
            ).info("Starting SKU-based link filtering")

            filtered_links = []
            skipped_count = 0

            for link in links:
                sku = link.split("?id=")[1].split("&")[0]

                if not sku:
                    self.service_logger.bind(url=link).warning(
                        "Link skipped - no SKU extracted"
                    )
                    skipped_count += 1
                    continue

                if sku in existing_skus:
                    self.service_logger.bind(url=link, sku=sku).debug(
                        "Link skipped - SKU already exists in database"
                    )
                    skipped_count += 1
                    continue

                filtered_links.append(link)

            self.service_logger.bind(
                total_links=len(links),
                filtered_links=len(filtered_links),
                skipped_links=skipped_count,
                existing_skus_count=existing_count,
            ).info("SKU-based link filtering completed")

            if len(filtered_links) == 0 and len(links) > 0:
                self.service_logger.warning(
                    "All links were filtered out - no new products to parse"
                )
            elif len(filtered_links) < len(links):
                self.service_logger.info(
                    f"Filtered out {len(links) - len(filtered_links)} existing products"
                )

            return filtered_links

        except Exception as e:
            self.service_logger.bind(
                error_type=type(e).__name__,
                error_message=str(e),
            ).error(
                "Failed to filter links by existing SKUs, returning all links"
            )
            return links

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

            except OutOfProxiesException as e:
                self.service_logger.bind(
                    url=url, error_type=type(e).__name__, error_message=str(e)
                ).error("No working proxies available")
                raise
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
        if not urls:
            self.service_logger.info("No URLs provided for product parsing")
            return []

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

            self._update_parsing_progress(
                processed_urls, len(all_products), len(urls)
            )

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

                except OutOfProxiesException as e:
                    error_msg = f"No working proxies available: {str(e)}"
                    parsing_errors.append(error_msg)
                    self.service_logger.bind(
                        batch_urls=batch_urls,
                        error_type=type(e).__name__,
                        error_message=str(e),
                    ).error("No working proxies available, stopping parsing")
                    raise
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

        self._update_progress(
            processed_urls=0,
            found_products=0,
            total_links_found=len(unique_links),
        )

        products = []
        if unique_links:
            try:
                products = await self.parse_products_batch(
                    unique_links, parser_class
                )
            except OutOfProxiesException as e:
                error_msg = f"No working proxies available: {str(e)}"
                parsing_errors.append(error_msg)
                self.service_logger.bind(
                    error_type=type(e).__name__,
                    error_message=str(e),
                ).error("No working proxies available, stopping parsing")
                raise
            except Exception as e:
                error_msg = f"Failed to parse products: {str(e)}"
                parsing_errors.append(error_msg)
                self.service_logger.bind(
                    error_type=type(e).__name__,
                    error_message=str(e),
                ).error("Product parsing failed")
        else:
            self._update_progress(
                processed_urls=0,
                found_products=0,
                total_links_found=0,
            )
            self.service_logger.info(
                "No new links to parse - all products already exist in database"
            )

        self.service_logger.bind(
            total_products=len(products),
            total_links=len(unique_links),
            total_errors=len(parsing_errors),
        ).success("Full parsing cycle completed")

        saved_count = 0
        try:
            new_count, duplicates_count = (
                self.database_service.save_products_batch(products)
            )
            saved_count = new_count
            self.service_logger.bind(
                total_products=len(products),
                new_products=new_count,
                duplicates=duplicates_count,
            ).info("Products saved to database")

            if self.config_obj.ai.enabled:
                try:
                    await self._process_new_products_with_ai()
                except Exception as ai_error:
                    self.service_logger.bind(
                        error_type=type(ai_error).__name__,
                        error_message=str(ai_error),
                    ).error(
                        "AI processing failed, continuing without AI enhancement"
                    )

        except Exception as e:
            error_msg = f"Failed to save products to database: {str(e)}"
            parsing_errors.append(error_msg)
            self.service_logger.bind(
                error_type=type(e).__name__,
                error_message=str(e),
            ).error("Failed to save products to database")

        if parsing_errors:
            self.service_logger.bind(
                error_count=len(parsing_errors), errors=parsing_errors
            ).warning("Parsing completed with errors")

        return products, None, saved_count

    async def _process_new_products_with_ai(self):
        from shared.services.openrouter_service import OpenRouterService

        db_products_for_ai = self.database_service.get_all_products(
            only_marked_for_ai=True
        )

        if not db_products_for_ai:
            self.service_logger.info("No products marked for AI processing")
            return

        self.service_logger.bind(products_count=len(db_products_for_ai)).info(
            "Found products marked for AI processing"
        )

        all_processing_skus = set()
        for product in db_products_for_ai:
            sku = product.get(self.config_obj.database.sku, "")
            if sku:
                all_processing_skus.add(sku)

        self.service_logger.bind(total_skus=len(all_processing_skus)).info(
            "Collected SKUs for AI processing"
        )

        http_client = HTTPClient(
            self.proxy_manager,
            self.config_obj.ai.timeout,
            self.config_obj.ai.retries,
            self.config_obj.parser.delay_min,
            self.config_obj.parser.delay_max,
        )

        ai_service = OpenRouterService(
            http_client,
            self.config_obj.ai.api_key,
            self.config_obj.ai.model,
            db_products_for_ai,
            self.config_obj.ai.prompt,
            self.config_obj,
        )

        ai_answer, failed_skus = await ai_service.batch_response()

        self.service_logger.bind(
            results_count=len(ai_answer), failed_skus_count=len(failed_skus)
        ).info("AI processing completed")

        processed_count = 0
        failed_count = 0
        successfully_processed_skus = set()

        id_to_product = {}

        for product in db_products_for_ai:
            product_id = product.get(self.config_obj.database.id)
            if product_id:
                id_to_product[product_id] = product

        for ai_item in ai_answer:
            if not isinstance(ai_item, dict):
                self.service_logger.warning("Invalid AI item format, skipping")
                continue

            ai_id = ai_item.get("id")
            enhanced_text = ai_item.get("text", "")

            if (
                ai_id is not None
                and ai_id in id_to_product and enhanced_text
            ):
                product = id_to_product[ai_id]
                sku = product.get(self.config_obj.database.sku, "")

                if sku:
                    original_prefix = self.config_obj.ai.out_prefix
                    new_value = original_prefix + enhanced_text

                    field_success = self.database_service.update_product_field(
                        sku, self.config_obj.ai.out_field, new_value
                    )

                    marker_success = (
                        self.database_service.update_marked_for_ai(sku, False)
                    )

                    if field_success and marker_success:
                        processed_count += 1
                        successfully_processed_skus.add(sku)
                        self.service_logger.bind(sku=sku).debug(
                            "Successfully processed product"
                        )
                    else:
                        failed_count += 1
                        self.service_logger.bind(
                            sku=sku,
                            field_success=field_success,
                            marker_success=marker_success,
                        ).warning("Failed to update product in database")
            else:
                self.service_logger.bind(
                    ai_idx=ai_id,
                    has_text=bool(enhanced_text),
                    max_idx=len(db_products_for_ai) - 1,
                ).warning("Invalid AI result item")

        reset_count = 0
        for failed_sku in failed_skus:
            if failed_sku not in successfully_processed_skus:
                if self.database_service.update_marked_for_ai(
                    failed_sku, True
                ):
                    reset_count += 1

        if failed_skus:
            self.service_logger.bind(reset_count=reset_count).warning(
                "Reset AI marker for failed products"
            )

        missing_skus = (
            all_processing_skus
            - successfully_processed_skus
            - set(failed_skus)
        )
        if missing_skus:
            self.service_logger.bind(
                missing_count=len(missing_skus),
                missing_skus=list(missing_skus)[:10],
            ).warning(
                "Some products were sent but not returned in results (showing first 10)"
            )
            for missing_sku in missing_skus:
                if self.database_service.update_marked_for_ai(
                    missing_sku, True
                ):
                    reset_count += 1

        self.service_logger.bind(
            processed=processed_count,
            failed=failed_count,
            reset_markers=reset_count,
            total_sent=len(all_processing_skus),
        ).success(
            f"AI enhancement completed: {processed_count} updated, {failed_count} failed, {reset_count} markers reset"
        )

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
            new_count, duplicates_count = (
                self.database_service.save_products_batch(products)
            )

            self.service_logger.bind(
                total_products=len(products),
                new_products=new_count,
                duplicates=duplicates_count,
            ).info("Database filtering completed")

            return None

        except Exception as e:
            self.service_logger.bind(
                products_count=len(products),
                error_type=type(e).__name__,
                error_message=str(e),
            ).error("Failed to save products")
            raise

    def get_database_stats(self) -> dict:
        try:
            total_count = self.database_service.get_products_count()
            return {
                "total_products": total_count,
                "database_path": self.database_service.db_path,
            }
        except Exception as e:
            self.service_logger.bind(
                error_type=type(e).__name__, error_message=str(e)
            ).error("Failed to get database stats")
            return {"error": str(e)}

    def create_sql_dump(self, output_path: str) -> bool:
        try:
            success = self.database_service.create_sql_dump(output_path)
            if success:
                self.service_logger.bind(output_path=output_path).info(
                    "SQL dump created"
                )
            else:
                self.service_logger.bind(output_path=output_path).error(
                    "Failed to create SQL dump"
                )
            return success
        except Exception as e:
            self.service_logger.bind(
                output_path=output_path,
                error_type=type(e).__name__,
                error_message=str(e),
            ).error("Error creating SQL dump")
            return False

    async def export_from_database(self) -> Optional[Tuple[Path, int]]:
        try:
            self.service_logger.info("Starting database export")

            result = await save_products_from_database(self.config_obj)

            if result:
                archive_path, saved_count = result
                self.service_logger.bind(
                    exported_products=saved_count,
                    archive_path=archive_path,
                ).success("Database export completed")
                return archive_path, saved_count

            return None

        except Exception as e:
            self.service_logger.bind(
                error_type=type(e).__name__, error_message=str(e)
            ).error("Failed to export from database")
            return None
