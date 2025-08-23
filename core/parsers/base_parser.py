from abc import ABC, abstractmethod

from shared.utils.html_parser import parse_markup


class BaseParser(ABC):
    def __init__(self, raw_html: str):
        self.html = parse_markup(raw_html)

    @abstractmethod
    def parse_html_page(self, text: str) -> str:
        pass
