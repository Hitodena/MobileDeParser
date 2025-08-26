from pydantic import BaseModel, Field


class ParserStatus(BaseModel):
    is_running: bool = Field(..., description="Запущен ли парсер")
    cycle_enabled: bool = Field(
        ..., description="Включен ли циклический режим"
    )
    interval_seconds: int = Field(
        ..., description="Интервал между циклами в секундах"
    )
    max_concurrency: int = Field(
        ..., description="Максимальное количество одновременных потоков"
    )

    @classmethod
    def create_default(cls) -> "ParserStatus":
        return cls(
            is_running=False,
            cycle_enabled=False,
            interval_seconds=0,
            max_concurrency=0,
        )
