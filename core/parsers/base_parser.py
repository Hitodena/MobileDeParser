import re
from abc import ABC, abstractmethod
from typing import Any, List, Optional

from bs4.element import PageElement
from loguru import logger

from core.models.product_model import ProductModel
from shared.utils.html_parser import parse_markup


class BaseParser(ABC):
    def __init__(self, raw_html: str, base_url: str, url):
        self.raw_html = raw_html
        self.base_url = base_url.rstrip("/")
        self.url = url.rstrip("/")

        self.parser_logger = logger.bind(
            parser_class=self.__class__.__name__,
            url=self.url,
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

    def  extract_attribute_safe(self, element: Any, attribute: str) -> str:
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
                result = "".join(price)
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

    def parse_only_numbers(self, text: str) -> Optional[str]:
        try:
            if not text:
                return None

            cleaned_text = self.clean_text(text)

            numbers = re.findall(r"\d+", cleaned_text)
            if numbers:
                result = "".join(numbers)
                self.parser_logger.bind(
                    original_text=text,
                    cleaned_text=cleaned_text,
                    extracted_numbers=result,
                ).debug("Numbers extracted successfully")
                return result
            return None
        except Exception as e:
            self.parser_logger.bind(
                error_type=type(e).__name__,
                error_message=str(e),
                original_text=text,
            ).warning("Failed to parse numbers")
            return None

    def clean_text(self, text: str) -> str:
        if not text:
            return ""

        replacements = {
            "\xa0": " ",
            "\u200b": "",
            "\u200c": "",
            "\u200d": "",
            "\u2060": "",
            "\u202f": " ",
            "\u2028": " ",
            "\u2029": " ",
            "\t": " ",
            "\n": " ",
            "\r": " ",
        }

        cleaned = text
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)

        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    def extract_year_from_date(self, date_str: str) -> str:
        if not date_str:
            return ""

        cleaned_date = self.clean_text(date_str)

        if "/" in cleaned_date:
            parts = cleaned_date.split("/")
            if len(parts) >= 2:
                year = parts[-1]
                return year

        self.parser_logger.bind(
            original_date=date_str,
            cleaned_date=cleaned_date,
        ).warning("Could not extract year from date")
        return cleaned_date

    def clean_number(self, number: str) -> str:
        if not number:
            return ""

        cleaned = self.clean_text(number)
        cleaned = re.sub(r"[^\d.,]", "", cleaned)
        cleaned = cleaned.replace(",", ".")

        parts = cleaned.split(".")
        if len(parts) > 2:
            cleaned = parts[0] + "." + "".join(parts[1:])

        return cleaned.strip()

    def set_html(self, raw_html: str) -> None:
        self.raw_html = raw_html
        self.html = parse_markup(raw_html)

        if not self.html:
            self.parser_logger.bind(
                error_type="html_parsing_failed",
            ).warning("Failed to parse new HTML content")

    def set_url(self, url: str) -> None:
        self.url = url.rstrip("/")

    @abstractmethod
    def parse_for_links(self) -> List[str]:
        pass

    @abstractmethod
    def parse_for_data(
        self,
    ) -> Optional[ProductModel]:
        pass
