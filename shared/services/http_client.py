import asyncio
from typing import Dict, Optional

from aiohttp import (
    ClientError,
    ClientResponseError,
    ClientSession,
    ClientTimeout,
)
from loguru import logger

from shared.exceptions.request_exceptions import RequestException
from shared.utils.generate_headers import generate_headers
from shared.utils.proxy_manager import ProxyManager


class HTTPClient:
    def __init__(
        self, proxy_manager: ProxyManager, timeout: int | float, retries: int
    ) -> None:
        self.proxy_manager = proxy_manager
        self._session: Optional[ClientSession] = None
        self.timeout = ClientTimeout(total=timeout)
        self.retries = retries

    def _get_headers(self) -> Dict[str, str]:
        return generate_headers()

    def _create_session(self) -> ClientSession:
        return ClientSession(
            headers=self._get_headers(),
            timeout=self.timeout,
        )

    async def get_content(self, url: str) -> str:
        request_logger = logger.bind(
            url=url,
            max_retries=self.retries,
            available_proxies=(self.proxy_manager.proxy_count),
        )

        last_exception = None
        request_logger.info("Starting request")

        for attempt in range(self.retries + 1):
            proxy = None
            if self.proxy_manager and self.proxy_manager.has_proxies:
                is_first_attempt = attempt == 0
                proxy = self.proxy_manager.get_proxy_for_request(
                    is_first_attempt
                )

            attempt_logger = request_logger.bind(
                attempt=attempt + 1,
                proxy=proxy,
                proxy_type="random" if attempt == 0 else "sequential",
            )

            attempt_logger.debug("Making request attempt")

            try:
                session_headers = self._get_headers()
                attempt_logger = attempt_logger.bind(
                    user_agent=session_headers.get("User-Agent", "unknown")
                )

                async with self._create_session() as session:
                    async with session.get(url, proxy=proxy) as response:
                        response.raise_for_status()
                        content = await response.text()

                        attempt_logger.bind(
                            status_code=response.status,
                            content_length=len(content),
                        ).success("Request completed successfully")

                        return content

            except ClientResponseError as e:
                last_exception = RequestException(
                    f"HTTP {e.status}: {e.message}"
                )
                attempt_logger.bind(
                    status_code=e.status,
                    error_message=e.message,
                    error_type="http_error",
                ).warning("HTTP error occurred")

                # Don't retry client errors (4xx) except rate limiting
                if 400 <= e.status < 500 and e.status != 429:
                    attempt_logger.bind(reason="client_error_no_retry").info(
                        "Stopping retries"
                    )
                    break

            except ClientError as e:
                last_exception = RequestException(f"Network error: {e}")
                attempt_logger.bind(
                    error_type="network_error", error_class=type(e).__name__
                ).warning("Network error occurred")

            except Exception as e:
                last_exception = RequestException(f"Unexpected error: {e}")
                attempt_logger.bind(
                    error_type="unexpected_error", error_class=type(e).__name__
                ).warning("Unexpected error occurred")

            # Retry logic
            if attempt < self.retries:
                wait_time = min(2**attempt, 5)
                attempt_logger.bind(wait_time=wait_time).info(
                    "Retrying request"
                )
                await asyncio.sleep(wait_time)

        request_logger.bind(
            final_exception_type=(
                type(last_exception).__name__ if last_exception else "unknown"
            )
        ).error("All retry attempts failed")

        raise last_exception or RequestException("All attempts failed")
