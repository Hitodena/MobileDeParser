import re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union

from bs4 import Tag
from loguru import logger

from shared.exceptions.html_exceptions import HTMLParsingError
from shared.utils.html_parser import parse_markup


class BaseParser(ABC):
    def __init__(self, raw_html: str, base_url: str):

        self.raw_html = raw_html
        self.base_url = base_url.rstrip("/")
        self.html = parse_markup(raw_html)

        if not self.html:
            raise HTMLParsingError("Failed to parse HTML content")

    def extract_text_safe(self, element: Tag) -> str:
        try:
            text = element.get_text(strip=True)
            return text if text else ""
        except Exception as e:
            logger.warning(f"Failed to extract text from element: {e}")
            return ""

    def extract_attribute_safe(self, element: Tag, attribute: str) -> str:
        try:
            value = element.get(attribute)
            return str(value) if value else ""
        except Exception as e:
            logger.warning(f"Failed to extract attribute '{attribute}': {e}")
            return ""

    def parse_price(self, price_text: str) -> Optional[str]:
        try:
            price = re.findall(r"\d+", price_text)
            if price:
                return price[0] + " €"

        except Exception as e:
            logger.warning(f"Failed to parse price '{price_text}': {e}")

        return None

    def parse_mileage(self, mileage_text: str) -> Optional[str]:
        try:

            numbers = re.findall(r"\d+", mileage_text)
            if numbers:
                return numbers[0] + " км"

        except Exception as e:
            logger.warning(f"Failed to parse mileage '{mileage_text}': {e}")

        return None

    @abstractmethod
    def parse_for_links(self) -> List[str]:
        pass

    @abstractmethod
    def parse_for_data(
        self,
    ) -> Dict[str, Union[str, int, float, List[str], None]]:
        pass
