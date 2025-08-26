from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class ParsingResult(BaseModel):

    success: bool = Field(..., description="Успешность выполнения")
    message: str = Field(..., description="Сообщение о результате")
    products_count: int = Field(
        default=0, description="Количество найденных товаров"
    )
    start_time: Optional[datetime] = Field(
        default=None, description="Время начала"
    )
    end_time: Optional[datetime] = Field(
        default=None, description="Время завершения"
    )
    error_message: Optional[str] = Field(
        default=None, description="Сообщение об ошибке"
    )

    @computed_field
    @property
    def duration_seconds(self) -> float:
        if not self.start_time or not self.end_time:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()

    @classmethod
    def success_result(
        cls, message: str, products_count: int = 0
    ) -> "ParsingResult":
        return cls(
            success=True,
            message=message,
            products_count=products_count,
            start_time=datetime.now(),
            end_time=datetime.now(),
        )

    @classmethod
    def error_result(
        cls, message: str, error_message: Optional[str] = None
    ) -> "ParsingResult":
        return cls(
            success=False,
            message=message,
            error_message=error_message,
            start_time=datetime.now(),
            end_time=datetime.now(),
        )
