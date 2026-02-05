from typing import Dict, List, Optional

from loguru import logger
from pydantic import BaseModel, Field, computed_field

from shared.config.config_model import ConfigModel
from shared.exceptions.model_exceptions import ModelExclusionError


class ProductModel(BaseModel):
    category: str = Field(alias="Category")
    model: str = Field(alias="Characteristics: модель")
    year_of_release: str = Field(alias="Characteristics: год выпуска")
    mileage: str = Field(alias="Characteristics: пробег")
    transmission: str = Field(alias="Characteristics: коробка")
    fuel: str = Field(alias="Characteristics: топливо")
    engine_volume: str = Field(alias="Characteristics: объем, см3")
    body: str = Field(alias="Characteristics: кузов")
    color: str = Field(alias="Characteristics: цвет")
    door_count: str = Field(alias="Characteristics: к-во дверей")
    seat_count: str = Field(alias="Characteristics: к-во мест")
    owner_count: Optional[str] = Field(
        alias="Characteristics: к-во владельцев", default=None
    )
    power: Optional[str] = Field(
        alias="Characteristics: мощность", default=None
    )
    price: str = Field(alias="Price")
    text: List[str] = Field(alias="Text", default_factory=list)
    images: List[str] = Field(alias="Photo", default_factory=list)
    url: str = Field(alias="URL")
    dealer: str = Field(alias="ДИЛЕР")
    sku: str = Field(alias="SKU")

    config: ConfigModel

    class Config:
        validate_by_name = True
        validate_assignment = True
        populate_by_field_name = True

    def __init__(self, config: ConfigModel, **data):
        data["config"] = config
        super().__init__(**data)

    @computed_field
    @property
    def processed_model(self) -> str:
        return self.apply_text_replacements_to_string(self.model)

    @computed_field
    @property
    def processed_door_count(self) -> str:
        return self.apply_text_replacements_to_string(self.door_count)

    @computed_field
    @property
    def processed_transmission(self) -> str:
        return self.apply_text_replacements_to_string(self.transmission)

    @computed_field
    @property
    def processed_fuel(self) -> str:
        return self.apply_text_replacements_to_string(self.fuel)

    @computed_field
    @property
    def processed_body(self) -> str:
        return self.apply_text_replacements_to_string(self.body)

    @computed_field
    @property
    def processed_color(self) -> str:
        return self.apply_text_replacements_to_string(self.color)

    @computed_field
    @property
    def formatted_title(self) -> str:
        try:
            formatted = self.config.templates.title.format(
                category=self.category,
                model=self.processed_model,
                year=self.year_of_release,
                mileage=self.mileage,
                transmission=self.processed_transmission,
            ).strip()
            logger.bind(formatted_title=formatted).debug(
                "Title formatted successfully"
            )
            return formatted
        except (KeyError, ValueError) as e:
            fallback = f"{self.category} {self.processed_model}, {self.year_of_release}".strip()
            logger.bind(
                error=str(e),
                error_type=type(e).__name__,
                fallback_title=fallback,
            ).error("Title formatting failed, using fallback")
            return fallback

    @computed_field
    @property
    def formatted_tab_one(self) -> str:
        return self.config.templates.tabs_one + self.processed_text

    @computed_field
    @property
    def formatted_tab_two(self) -> str:
        return self.config.templates.tabs_two

    @computed_field
    @property
    def formatted_seo_title(self) -> str:
        try:
            formatted = self.config.templates.seo_title.format(
                category=self.category,
                model=self.processed_model,
                year=self.year_of_release,
                fuel=self.processed_fuel or "",
                price=self.price or "",
            ).strip()
            logger.bind(formatted_seo_title=formatted).debug(
                "SEO title formatted successfully"
            )
            return formatted
        except (KeyError, ValueError) as e:
            fallback = f"{self.category} {self.processed_model}, {self.year_of_release} год. {self.processed_fuel}, цена {self.price} € — авто под заказ из Европы"
            logger.bind(
                error=str(e),
                error_type=type(e).__name__,
                fallback_seo_title=fallback,
            ).error("SEO title formatting failed, using fallback")
            return fallback

    @computed_field
    @property
    def formatted_seo_description(self) -> str:
        try:
            formatted = self.config.templates.seo_description.format(
                category=self.category,
                model=self.processed_model,
                year=self.year_of_release,
                price=self.price or "",
            ).strip()
            logger.bind(formatted_seo_description=formatted).debug(
                "SEO description formatted successfully"
            )
            return formatted
        except (KeyError, ValueError) as e:
            fallback = f"Купить авто из Европы под заказ {self.category} {self.processed_model}, {self.year_of_release} за {self.price}€. Прозрачная история. Реальный пробег."
            logger.bind(
                error=str(e),
                error_type=type(e).__name__,
                fallback_seo_description=fallback,
            ).error("SEO description formatting failed, using fallback")
            return fallback

    @computed_field
    @property
    def formatted_seo_keywords(self) -> str:
        brand_specific = f"авто из {self.category.lower()}, купить авто под заказ из {self.category.lower()}"
        formatted = (
            f"{self.config.templates.seo_keywords}, {brand_specific}".strip()
        )
        logger.bind(formatted_seo_keywords=formatted).debug(
            "SEO keywords formatted successfully"
        )
        return formatted

    @computed_field
    @property
    def processed_text(self) -> str:
        processed = self.apply_text_replacements_to_text_field(self.text)
        logger.bind(
            original_length=len(self.text),
            processed_length=len(processed),
            final_length=len(processed),
        ).debug("Text processed successfully")
        return processed

    @computed_field
    @property
    def processed_images_string(self) -> str:
        return (
            ",".join(self.get_processed_images())
            if self.get_processed_images()
            else ""
        )

    @computed_field
    @property
    def proccessed_start_text(self) -> str:
        formatted_string = self.config.templates.start_text.format(
            category=self.category, model=self.processed_model
        )
        return formatted_string

    def apply_text_replacements_to_text_field(self, text: List[str]) -> str:
        if not text:
            return ""
        replacements = self.config.data.replacement_rules
        if not replacements:
            logger.bind(text_length=len(text)).debug(
                "No replacement rules available"
            )
            return "<br />".join(text)
        result = text
        replacements_made = 0
        for original, replacement in replacements.items():
            if original in result:
                result = [
                    item.replace(original, replacement) for item in result
                ]
                replacements_made += 1
        logger.bind(
            original_length=len(text),
            final_length=len(result),
            replacements_made=replacements_made,
            total_rules=len(replacements),
        ).debug("Text replacements applied")
        return "<br />".join(result)

    def apply_text_replacements_to_string(self, text: str) -> str:
        if not text:
            return ""
        replacements = self.config.data.replacement_rules
        if not replacements:
            logger.bind(text_length=len(text)).debug(
                "No replacement rules available for string"
            )
            return text
        result = text
        replacements_made = 0
        for original, replacement in replacements.items():
            if original in result:
                result = result.replace(original, replacement)
                replacements_made += 1
        logger.bind(
            original_text=text,
            final_text=result,
            replacements_made=replacements_made,
            total_rules=len(replacements),
        ).debug("String replacements applied")
        return result

    def is_dealer_excluded(self) -> bool:
        dealer_exclusions = self.config.data.dealer_exclusions
        if not dealer_exclusions:
            logger.bind(dealer=self.dealer).debug(
                "No dealer exclusions configured"
            )
            return False
        excluded = self.dealer.lower() in [
            dealer.lower() for dealer in dealer_exclusions
        ]
        logger.bind(
            dealer=self.dealer,
            is_excluded=excluded,
            total_exclusions=len(dealer_exclusions),
        ).debug("Dealer exclusion check completed")
        return excluded

    def is_brand_excluded(self) -> bool:
        brand_exclusions = self.config.data.brand_exclusions
        if not brand_exclusions:
            logger.bind(brand=self.model).debug(
                "No brand exclusions configured"
            )
            return False
        excluded = self.category in brand_exclusions
        logger.bind(
            brand=self.category,
            is_excluded=excluded,
            total_exclusions=len(brand_exclusions),
        ).debug("Brand exclusion check completed")
        return excluded

    def check_exclusions(self) -> None:
        if self.is_dealer_excluded():
            logger.bind(
                dealer=self.dealer,
                model=self.model,
                url=self.url,
            ).warning("Product excluded due to dealer exclusion")
            raise ModelExclusionError(
                f"Dealer '{self.dealer}' is in exclusion list"
            )

        if self.is_brand_excluded():
            logger.bind(
                brand=self.category,
                dealer=self.dealer,
                url=self.url,
            ).warning("Product excluded due to brand exclusion")
            raise ModelExclusionError(
                f"Brand '{self.model}' is in exclusion list"
            )

        logger.bind(
            dealer=self.dealer,
            brand=self.model,
            url=self.url,
        ).debug("Product passed all exclusion checks")

    def get_processed_images(self) -> List[str]:
        if not self.images:
            logger.debug("No images to process")
            return []
        original_count = len(self.images)
        image_exclusions = self.config.data.image_exclusions

        # Проверяем, есть ли дилер в списке исключений
        if image_exclusions and self.dealer in image_exclusions:
            rules = image_exclusions.get(self.dealer)

            # Если для дилера нет правил (пустая строка в CSV), возвращаем оригинальные фото
            if not rules:
                logger.bind(dealer=self.dealer).warning(
                    "Dealer found in exclusion file, but no rules are defined."
                )
                return self.images

            processed_images = self._apply_image_exclusions(self.images, rules)
            logger.bind(
                dealer=self.dealer,
                original_count=original_count,
                processed_count=len(processed_images),
                rules=rules,
            ).debug("Dealer-specific image exclusions applied")
            return processed_images
        else:
            # Глобальная проверка, если для дилера нет правил в файле
            if original_count < self.config.parser.exclude_ads_pictures:
                logger.bind(
                    dealer=self.dealer,
                    image_count=original_count,
                    minimum_required=self.config.parser.exclude_ads_pictures,
                ).warning(
                    "Images excluded due to global minimum requirement (no dealer rules)"
                )
                raise ModelExclusionError("No minimal images requirements")

            logger.bind(final_count=original_count).debug(
                "Images processed without exclusions"
            )
            return self.images

    def _apply_image_exclusions(
        self, images: List[str], rules: Dict[str, str]
    ) -> List[str]:
        if not images:
            return images

        result = images.copy()
        original_count = len(result)
        removed_images = []

        start_remove = rules.get("НАЧАЛО") or rules.get("start", "")
        end_remove = rules.get("КОНЕЦ") or rules.get("end", "")

        if not start_remove.strip() and not end_remove.strip():
            logger.bind(dealer=self.dealer).debug(
                "Exclusion rules are empty, returning original images"
            )
            return result

        if start_remove and start_remove.strip():
            positions_to_remove = []
            try:
                for pos_str in start_remove.split(","):
                    pos_str = pos_str.strip()
                    if pos_str.isdigit():
                        pos = int(pos_str)
                        if pos > 0:
                            index = pos - 1
                            if index < len(result):
                                positions_to_remove.append(index)

                positions_to_remove.sort(reverse=True)

                for index in positions_to_remove:
                    if index < len(result):
                        removed_image = result.pop(index)
                        removed_images.append(f"позиция {index + 1}")
                        logger.bind(
                            removed_position=index + 1,
                            removed_image_url=removed_image[:50] + "...",
                            remaining_count=len(result),
                        ).debug("Removed image at specific position")

            except (ValueError, IndexError) as e:
                logger.bind(
                    error=str(e),
                    start_remove_value=start_remove,
                ).warning("Failed to parse start positions for image removal")

        if end_remove and end_remove.strip():
            try:
                count_to_remove = int(end_remove.strip())
                if count_to_remove > 0:
                    actual_remove = min(count_to_remove, len(result))
                    for i in range(actual_remove):
                        if result:
                            removed_image = result.pop()
                            removed_images.append(f"с конца {i + 1}")
                            logger.bind(
                                removed_image_url=removed_image[:50] + "...",
                                remaining_count=len(result),
                            ).debug("Removed image from end")
            except (ValueError, TypeError) as e:
                logger.bind(
                    error=str(e),
                    end_remove_value=end_remove,
                ).warning("Failed to parse end count for image removal")

        logger.bind(
            dealer=self.dealer,
            original_count=original_count,
            final_count=len(result),
            removed_images=removed_images,
            rules_applied=rules,
        ).debug("Image exclusions applied successfully")

        if len(result) < self.config.parser.exclude_ads_pictures:
            logger.bind(
                dealer=self.dealer,
                original_count=original_count,
                final_count=len(result),
                minimum_required=self.config.parser.exclude_ads_pictures,
            ).warning(
                "Images excluded due to global minimum requirement after exclusions applied"
            )
            raise ModelExclusionError("No minimal images requirements")

        return result

    def convert_price_to_rubles(self) -> Optional[str]:
        try:
            if not self.price:
                logger.warning("No price available for conversion")
                return None
            eur_price = float(self.price)
            exchange_rate = self.config.calculation.currency_exchange or 0.24
            if exchange_rate <= 0:
                logger.bind(
                    configured_rate=self.config.calculation.currency_exchange,
                    default_rate=0.24,
                ).warning("Invalid exchange rate, using default")
                exchange_rate = 0.24
            rub_price = eur_price / exchange_rate
            formatted_price = f"{int(rub_price):,}".replace(",", " ")
            logger.bind(
                eur_price=eur_price,
                exchange_rate=exchange_rate,
                rub_price=int(rub_price),
                formatted_price=formatted_price,
            ).debug("Price conversion completed")
            return formatted_price
        except (ValueError, AttributeError) as e:
            logger.bind(
                error=str(e),
                error_type=type(e).__name__,
                original_price=self.price,
            ).error("Price conversion failed")
            return None

    def to_csv_dict(self) -> Dict[str, str]:
        try:
            # Basic required fields - these must be present
            required_fields = {
                "category": self.category,
                "model": self.model,
                "color": self.color,
                "year_of_release": self.year_of_release,
                "mileage": self.mileage,
                "transmission": self.transmission,
                "fuel": self.fuel,
                "body": self.body,
                "price": self.price,
                "images": self.images,
            }

            missing_required = [
                field_name
                for field_name, value in required_fields.items()
                if value is None
                or (isinstance(value, str) and not value.strip())
                or (isinstance(value, list) and not value)
            ]

            if missing_required:
                logger.bind(
                    dealer=self.dealer,
                    sku=self.sku,
                    missing_fields=missing_required,
                ).warning("Product skipped due to missing required fields")
                raise ModelExclusionError(
                    f"Missing required fields: {', '.join(missing_required)}"
                )

            self.check_exclusions()
            processed_images = self.get_processed_images()
            if len(processed_images) < self.config.parser.exclude_ads_pictures:
                raise ModelExclusionError(
                    "Product excluded due to insufficient images count"
                )

            if not self.dealer:
                raise ModelExclusionError("No dealer available")

            csv_dict = {
                "Title": self.formatted_title,
                "Category": self.category,
                "Characteristics: модель": self.processed_model,
                "Characteristics: год выпуска": self.year_of_release,
                "Characteristics: пробег": self.mileage,
                "Characteristics: коробка": self.processed_transmission,
                "Characteristics: топливо": self.processed_fuel,
                "Characteristics: объем, см3": self.engine_volume,
                "Characteristics: мощность": self.power,
                "Characteristics: кузов": self.processed_body,
                "Characteristics: цвет": self.processed_color,
                "Characteristics: к-во дверей": self.door_count,
                "Characteristics: к-во мест": self.seat_count,
                "Characteristics: к-во владельцев": self.owner_count,
                "Price": self.price,
                "Text": self.proccessed_start_text,
                "Photo": ",".join(processed_images),
                "URL": self.url,
                "ДИЛЕР": self.dealer,
                "SKU": self.sku,
                "SEO title": self.formatted_seo_title,
                "SEO descr": self.formatted_seo_description,
                "SEO keywords": self.formatted_seo_keywords,
                "SEO alt": self.formatted_title,
                "Tabs:1": self.formatted_tab_one,
                "Tabs:2": self.formatted_tab_two,
            }
            logger.bind(
                total_fields=len(csv_dict),
                processed_images_count=len(processed_images),
                text_length=len(csv_dict.get("Text", "")),
            ).info("CSV dictionary created successfully")
            return csv_dict
        except ModelExclusionError:
            logger.bind(
                dealer=self.dealer,
                brand=self.model,
                url=self.url,
            ).warning("Product excluded due to exclusion checks")
            return {}
        except Exception as e:
            logger.bind(
                error=str(e),
                error_type=type(e).__name__,
            ).error("Failed to create CSV dictionary")
            raise e
