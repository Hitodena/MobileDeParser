import json
from typing import Dict, List, Optional
from urllib.parse import urljoin

from bs4.element import Tag

from core.models.product_model import ProductModel
from core.parsers.base_parser import BaseParser
from shared.config.config import config


class MobileDeRuParser(BaseParser):
    def __init__(self, raw_html: str, base_url: str, url: str):
        if not url.startswith("https://mobile.de/ru/") and not url.startswith(
            "https://www.mobile.de/ru/"
        ):
            raise ValueError(
                f"Неверный формат URL. Ожидается URL начинающийся с 'https://mobile.de/ru/', получен: {url}"
            )

        super().__init__(raw_html, base_url, url)

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

        if links:
            self.mobilede_logger.bind(
                final_link_count=len(links),
            ).info("Link parsing completed")
        else:
            self.mobilede_logger.warning("No links found during parsing")

        return links

    def parse_for_data(
        self,
    ) -> Optional[ProductModel]:
        data = {
            "category": "",
            "model": "",
            "year_of_release": "",
            "mileage": "",
            "transmission": "",
            "fuel": "",
            "engine_volume": "",
            "body": "",
            "color": "",
            "door_count": "",
            "seat_count": "",
            "owner_count": "",
            "price": "",
            "images": [],
            "url": self.url,
            "dealer": "",
            "text": [],
            "sku": self.url.split("/")[-1].split(".")[0],
        }

        if not self.html:
            self.mobilede_logger.bind(
                error_type="no_html_content",
            ).warning("No HTML content available for data parsing")
            data["config"] = config
            return ProductModel(**data)

        try:
            self._extract_title_fields(data)

            self._extract_technical_fields(data)

            self._extract_additional_fields(data)

            self._extract_price(data)

            self._extract_images(data)

            self._extract_dealer_link(data)

            self._extract_feautres(data)

        except Exception as e:
            self.mobilede_logger.bind(
                error_type=type(e).__name__,
                error_message=str(e),
            ).exception("Error during data parsing")

        self.mobilede_logger.bind(
            extracted_fields=list(data.keys()),
        ).success("Data parsing completed")

        data["config"] = config
        return ProductModel(**data)

    def _extract_title_fields(self, data: Dict) -> None:
        try:
            title_element = self.html.find("h1")
            if title_element:
                title_text = self.extract_text_safe(title_element).strip()
                title_words = title_text.split()
                if len(title_words) >= 2:
                    data["category"] = title_words[0]
                    data["model"] = title_words[1]

                    self.mobilede_logger.bind(
                        category=data["category"],
                        model=data["model"],
                        full_title=title_text,
                    ).debug("Title fields extracted successfully")
                else:
                    self.mobilede_logger.warning(
                        "Title element found but insufficient words for parsing"
                    )
            else:
                self.mobilede_logger.warning("No title element found")

        except Exception as e:
            self.mobilede_logger.bind(
                error_type=type(e).__name__,
                error_message=str(e),
            ).warning("Failed to extract title fields")

    def _extract_technical_fields(self, data: Dict) -> None:
        try:
            tech_rows = self.html.find_all("div", class_="g-row")

            for row in tech_rows:
                if isinstance(row, Tag):
                    span_elements = row.find_all("span")
                    if len(span_elements) >= 2:
                        label = self.extract_text_safe(
                            span_elements[0]
                        ).strip()
                        value = self.extract_text_safe(
                            span_elements[1]
                        ).strip()

                        if "Первая регистрация" in label and "/" in value:
                            year = value.split("/")[-1].strip()
                            if year:
                                data["year_of_release"] = year

                        elif "Пробег" in label:
                            mileage = self.parse_only_numbers(value)
                            if mileage:
                                data["mileage"] = mileage

                        elif "Коробка передач" in label:
                            data["transmission"] = value

                        elif "Топливо" in label:
                            data["fuel"] = value

                        elif "Объем двигателя" in label:
                            volume = self.parse_only_numbers(value)
                            if volume:
                                data["engine_volume"] = volume

            # Проверяем, были ли найдены технические поля
            tech_fields_found = any(
                [
                    data["year_of_release"],
                    data["mileage"],
                    data["transmission"],
                    data["fuel"],
                    data["engine_volume"],
                ]
            )

            if tech_fields_found:
                self.mobilede_logger.debug(
                    "Technical fields extraction completed"
                )
            else:
                self.mobilede_logger.warning("No technical fields found")

        except Exception as e:
            self.mobilede_logger.bind(
                error_type=type(e).__name__,
                error_message=str(e),
            ).warning("Failed to extract technical fields")

    def _extract_additional_fields(self, data: Dict) -> None:
        try:
            all_rows = self.html.find_all("div", class_="g-row")

            for row in all_rows:
                if isinstance(row, Tag):
                    span_elements = row.find_all("span")
                    if len(span_elements) >= 2:
                        label = self.extract_text_safe(
                            span_elements[0]
                        ).strip()
                        value = self.extract_text_safe(
                            span_elements[1]
                        ).strip()

                        if "Категория" in label:
                            data["body"] = value

                        elif "Цвет" in label:
                            data["color"] = value

                        elif "дверей" in label or "дверь" in label:
                            data["door_count"] = value

                        elif "мест" in label or "Количество мест" in label:
                            data["seat_count"] = value

                        elif "владельцев" in label:
                            data["owner_count"] = value

            # Проверяем, были ли найдены дополнительные поля
            additional_fields_found = any(
                [
                    data["body"],
                    data["color"],
                    data["door_count"],
                    data["seat_count"],
                    data["owner_count"],
                ]
            )

            if additional_fields_found:
                self.mobilede_logger.debug(
                    "Additional fields extraction completed"
                )
            else:
                self.mobilede_logger.warning("No additional fields found")

        except Exception as e:
            self.mobilede_logger.bind(
                error_type=type(e).__name__,
                error_message=str(e),
            ).warning("Failed to extract additional fields")

    def _extract_price(self, data: Dict) -> None:
        try:
            price_element = self.html.find("p", class_="h3 u-text-bold")
            if price_element:
                price_text = self.extract_text_safe(price_element)
                price = self.parse_only_numbers(price_text)
                if price:
                    data["price"] = price

                    self.mobilede_logger.bind(
                        extracted_price=price,
                        original_text=price_text,
                    ).debug("Price extracted successfully")
                else:
                    self.mobilede_logger.warning(
                        "Price element found but could not parse price"
                    )
            else:
                self.mobilede_logger.warning("No price element found")

        except Exception as e:
            self.mobilede_logger.bind(
                error_type=type(e).__name__,
                error_message=str(e),
            ).warning("Failed to extract price")

    def _extract_images(self, data: Dict) -> None:
        try:
            image_data_element = self.html.find("div", class_="js-image-data")
            if image_data_element:
                images_attr = self.extract_attribute_safe(
                    image_data_element, "data-images"
                )
                if images_attr:
                    try:
                        images_list = json.loads(images_attr)
                        if isinstance(images_list, list):
                            data["images"] = images_list

                            self.mobilede_logger.bind(
                                image_count=len(images_list),
                            ).debug("Images extracted successfully")
                        else:
                            self.mobilede_logger.warning(
                                "Images data is not a list"
                            )
                    except json.JSONDecodeError as e:
                        self.mobilede_logger.bind(
                            error_message=str(e),
                        ).warning("Failed to parse images JSON")
                else:
                    self.mobilede_logger.warning(
                        "No images data attribute found"
                    )
            else:
                self.mobilede_logger.warning("No images element found")

        except Exception as e:
            self.mobilede_logger.bind(
                error_type=type(e).__name__,
                error_message=str(e),
            ).warning("Failed to extract images")

    def _extract_dealer_link(self, data: Dict) -> None:
        try:
            links = self.html.find_all("a", href=True)
            dealer_found = False
            for link in links:
                link_url = self.extract_attribute_safe(link, "href")
                if link_url.startswith("https://home.mobile.de/"):
                    data["dealer"] = link_url
                    self.mobilede_logger.bind(
                        dealer=data["dealer"],
                    ).debug("Dealer link extracted successfully")
                    dealer_found = True
                    break

            if not dealer_found:
                self.mobilede_logger.warning("No dealer link found")

        except Exception as e:
            self.mobilede_logger.bind(
                error_type=type(e).__name__,
                error_message=str(e),
            ).warning("Failed to extract dealer link")

    def _extract_feautres(self, data: Dict) -> None:
        try:
            feature_elements = self.html.find_all(
                "p", class_="bullet-point-text"
            )
            features_list = []
            for element in feature_elements:
                if isinstance(element, Tag):
                    feature_text = self.extract_text_safe(element).strip()
                    if feature_text:
                        features_list.append(feature_text)

            if features_list:
                data["text"] = features_list
                self.mobilede_logger.bind(
                    features_count=len(features_list),
                ).debug("Features extracted successfully")
            else:
                self.mobilede_logger.warning("No features found")

        except Exception as e:
            self.mobilede_logger.bind(
                error_type=type(e).__name__,
                error_message=str(e),
            ).warning("Failed to extract features")

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
