from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def create_product_model(table_name: str):
    """Create ProductDB model with dynamic table name"""

    class ProductDB(Base):
        __tablename__ = table_name

        id = Column(Integer, primary_key=True, autoincrement=True)
        title = Column(String(255), nullable=False)
        category = Column(String(255), nullable=False)
        model = Column(String(255), nullable=False)
        year_of_release = Column(String(50), nullable=False)
        mileage = Column(String(100), nullable=False)
        transmission = Column(String(100), nullable=False)
        fuel = Column(String(100), nullable=False)
        engine_volume = Column(String(100), nullable=True)
        body = Column(String(100), nullable=False)
        color = Column(String(100), nullable=False)
        door_count = Column(String(50), nullable=True)
        seat_count = Column(String(50), nullable=True)
        owner_count = Column(String(50), nullable=True)
        power = Column(String(100), nullable=True)
        price = Column(String(100), nullable=False)
        text = Column(Text, nullable=False)
        images = Column(Text, nullable=False)
        url = Column(String(500), nullable=False)
        dealer = Column(String(255), nullable=False)
        sku = Column(String(255), unique=True, nullable=False, index=True)
        seo_title = Column(Text, nullable=False)
        seo_description = Column(Text, nullable=False)
        seo_keywords = Column(Text, nullable=False)
        seo_alt = Column(Text, nullable=False)
        tab_one = Column(Text, nullable=False)
        tab_two = Column(Text, nullable=False)
        created_at = Column(DateTime, default=func.now(), nullable=False)
        updated_at = Column(
            DateTime, default=func.now(), onupdate=func.now(), nullable=False
        )

        def __repr__(self):
            return f"<ProductDB(sku='{self.sku}', model='{self.model}', dealer='{self.dealer}')>"

    return ProductDB
