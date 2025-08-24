import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from bs4.element import PageElement
from loguru import logger

from shared.utils.html_parser import parse_markup


class BaseParser(ABC):
    def __init__(self, raw_html: str, base_url: str):
        self.raw_html = raw_html
        self.base_url = base_url.rstrip("/")

        # Create contextual logger for parser initialization
        self.parser_logger = logger.bind(
            parser_class=self.__class__.__name__,
            base_url=self.base_url,
        )

        self.html = parse_markup(raw_html)

        if not self.html:
            self.parser_logger.bind(
                error_type="html_parsing_failed",
            ).error("Failed to parse HTML content")
            raise ValueError("Failed to parse HTML content")

    def extract_text_safe(self, element: PageElement) -> str:
        try:
            text = element.get_text(strip=True)
            return text if text else ""
        except Exception as e:
            self.parser_logger.bind(
                error_type=type(e).__name__,
                error_message=str(e),
            ).warning("Failed to extract text from element")
            return ""

    def extract_attribute_safe(self, element: Any, attribute: str) -> str:
        try:
            if hasattr(element, "get"):
                value = element.get(attribute)
                result = str(value) if value else ""

                self.parser_logger.bind(
                    attribute_name=attribute,
                    attribute_value=result,
                    has_value=bool(result),
                ).debug("Attribute extraction completed")

                return result
            else:
                return ""
        except (AttributeError, TypeError) as e:
            self.parser_logger.bind(
                error_type=type(e).__name__,
                error_message=str(e),
            ).warning("Failed to extract attribute")
            return ""

    def parse_price(self, price_text: str) -> Optional[str]:
        try:
            price = re.findall(r"\d+", price_text)
            if price:
                result = price[0]
                self.parser_logger.bind(
                    extracted_price=result,
                ).debug("Price parsing completed")
                return result
            return None
        except Exception as e:
            self.parser_logger.bind(
                error_type=type(e).__name__,
                error_message=str(e),
            ).warning("Failed to parse price")
            return None

    def parse_mileage(self, mileage_text: str) -> Optional[str]:
        try:
            numbers = re.findall(r"\d+", mileage_text)
            if numbers:
                result = numbers[0]
                self.parser_logger.bind(
                    extracted_mileage=result,
                ).debug("Mileage parsing completed")
                return result
            return None
        except Exception as e:
            self.parser_logger.bind(
                error_type=type(e).__name__,
                error_message=str(e),
            ).warning("Failed to parse mileage")
            return None

    def set_html(self, raw_html: str) -> None:
        self.raw_html = raw_html
        self.html = parse_markup(raw_html)

        if not self.html:
            self.parser_logger.bind(
                error_type="html_parsing_failed",
            ).warning("Failed to parse new HTML content")

    @abstractmethod
    def parse_for_links(self) -> List[str]:
        pass

    @abstractmethod
    def parse_for_data(
        self,
    ) -> Dict[str, Union[str, int, float, List[str], None]]:
        pass
