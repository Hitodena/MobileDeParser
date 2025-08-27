from pathlib import Path
from typing import Dict, List, Literal, Set

from pydantic import BaseModel, Field, computed_field, field_validator

from shared.utils.generate_links import generate_links


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
    modules: List[str] = Field(default=[])

    @field_validator("log_dir", mode="after")
    @classmethod
    def validate_log_dir(cls, v: str) -> Path:
        return Path(v).resolve()


class ParserConfig(BaseModel):
    base_url: str = Field(default="https://www.mobile.de/")
    base_search_url: str = Field(
        default="https://www.mobile.de/ru/категория/автомобиль/vhc:car/"
    )
    check_url: str = Field(default="https://www.mobile.de/ru/")
    pages: int = Field(default=40)
    items_per_page: int = Field(default=50)
    timeout: int = Field(default=15)
    retries: int = Field(default=3)
    delay_min: float = Field(default=0.1)
    delay_max: float = Field(default=0.5)
    max_concurrency: int = Field(default=5)
    exclude_ads_pictures: int = Field(default=-1)
    proxy_file: Path = Field(default=Path("proxies.txt"))
    proxy_timeout: float = Field(default=5)
    interval_between_parse: float = Field(default=1800)
    cycle: bool = Field(default=True)

    @field_validator("proxy_file", mode="after")
    @classmethod
    def validate_proxy_file(cls, v: str) -> Path:
        return Path(v).resolve()

    @computed_field
    @property
    def links(self) -> List[str]:
        return generate_links(
            self.base_search_url, self.pages, self.items_per_page
        )


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
    db_path: Path = Field(default=Path("products.db"))

    @field_validator("files_dir", mode="after")
    @classmethod
    def validate_files_dir(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return Path(v).resolve()

    @field_validator(
        "brand_excludes_file",
        "dealer_excludes_file",
        "dealer_exclude_images_file",
        "replaces_file",
        mode="after",
    )
    @classmethod
    def validate_files(cls, v: Path) -> Path:
        if not v.exists():
            raise FileNotFoundError(f"File does not exist: {v}")
        return Path(v).resolve()


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
    tabs_one: str = Field(default="info|#|ИНФОРМАЦИЯ|#|")
    tabs_two: str = Field(default="info|#|ИНФОРМАЦИЯ|#|")


class CalculationConfig(BaseModel):
    currency_exchange: float = Field(default=0.24)


class ApiConfig(BaseModel):
    telegram: str = Field(...)
    tg_users: Set[int] = Field(default=set())


class DataConfig(BaseModel):
    replacement_rules: Dict[str, str] = Field(default_factory=dict)
    dealer_exclusions: List[str] = Field(default_factory=list)
    image_exclusions: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    brand_exclusions: List[str] = Field(default_factory=list)


class ConfigModel(BaseModel):
    logging: LoggingConfig
    parser: ParserConfig
    files: FilesConfig
    templates: TemplatesConfig
    calculation: CalculationConfig
    api: ApiConfig
    data: DataConfig = Field(default_factory=DataConfig)
