from typing import Dict, List, Optional

from loguru import logger
from pydantic import BaseModel, Field, computed_field

from shared.config.config_model import ConfigModel
from shared.exceptions.model_exceptions import ModelExclusionError


class ProductModel(BaseModel):
    category: str = Field(alias="Category", default="")
    model: str = Field(alias="Characteristics: модель", default="")
    year_of_release: str = Field(
        alias="Characteristics: год выпуска", default=""
    )
    mileage: str = Field(alias="Characteristics: пробег", default="")
    transmission: str = Field(alias="Characteristics: коробка", default="")
    fuel: str = Field(alias="Characteristics: топливо", default="")
    engine_volume: str = Field(alias="Characteristics: объем, см3", default="")
    body: str = Field(alias="Characteristics: кузов", default="")
    color: str = Field(alias="Characteristics: цвет", default="")
    door_count: str = Field(alias="Characteristics: к-во дверей", default="")
    seat_count: str = Field(alias="Characteristics: к-во мест", default="")
    owner_count: str = Field(
        alias="Characteristics: к-во владельцев", default=""
    )
    price: str = Field(alias="Price", default="")
    text: List[str] = Field(alias="Text", default_factory=list)
    images: List[str] = Field(alias="Photo", default_factory=list)
    url: str = Field(alias="URL", default="")
    dealer: str = Field(alias="ДИЛЕР", default="")
    sku: str = Field(alias="SKU", default="")

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
    def formatted_title(self) -> str:
        try:
            formatted = self.config.templates.title.format(
                self.category or "",
                self.model or "",
                self.year_of_release or "",
                self.mileage or "",
                self.transmission or "",
            ).strip()
            logger.debug(
                "Title formatted successfully", formatted_title=formatted
            )
            return formatted
        except (IndexError, KeyError) as e:
            fallback = (
                f"{self.category} {self.model}, {self.year_of_release}".strip()
            )
            logger.error(
                "Title formatting failed, using fallback",
                error=str(e),
                error_type=type(e).__name__,
                fallback_title=fallback,
            )
            return fallback

    @computed_field
    @property
    def formatted_tab_one(self) -> str:
        return self.config.templates.tabs_one  # TODO: add format

    @computed_field
    @property
    def formatted_tab_two(self) -> str:
        return self.config.templates.tabs_two  # TODO: add format

    @computed_field
    @property
    def formatted_seo_title(self) -> str:
        try:
            formatted = self.config.templates.seo_title.format(
                self.category or "",
                self.model or "",
                self.year_of_release or "",
                "",
                "",
                "",
                self.fuel or "",
                "",
                "",
                "",
                "",
                "",
                "",
                self.price or "",
            ).strip()
            logger.debug(
                "SEO title formatted successfully",
                formatted_seo_title=formatted,
            )
            return formatted
        except (IndexError, KeyError) as e:
            fallback = f"{self.category} {self.model}, {self.year_of_release} год. {self.fuel}, цена {self.price} € — авто под заказ из Европы"
            logger.error(
                "SEO title formatting failed, using fallback",
                error=str(e),
                error_type=type(e).__name__,
                fallback_seo_title=fallback,
            )
            return fallback

    @computed_field
    @property
    def formatted_seo_description(self) -> str:
        try:
            formatted = self.config.templates.seo_description.format(
                self.category or "",
                self.model or "",
                self.year_of_release or "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                self.price or "",
            ).strip()
            logger.debug(
                "SEO description formatted successfully",
                formatted_seo_description=formatted,
            )
            return formatted
        except (IndexError, KeyError) as e:
            fallback = f"Купить авто из Европы под заказ {self.category} {self.model}, {self.year_of_release} за {self.price}€. Прозрачная история. Реальный пробег."
            logger.error(
                "SEO description formatting failed, using fallback",
                error=str(e),
                error_type=type(e).__name__,
                fallback_seo_description=fallback,
            )
            return fallback

    @computed_field
    @property
    def formatted_seo_keywords(self) -> str:
        brand_specific = f"авто из {self.category.lower()}, купить авто под заказ из {self.category.lower()}"
        formatted = (
            f"{self.config.templates.seo_keywords}, {brand_specific}".strip()
        )
        logger.debug(
            "SEO keywords formatted successfully",
            formatted_seo_keywords=formatted,
        )
        return formatted

    @computed_field
    @property
    def processed_text(self) -> str:
        processed = self.apply_text_replacements(self.text)
        final_text = f"{self.config.templates.start_text}{processed}"
        logger.debug(
            "Text processed successfully",
            original_length=len(self.text),
            processed_length=len(processed),
            final_length=len(final_text),
        )
        return final_text

    def apply_text_replacements(self, text: List[str]) -> str:
        if not text:
            return ""
        replacements = self.config.data.replacement_rules
        if not replacements:
            logger.debug(
                "No replacement rules available", text_length=len(text)
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
        logger.debug(
            "Text replacements applied",
            original_length=len(text),
            final_length=len(result),
            replacements_made=replacements_made,
            total_rules=len(replacements),
        )
        return "<br />".join(result)

    def is_dealer_excluded(self) -> bool:
        dealer_exclusions = self.config.data.dealer_exclusions
        if not dealer_exclusions:
            logger.debug("No dealer exclusions configured", dealer=self.dealer)
            return False
        excluded = self.dealer in dealer_exclusions
        logger.debug(
            "Dealer exclusion check completed",
            dealer=self.dealer,
            is_excluded=excluded,
            total_exclusions=len(dealer_exclusions),
        )
        return excluded

    def is_brand_excluded(self) -> bool:
        brand_exclusions = self.config.data.brand_exclusions
        if not brand_exclusions:
            logger.debug("No brand exclusions configured", brand=self.model)
            return False
        excluded = self.model in brand_exclusions
        logger.debug(
            "Brand exclusion check completed",
            brand=self.model,
            is_excluded=excluded,
            total_exclusions=len(brand_exclusions),
        )
        return excluded

    def check_exclusions(self) -> None:
        if self.is_dealer_excluded():
            logger.warning(
                "Product excluded due to dealer exclusion",
                dealer=self.dealer,
                model=self.model,
                url=self.url,
            )
            raise ModelExclusionError(
                f"Dealer '{self.dealer}' is in exclusion list"
            )

        if self.is_brand_excluded():
            logger.warning(
                "Product excluded due to brand exclusion",
                brand=self.model,
                dealer=self.dealer,
                url=self.url,
            )
            raise ModelExclusionError(
                f"Brand '{self.model}' is in exclusion list"
            )

        logger.debug(
            "Product passed all exclusion checks",
            dealer=self.dealer,
            brand=self.model,
            url=self.url,
        )

    def get_processed_images(self) -> List[str]:
        if not self.images:
            logger.debug("No images to process")
            return []
        original_count = len(self.images)
        image_exclusions = self.config.data.image_exclusions
        if image_exclusions and self.dealer in image_exclusions:
            rules = image_exclusions[self.dealer]
            processed_images = self._apply_image_exclusions(self.images, rules)
            logger.debug(
                "Dealer-specific image exclusions applied",
                dealer=self.dealer,
                original_count=original_count,
                processed_count=len(processed_images),
                rules=rules,
            )
            return processed_images
        if self.config.parser.exclude_ads_pictures > 0:
            min_images = self.config.parser.exclude_ads_pictures + 1
            if original_count < min_images:
                logger.debug(
                    "Images excluded due to global minimum requirement",
                    image_count=original_count,
                    minimum_required=min_images,
                )
                return []
        logger.debug(
            "Images processed without exclusions", final_count=original_count
        )
        return self.images

    def _apply_image_exclusions(
        self, images: List[str], rules: Dict[str, str]
    ) -> List[str]:
        if not images:
            return images
        result = images.copy()
        original_count = len(result)
        start_remove = rules.get("start", "1")
        if start_remove.isdigit():
            start_count = int(start_remove)
            if start_count > 0 and len(result) > start_count:
                result = result[start_count:]
                logger.debug(
                    "Removed images from start",
                    removed_count=start_count,
                    remaining_count=len(result),
                )
        penultimate = rules.get("penultimate", "*")
        if penultimate != "*" and len(result) >= 2:
            removed_image = result.pop(-2)
            logger.debug(
                "Removed penultimate image",
                removed_image_url=removed_image[:50] + "...",
                remaining_count=len(result),
            )
        last = rules.get("last", "*")
        if last != "*" and len(result) >= 1:
            removed_image = result.pop(-1)
            logger.debug(
                "Removed last image",
                removed_image_url=removed_image[:50] + "...",
                remaining_count=len(result),
            )
        logger.debug(
            "Image exclusions applied successfully",
            original_count=original_count,
            final_count=len(result),
            rules_applied=rules,
        )
        return result

    def convert_price_to_rubles(self) -> Optional[str]:
        try:
            if not self.price:
                logger.warning("No price available for conversion")
                return None
            eur_price = float(self.price)
            exchange_rate = self.config.calculation.currency_exchange or 0.24
            if exchange_rate <= 0:
                logger.warning(
                    "Invalid exchange rate, using default",
                    configured_rate=self.config.calculation.currency_exchange,
                    default_rate=0.24,
                )
                exchange_rate = 0.24
            rub_price = eur_price / exchange_rate
            formatted_price = f"{int(rub_price):,}".replace(",", " ")
            logger.debug(
                "Price conversion completed",
                eur_price=eur_price,
                exchange_rate=exchange_rate,
                rub_price=int(rub_price),
                formatted_price=formatted_price,
            )
            return formatted_price
        except (ValueError, AttributeError) as e:
            logger.error(
                "Price conversion failed",
                error=str(e),
                error_type=type(e).__name__,
                original_price=self.price,
            )
            return None

    def to_csv_dict(self) -> Dict[str, str]:
        try:
            self.check_exclusions()
            processed_images = self.get_processed_images()

            if not processed_images:
                raise ModelExclusionError("No minimal images requirements")

            if not self.dealer:
                raise ModelExclusionError("No dealer available")

            csv_dict = {
                "Title": self.formatted_title,
                "Category": self.category,
                "Characteristics: модель": self.model,
                "Characteristics: год выпуска": self.year_of_release,
                "Characteristics: пробег": self.mileage,
                "Characteristics: коробка": self.transmission,
                "Characteristics: топливо": self.fuel,
                "Characteristics: объем, см3": self.engine_volume,
                "Characteristics: кузов": self.body,
                "Characteristics: цвет": self.color,
                "Characteristics: к-во дверей": self.door_count,
                "Characteristics: к-во мест": self.seat_count,
                "Characteristics: к-во владельцев": self.owner_count,
                "Price": self.price,
                "Text": self.processed_text,
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
            logger.info(
                "CSV dictionary created successfully",
                total_fields=len(csv_dict),
                processed_images_count=len(processed_images),
                text_length=len(csv_dict.get("Text", "")),
            )
            return csv_dict
        except ModelExclusionError:
            logger.warning(
                "Product excluded due to exclusion checks",
                dealer=self.dealer,
                brand=self.model,
                url=self.url,
            )
            return {}
        except Exception as e:
            logger.error(
                "Failed to create CSV dictionary",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise e
