import asyncio
import random
from pathlib import Path
from typing import List

from aiohttp import (
    ClientError,
    ClientResponseError,
    ClientSession,
    ClientTimeout,
)
from loguru import logger

from shared.exceptions.request_exceptions import OutOfProxiesException
from shared.utils.generate_headers import generate_headers


class ProxyManager:
    def __init__(
        self,
        proxy_file: Path,
        timeout: int | float,
        check_url: str,
        check_retries: int,
        check_interval: int,
    ) -> None:
        self.proxy_file = proxy_file
        self.timeout = ClientTimeout(total=timeout)
        self.check_url = check_url
        self.valid_proxies: List[str] = []
        self.failed_proxies: set[str] = set()
        self._current_proxy_index = 0
        self.check_retries = check_retries
        self.check_interval = check_interval

    async def check_proxy(self, proxy_string: str) -> str | None:
        if not proxy_string:
            return None

        formatted_proxy = self.format_proxy_for_aiohttp(proxy_string)
        if not formatted_proxy:
            return None

        headers = generate_headers()
        proxy_logger = logger.bind(
            proxy=proxy_string,
            formatted_proxy=formatted_proxy,
            check_url=self.check_url,
            timeout=self.timeout.total,
            user_agent=headers.get("User-Agent", "unknown"),
        )

        try:
            async with ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    self.check_url,
                    proxy=formatted_proxy,
                    headers=headers,
                ) as response:
                    response.raise_for_status()
                    return proxy_string

        except ClientResponseError as e:
            proxy_logger.bind(
                error_type="http_error",
                status_code=e.status,
                error_class=type(e).__name__,
            ).warning(f"Proxy HTTP error: {e.status}")
            self.mark_proxy_as_failed(proxy_string)
        except ClientError as e:
            proxy_logger.bind(
                error_type="client_error", error_class=type(e).__name__
            ).warning("Proxy connection failed")
            return None
        except asyncio.TimeoutError:
            proxy_logger.bind(error_type="timeout").warning("Proxy timed out")
            return None
        except Exception as e:
            proxy_logger.bind(
                error_type="unexpected", error_class=type(e).__name__
            ).exception("Unexpected error during proxy check")
            return None

    async def load_and_verify_proxies(self) -> None:
        loader_logger = logger.bind(
            proxy_file=str(self.proxy_file),
            check_url=self.check_url,
            timeout=self.timeout.total,
        )

        if not self.proxy_file.exists():
            loader_logger.warning(
                "Proxy file not found, proceeding without proxies"
            )
            self.valid_proxies = []
            return None

        try:
            with open(self.proxy_file, "r", encoding="utf-8") as f:
                proxies = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.strip().startswith("#")
                ]
            loader_logger.bind(raw_proxy_count=len(proxies)).info(
                "Loaded proxies from file"
            )
        except IOError as e:
            loader_logger.bind(
                error_type="file_read_error", error_class=type(e).__name__
            ).exception("Failed to read proxy file")
            self.valid_proxies = []
            return

        if not proxies:
            loader_logger.warning("No proxies found in file")
            self.valid_proxies = []
            raise OutOfProxiesException("No proxies found in file")

        loader_logger.bind(raw_proxy_count=len(proxies)).info(
            "Starting proxy validation"
        )

        for attempt in range(self.check_retries):
            loader_logger.bind(
                attempt=attempt + 1,
                max_retries=self.check_retries,
                interval=self.check_interval,
            ).info("Attempting to validate proxies")

            tasks = [self.check_proxy(proxy) for proxy in proxies]
            results = await asyncio.gather(*tasks)

            self.valid_proxies = [
                proxy for proxy in results if proxy is not None
            ]
            valid_count = len(self.valid_proxies)

            if self.valid_proxies:
                loader_logger.bind(
                    valid_proxies=valid_count,
                    total_proxies=len(proxies),
                    success_rate=round((valid_count / len(proxies)) * 100, 2),
                    attempt=attempt + 1,
                ).success("Proxy validation completed successfully")

                random.shuffle(self.valid_proxies)
                loader_logger.debug("Proxies shuffled for better distribution")
                break
            elif attempt < self.check_retries - 1:
                loader_logger.bind(
                    attempt=attempt + 1,
                    max_retries=self.check_retries,
                    next_retry_in=self.check_interval,
                ).warning(
                    f"No valid proxies found on attempt {attempt + 1}, "
                    f"retrying in {self.check_interval} seconds"
                )
                await asyncio.sleep(self.check_interval)
            else:
                loader_logger.bind(
                    total_attempts=self.check_retries,
                    total_proxies=len(proxies),
                ).error("No valid proxies found after all retry attempts")
                raise OutOfProxiesException(
                    f"No valid proxies found after {self.check_retries} attempts"
                )

    async def get_next_proxy(self) -> str:
        if not self.valid_proxies:
            await self.load_and_verify_proxies()

        proxy = self.valid_proxies[self._current_proxy_index]
        self._current_proxy_index = (self._current_proxy_index + 1) % len(
            self.valid_proxies
        )
        return proxy

    async def get_random_proxy(self) -> str:
        if not self.valid_proxies:
            await self.load_and_verify_proxies()
        return random.choice(self.valid_proxies)

    async def get_proxy_for_request(
        self, is_first_request: bool = True
    ) -> str:
        proxy_type = "random" if is_first_request else "sequential"
        if is_first_request:
            proxy = await self.get_random_proxy()
        else:
            proxy = await self.get_next_proxy()

        logger.bind(
            proxy=proxy,
            proxy_type=proxy_type,
            available_proxies=len(self.valid_proxies),
            current_index=self._current_proxy_index,
        ).debug("Selected proxy for request")

        return proxy

    @property
    def has_proxies(self) -> bool:
        return len(self.valid_proxies) > 0

    @property
    def proxy_count(self) -> int:
        return len(self.valid_proxies)

    def get_total_proxies_from_file(self) -> int:
        try:
            if not self.proxy_file.exists():
                return 0
            with open(self.proxy_file, "r", encoding="utf-8") as f:
                proxies = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.strip().startswith("#")
                ]
            return len(proxies)
        except Exception:
            return 0

    async def initialize(self) -> None:
        await self.load_and_verify_proxies()

    def format_proxy_for_aiohttp(self, proxy_string: str) -> str | None:
        if not proxy_string:
            return None

        if "://" in proxy_string:
            return proxy_string

        parts = proxy_string.split(":")
        if len(parts) == 4:
            ip, port, login, password = parts
            return f"http://{login}:{password}@{ip}:{port}"

        return f"http://{proxy_string}"

    def mark_proxy_as_failed(self, proxy: str) -> None:
        if proxy:
            self.failed_proxies.add(proxy)
            if proxy in self.valid_proxies:
                self.valid_proxies.remove(proxy)
                logger.bind(proxy=proxy).warning(
                    "Proxy marked as failed and removed from pool"
                )
