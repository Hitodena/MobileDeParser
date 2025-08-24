from typing import Dict, List, Union
from urllib.parse import urljoin

from core.parsers.base_parser import BaseParser


class MobileDeRuParser(BaseParser):
    def __init__(self, raw_html: str, base_url: str):
        super().__init__(raw_html, base_url)

        # Create specific logger for MobileDe parser
        self.mobilede_logger = self.parser_logger.bind(
            parser_type="mobilede_ru",
            site_domain="mobilede.ru",
        )

    def parse_for_links(self) -> List[str]:
        links = []

        if not self.html:
            self.mobilede_logger.bind(
                error_type="no_html_content",
            ).warning("No HTML content available for link parsing")
            return links

        try:
            anchor_tags = self.html.find_all("a", class_="vehicle-data")

            for anchor in anchor_tags:
                href = self.extract_attribute_safe(anchor, "href")

                if not href or not self._is_valid_link(href):
                    continue

                resolved_url = self._resolve_url(href)

                if resolved_url and resolved_url not in links:
                    links.append(resolved_url)

        except Exception as e:
            self.mobilede_logger.bind(
                error_type=type(e).__name__,
                error_message=str(e),
            ).exception("Error during link parsing")
            return links

        self.mobilede_logger.bind(
            final_link_count=len(links),
        ).info("Link parsing completed")

        return links

    def parse_for_data(
        self,
    ) -> Dict[str, Union[str, int, float, List[str], None]]:
        try:
            links = self.parse_for_links()
            result: Dict[str, Union[str, int, float, List[str], None]] = {
                "links": links
            }

            self.mobilede_logger.bind(
                links_count=len(links),
            ).info("Data parsing completed")

            return result

        except Exception as e:
            self.mobilede_logger.bind(
                error_type=type(e).__name__,
                error_message=str(e),
            ).exception("Error during data parsing")
            return {"links": []}

    def _is_valid_link(self, href: str) -> bool:
        if not href or href.strip() == "":
            return False

        if href.lower().startswith(("javascript:", "mailto:", "tel:")):
            return False

        if href.startswith("#"):
            return False

        if href.lower().startswith("data:"):
            return False

        return True

    def _resolve_url(self, href: str) -> str:
        if href.startswith("http"):
            return href
        else:
            return urljoin(self.base_url, href)
