from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class ParsingProgress(BaseModel):

    total_urls: int = Field(
        default=0, description="Общее количество URL для обработки"
    )
    processed_urls: int = Field(
        default=0, description="Количество обработанных URL"
    )
    found_products: int = Field(
        default=0, description="Количество найденных товаров"
    )
    start_time: Optional[datetime] = Field(
        default=None, description="Время начала парсинга"
    )
    last_update: Optional[datetime] = Field(
        default=None, description="Время последнего обновления"
    )
    status: str = Field(default="idle", description="Статус парсинга")
    error_message: Optional[str] = Field(
        default=None, description="Сообщение об ошибке"
    )

    @computed_field
    @property
    def progress_percentage(self) -> float:
        if self.total_urls == 0:
            return 0.0
        return (self.processed_urls / self.total_urls) * 100

    @computed_field
    @property
    def elapsed_time(self) -> float:
        if not self.start_time:
            return 0.0
        end_time = self.last_update or datetime.now()
        return (end_time - self.start_time).total_seconds()

    def update_progress(
        self,
        processed_urls: Optional[int] = None,
        found_products: Optional[int] = None,
    ) -> None:
        if processed_urls is not None:
            self.processed_urls = processed_urls

        if found_products is not None:
            self.found_products = found_products

        self.last_update = datetime.now()

    def start_tracking(self, total_urls: int) -> None:
        self.total_urls = total_urls
        self.processed_urls = 0
        self.found_products = 0
        self.start_time = datetime.now()
        self.last_update = datetime.now()
        self.status = "running"
        self.error_message = None

    def complete_tracking(
        self, success: bool = True, error_message: Optional[str] = None
    ) -> None:
        self.status = "completed" if success else "error"
        self.error_message = error_message
        self.last_update = datetime.now()
