from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LoggingConfig(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )
    file_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = (
        Field(default="DEBUG")
    )
    log_dir: Path = Field(default=Path("logs"))
    rotation: str = Field(default="10 MB")
    retention: str = Field(default="30 days")
    compression: str = Field(default="zip")
    serialize: bool = Field(default=False)
    backtrace: bool = Field(default=True)
    diagnose: bool = Field(default=False)
    enqueue: bool = Field(default=True)

    @field_validator("log_dir", mode="after")
    @classmethod
    def validate_log_dir(cls, v: str) -> Path:
        return Path(v).resolve()


class ParserConfig(BaseModel):
    base_url: str = Field(default="https://www.mobile.de")
    base_search_url: str = Field(
        default="https://www.mobile.de/ru/категория/автомобиль/vhc:car"
    )
    timeout: int = Field(default=15)
    retries: int = Field(default=3)
    delay_min: int = Field(default=100)
    delay_max: int = Field(default=500)
    max_concurrency: int = Field(default=5)
    exclude_ads_pictures: int = Field(default=-1)
    proxy_file: Path = Field(default=Path("proxies.txt"))


class FilesConfig(BaseModel):
    lines_limit: int = Field(default=450)
    brand_excludes_file: Path = Field(
        default=Path("var/www/mobile/excludes_brand.csv")
    )
    dealer_excludes_file: Path = Field(
        default=Path("var/www/mobile/excludes_dealer.csv")
    )
    dealer_exclude_images_file: Path = Field(
        default=Path("var/www/mobile/excludes_images.csv")
    )
    replaces_file: Path = Field(default=Path("var/www/mobile/replaces.csv"))
    files_dir: Path = Field(default=Path("var/www/mobile/files"))

    @field_validator("files_dir", mode="after")
    @classmethod
    def validate_files_dir(cls, v: Path) -> None:
        v.mkdir(parents=True, exist_ok=True)
        return None

    @field_validator(
        "brand_excludes_file",
        "dealer_excludes_file",
        "dealer_exclude_images_file",
        "replaces_file",
        mode="after",
    )
    @classmethod
    def validate_files(cls, v: Path) -> None:
        if not v.exists():
            raise FileNotFoundError(f"File does not exist: {v}")
        return None


class TemplatesConfig(BaseModel):
    title: str = Field(default="{0} {1}, {2}, {4}, пробег {3} км")
    seo_title: str = Field(
        default="{0} {1}, {2} год. {6}, цена {13} € — авто под заказ из Европы"
    )
    seo_description: str = Field(
        default="Купить авто из Европы под заказ {0} {1}, {2} за {13}€. Прозрачная история. Реальный пробег."
    )
    seo_keywords: str = Field(
        default="авто под заказ, авто из европы, купить авто под заказ из европы, авто из , купить авто под заказ из "
    )
    start_text: str = Field(
        default='<span style="color:#ff0000"><strong>ВНИМАНИЕ!!!<br />Цена авто указана в Европе, без таможни и доставки<br />Для расчёта полной цены - нажмите кнопку ЗАПРОС</strong></span><br /><br />'
    )


class GasolineCalculationConfig(BaseModel):
    discount: float = Field(default=1.23)
    old_price: float = Field(default=0)
    expenses: float = Field(default=0)


class ElectricCalculationConfig(BaseModel):
    discount: float = Field(default=1.23)
    expenses: float = Field(default=0)
    tax: float = Field(default=0)


class CalculationConfig(BaseModel):
    currency_exchange: float = Field(default=0.24)
    gasoline: GasolineCalculationConfig = Field(
        default=GasolineCalculationConfig()
    )
    electric: ElectricCalculationConfig = Field(
        default=ElectricCalculationConfig()
    )


class ConfigModel(BaseModel):
    logging: LoggingConfig
    parser: ParserConfig
    files: FilesConfig
    templates: TemplatesConfig
    calculation: CalculationConfig
