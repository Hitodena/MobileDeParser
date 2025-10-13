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
            anchor_tags = self.html.find_all(
                "a", class_="BaseListing_containerLink___4jHz"
            )

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
            title_element = self.html.find("h2")
            if title_element:
                title_text = self.extract_text_safe(title_element).strip()

                cleaned_title = self._clean_title_text(title_text)

                if self._extract_from_cleaned_title(cleaned_title, data):
                    self.mobilede_logger.bind(
                        category=data["category"],
                        model=data["model"],
                        original_title=title_text,
                        cleaned_title=cleaned_title,
                    ).debug(
                        "Title fields extracted from cleaned title successfully"
                    )
                else:
                    if self._extract_from_original_title(title_text, data):
                        self.mobilede_logger.bind(
                            category=data["category"],
                            model=data["model"],
                            original_title=title_text,
                        ).debug(
                            "Title fields extracted from original title successfully"
                        )
                    else:
                        self.mobilede_logger.warning(
                            "Failed to extract title fields from both cleaned and original title"
                        )
            else:
                self.mobilede_logger.warning("No title element found")

        except Exception as e:
            self.mobilede_logger.bind(
                error_type=type(e).__name__,
                error_message=str(e),
            ).warning("Failed to extract title fields")

    def _clean_title_text(self, title_text: str) -> str:
        if not title_text:
            return ""

        cut_symbols = [".", "*", "(", "[", "|", "/", "\\"]

        cut_position = len(title_text)
        for symbol in cut_symbols:
            pos = title_text.find(symbol)
            if pos != -1 and pos < cut_position:
                cut_position = pos

        plus_pos = title_text.find("+")
        if plus_pos != -1 and plus_pos < cut_position:
            cut_position = plus_pos

        dash_pos = title_text.find(" - ")
        if dash_pos != -1 and dash_pos < cut_position:
            cut_position = dash_pos

        for i in range(len(title_text) - 1):
            if (
                title_text[i] == "-"
                and title_text[i - 1] != " "
                and title_text[i + 1] != " "
            ):
                continue
            elif title_text[i] == "-" and (
                title_text[i - 1] == " " or title_text[i + 1] == " "
            ):
                if i < cut_position:
                    cut_position = i
                break

        cleaned = title_text[:cut_position].strip()

        cleaned = cleaned.rstrip()

        self.mobilede_logger.bind(
            original_title=title_text,
            cleaned_title=cleaned,
            cut_position=cut_position,
        ).debug("Title cleaned successfully")

        return cleaned

    def _extract_from_cleaned_title(
        self, cleaned_title: str, data: Dict
    ) -> bool:
        if not cleaned_title:
            return False

        words = [
            word.strip() for word in cleaned_title.split() if word.strip()
        ]

        if len(words) >= 2:
            data["category"] = words[0]
            data["model"] = words[1]
            return True
        elif len(words) == 1:
            data["category"] = words[0]
            data["model"] = ""
            return True

        return False

    def _extract_from_original_title(
        self, title_text: str, data: Dict
    ) -> bool:
        if not title_text:
            return False

        words = [word.strip() for word in title_text.split() if word.strip()]

        if len(words) >= 2:
            data["category"] = words[0]
            data["model"] = words[1]
            return True
        elif len(words) == 1:
            data["category"] = words[0]
            data["model"] = ""
            return True

        return False

    def _extract_technical_fields(self, data: Dict) -> None:
        try:
            tech_article = self.html.find(
                "article", {"data-testid": "vip-technical-data-box"}
            )

            if isinstance(tech_article, Tag):
                dt_elements = tech_article.find_all("dt")
                for dt_element in dt_elements:
                    if not isinstance(dt_element, Tag):
                        continue

                    dd_element = dt_element.find_next_sibling("dd")
                    if not isinstance(dd_element, Tag):
                        continue

                    label_text = self.extract_text_safe(dt_element).strip()
                    value_text = self.extract_text_safe(dd_element).strip()
                    data_testid = dt_element.get("data-testid", "")

                    if (
                        data_testid == "firstRegistration-item"
                        or "Первая регистрация" in label_text
                    ) and "/" in value_text:
                        year = value_text.split("/")[-1].strip()
                        if year:
                            data["year_of_release"] = year
                        continue

                    if data_testid == "mileage-item" or "Пробег" in label_text:
                        mileage = self.parse_only_numbers(value_text)
                        if mileage:
                            data["mileage"] = mileage
                        continue

                    if (
                        data_testid == "transmission-item"
                        or "Трансмиссия" in label_text
                        or "Коробка передач" in label_text
                    ):
                        data["transmission"] = value_text
                        continue

                    if data_testid == "fuel-item" or "Топливо" in label_text:
                        data["fuel"] = value_text
                        continue

                    if "Объем двигателя" in label_text:
                        volume = self.parse_only_numbers(value_text)
                        if volume:
                            data["engine_volume"] = volume

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
            tech_article = self.html.find(
                "article", {"data-testid": "vip-technical-data-box"}
            )
            if isinstance(tech_article, Tag):
                dt_elements = tech_article.find_all("dt")
                for dt_element in dt_elements:
                    if not isinstance(dt_element, Tag):
                        continue

                    dd_element = dt_element.find_next_sibling("dd")
                    if not isinstance(dd_element, Tag):
                        continue

                    label_text = self.extract_text_safe(dt_element).strip()
                    value_text = self.extract_text_safe(dd_element).strip()
                    data_testid = dt_element.get("data-testid", "")

                    if (
                        data_testid == "category-item"
                        or "Категория" in label_text
                    ):
                        category = value_text.strip()
                        if category:
                            data["body"] = category
                        continue

                    if data_testid == "color-item" or "Цвет" in label_text:
                        color = value_text.strip()
                        if color:
                            data["color"] = color
                        continue

                    if (
                        data_testid == "doorCount-item"
                        or "Число дверей" in label_text
                    ):
                        door_count = value_text.strip()
                        if door_count:
                            data["door_count"] = door_count
                        continue

                    if (
                        data_testid == "numSeats-item"
                        or "Количество мест" in label_text
                    ):
                        seat_count = value_text.strip()
                        if seat_count:
                            data["seat_count"] = seat_count
                        continue

                    if (
                        data_testid == "numberOfPreviousOwners-item"
                        or "Количество владельцев" in label_text
                    ):
                        owner_count = value_text.strip()
                        if owner_count:
                            data["owner_count"] = owner_count
                        continue

            additional_fields_found = any(
                [
                    data["color"],
                    data["door_count"],
                    data["seat_count"],
                    data["owner_count"],
                    data["body"],
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
            price_element = self.html.find(
                "div",
                class_="MainPriceArea_mainPrice__xCkfs typography_headlineLarge__jywu0",
            )
            if price_element:
                price_text = self.extract_text_safe(price_element)
                price = self.parse_only_numbers(price_text)
                if price:
                    try:
                        price_euro = int(price)
                        price_rub = int(
                            price_euro * config.calculation.currency_exchange
                        )
                        data["price"] = str(price_rub)

                        self.mobilede_logger.bind(
                            extracted_price_euro=price_euro,
                            converted_price_rub=price_rub,
                            exchange_rate=config.calculation.currency_exchange,
                            original_text=price_text,
                        ).debug("Price extracted and converted successfully")
                    except (ValueError, AttributeError) as e:

                        data["price"] = price
                        self.mobilede_logger.bind(
                            extracted_price=price,
                            original_text=price_text,
                            conversion_error=str(e),
                        ).warning("Price extracted but conversion failed")
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
            image_data_element = self.html.find(
                "div", {"data-testid": "image-gallery"}
            )
            img_elements = image_data_element.find_all("img")  # type: ignore
            collected_urls: List[str] = []

            for img in img_elements:
                if not isinstance(img, Tag):
                    continue
                src_value = self.extract_attribute_safe(img, "src")
                if src_value and src_value not in collected_urls:
                    collected_urls.append(src_value)
                    continue

            if collected_urls:
                data["images"] = collected_urls
                self.mobilede_logger.bind(
                    image_count=len(collected_urls),
                ).debug("Images extracted successfully (img elements)")
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
                if link_url.startswith(
                    "https://home.mobile.de/home/redirect.html"
                ):
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
                "ul", {"data-testid": "vip-features-list"}
            )
            features_list: List[str] = []
            for element in feature_elements:
                if not isinstance(element, Tag):
                    continue
                li_elements = element.find_all("li")
                for li in li_elements:
                    if not isinstance(li, Tag):
                        continue
                    item_text = self.extract_text_safe(li).strip()
                    if item_text:
                        features_list.append(item_text)

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
