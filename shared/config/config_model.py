from pathlib import Path
from typing import Dict, List, Literal, Self, Set

from pydantic import (
    BaseModel,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

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
    proxy_check_retries: int = Field(default=3)
    proxy_check_interval: int = Field(default=600)

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


class AIConfig(BaseModel):
    enabled: bool = Field(default=True)
    api_key: str = Field(default="")
    model: str = Field(default="openrouter/polaris-alpha")
    prompt_path: str = Field("prompt.txt")
    prompt: str = Field(
        default="Перепиши короткое описание автомобиля, сделай его уникальным и привлекательным. Сохрани факты. Максимум 2-3 предложения."
    )
    timeout: int = Field(default=600)
    retries: int = Field(default=3)
    ref_field: str = Field(default="title")
    out_field: str = Field(default="tab_two")
    out_prefix: str = Field(default="info|#|ИНФОРМАЦИЯ|#|")
    batch_count: int = Field(default=100)

    @model_validator(mode="after")
    def define_prompt(self) -> Self:
        if self.enabled and self.api_key:
            try:
                path = Path(self.prompt_path)
                prompt_content = open(path, encoding="utf-8").read().strip()
                self.prompt = prompt_content
                return self
            except FileNotFoundError:
                self.enabled = False
                return self
        else:
            return self


class FilesConfig(BaseModel):
    lines_limit: int = Field(default=450)
    brand_excludes_file: Path = Field(
        default=Path("/var/www/mobile/excludes_brand.csv")
    )
    dealer_excludes_file: Path = Field(
        default=Path("/var/www/mobile/excludes_dealer.csv")
    )
    dealer_exclude_images_file: Path = Field(
        default=Path("/var/www/mobile/excludes_images.csv")
    )
    replaces_file: Path = Field(default=Path("/var/www/mobile/replaces.csv"))
    files_dir: Path = Field(default=Path("/var/www/mobile/files"))
    db_path: str = Field(default="sqlite:///var/www/mobile/files/products.db")
    db_table_name: str = Field(default="products")
    db_additional_table_name: str | None = Field(default=None)

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
    title: str = Field(default="")
    seo_title: str = Field(default="")
    seo_description: str = Field(default="")
    seo_keywords: str = Field(default="")
    start_text: str = Field(default="")
    tabs_one: str = Field(default="")
    tabs_two: str = Field(default="")


class CalculationConfig(BaseModel):
    currency_exchange: float = Field(default=0.24)


class ApiConfig(BaseModel):
    telegram: str = Field(...)
    tg_users: Set[int] = Field(default=set())


class DatabaseConfig(BaseModel):
    id: str = Field(default="id")
    title: str = Field(default="Title")
    category: str = Field(default="Category")
    model: str = Field(default="Characteristics: модель")
    year_of_release: str = Field(default="Characteristics: год выпуска")
    mileage: str = Field(default="Characteristics: пробег")
    transmission: str = Field(default="Characteristics: коробка")
    fuel: str = Field(default="Characteristics: топливо")
    engine_volume: str = Field(default="Characteristics: объем, см3")
    body: str = Field(default="Characteristics: кузов")
    color: str = Field(default="Characteristics: цвет")
    door_count: str = Field(default="Characteristics: к-во дверей")
    seat_count: str = Field(default="Characteristics: к-во мест")
    owner_count: str = Field(default="Characteristics: к-во владельцев")
    power: str = Field(default="Characteristics: мощность")
    price: str = Field(default="Price")
    text: str = Field(default="Text")
    images: str = Field(default="Photo")
    url: str = Field(default="URL")
    dealer: str = Field(default="ДИЛЕР")
    sku: str = Field(default="SKU")
    seo_title: str = Field(default="SEO title")
    seo_description: str = Field(default="SEO descr")
    seo_keywords: str = Field(default="SEO keywords")
    seo_alt: str = Field(default="SEO alt")
    tab_one: str = Field(default="Tabs:1")
    tab_two: str = Field(default="Tabs:2")


class DataConfig(BaseModel):
    replacement_rules: Dict[str, str] = Field(
        default_factory=dict, min_length=1
    )
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
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
