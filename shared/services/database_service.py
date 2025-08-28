import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from core.models.product_model import ProductModel
from shared.models.database_model import Base, ProductDB


class DatabaseService:
    _instance = None
    _initialized = False

    def __new__(cls, db_path: Path | None = None):
        if cls._instance is None:
            cls._instance = super(DatabaseService, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_path: Path | None = None):
        if not self._initialized and db_path is not None:
            self.db_path = db_path
            self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
            self.SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine
            )

            Base.metadata.create_all(bind=self.engine)
            logger.bind(service="DatabaseService", db_path=str(db_path)).info(
                "Database initialized"
            )
            self._initialized = True

    def get_session(self):
        return self.SessionLocal()

    def product_exists(self, sku: str) -> bool:
        with self.get_session() as session:
            product = (
                session.query(ProductDB).filter(ProductDB.sku == sku).first()
            )
            return product is not None

    def save_product(self, product: ProductModel) -> bool:
        try:
            if self.product_exists(product.sku):
                logger.bind(service="DatabaseService", sku=product.sku).info(
                    "Product already exists, skipping"
                )
                return False

            csv_dict = product.to_csv_dict()
            if not csv_dict:
                return False

            db_product = self._convert_to_db_model(product)

            with self.get_session() as session:
                session.add(db_product)
                session.commit()
                logger.bind(service="DatabaseService", sku=product.sku).info(
                    "Product saved to database"
                )
                return True

        except IntegrityError as e:
            logger.bind(
                service="DatabaseService",
                sku=product.sku,
                error_type=type(e).__name__,
                error_message=str(e),
            ).warning("Integrity error while saving product")
            return False
        except Exception as e:
            logger.bind(
                service="DatabaseService",
                sku=product.sku,
                error_type=type(e).__name__,
                error_message=str(e),
            ).error("Error saving product")
            return False

    def save_products_batch(
        self, products: List[ProductModel]
    ) -> tuple[int, int]:
        new_count = 0
        duplicate_count = 0

        for product in products:
            if self.save_product(product):
                new_count += 1
            else:
                duplicate_count += 1

        return new_count, duplicate_count

    def _convert_to_db_model(self, product: ProductModel) -> ProductDB:
        images_json = json.dumps(product.images) if product.images else ""

        return ProductDB(
            title=product.formatted_title,
            category=product.category,
            model=product.model,
            year_of_release=product.year_of_release,
            mileage=product.mileage,
            transmission=product.transmission,
            fuel=product.fuel,
            engine_volume=product.engine_volume,
            body=product.body,
            color=product.color,
            door_count=product.door_count,
            seat_count=product.seat_count,
            owner_count=product.owner_count,
            price=product.price,
            text=product.processed_text,
            images=images_json,
            url=product.url,
            dealer=product.dealer,
            sku=product.sku,
            seo_title=product.formatted_seo_title,
            seo_description=product.formatted_seo_description,
            seo_keywords=product.formatted_seo_keywords,
            seo_alt=product.formatted_title,
            tab_one=product.formatted_tab_one,
            tab_two=product.formatted_tab_two,
        )

    def get_all_products(self) -> List[Dict]:
        with self.get_session() as session:
            products = session.query(ProductDB).all()
            return [self._db_to_dict(product) for product in products]

    def _db_to_dict(self, db_product: ProductDB) -> Dict:
        return {
            "Title": db_product.title,
            "Category": db_product.category,
            "Characteristics: модель": db_product.model,
            "Characteristics: год выпуска": db_product.year_of_release,
            "Characteristics: пробег": db_product.mileage,
            "Characteristics: коробка": db_product.transmission,
            "Characteristics: топливо": db_product.fuel,
            "Characteristics: объем, см3": db_product.engine_volume,
            "Characteristics: кузов": db_product.body,
            "Characteristics: цвет": db_product.color,
            "Characteristics: к-во дверей": db_product.door_count,
            "Characteristics: к-во мест": db_product.seat_count,
            "Characteristics: к-во владельцев": db_product.owner_count,
            "Price": db_product.price,
            "Text": db_product.text,
            "Photo": db_product.images,
            "URL": db_product.url,
            "ДИЛЕР": db_product.dealer,
            "SKU": db_product.sku,
            "SEO title": db_product.seo_title,
            "SEO descr": db_product.seo_description,
            "SEO keywords": db_product.seo_keywords,
            "SEO alt": db_product.seo_alt,
            "Tabs:1": db_product.tab_one,
            "Tabs:2": db_product.tab_two,
        }

    def get_products_count(self) -> int:
        with self.get_session() as session:
            return session.query(ProductDB).count()

    def create_sql_dump(self, output_path: str) -> bool:
        try:
            with self.get_session() as session:
                products = session.query(ProductDB).all()

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write("-- SQL Dump of Products Database\n")
                    f.write(f"-- Generated at: {datetime.now().isoformat()}\n")
                    f.write(f"-- Total products: {len(products)}\n\n")

                    for product in products:
                        f.write(self._create_insert_statement(product))
                        f.write("\n")

                logger.bind(
                    service="DatabaseService",
                    output_path=output_path,
                    products_count=len(products),
                ).info("SQL dump created")
                return True

        except Exception as e:
            logger.bind(
                service="DatabaseService",
                output_path=output_path,
                error_type=type(e).__name__,
                error_message=str(e),
            ).error("Error creating SQL dump")
            return False

    def _create_insert_statement(self, product: ProductDB) -> str:
        fields = [
            "title",
            "category",
            "model",
            "year_of_release",
            "mileage",
            "transmission",
            "fuel",
            "engine_volume",
            "body",
            "color",
            "door_count",
            "seat_count",
            "owner_count",
            "price",
            "text",
            "images",
            "url",
            "dealer",
            "sku",
            "seo_title",
            "seo_description",
            "seo_keywords",
            "seo_alt",
            "tab_one",
            "tab_two",
            "created_at",
            "updated_at",
        ]

        values = [
            f"'{product.title or ''}'",
            f"'{product.category or ''}'",
            f"'{product.model or ''}'",
            f"'{product.year_of_release or ''}'",
            f"'{product.mileage or ''}'",
            f"'{product.transmission or ''}'",
            f"'{product.fuel or ''}'",
            f"'{product.engine_volume or ''}'",
            f"'{product.body or ''}'",
            f"'{product.color or ''}'",
            f"'{product.door_count or ''}'",
            f"'{product.seat_count or ''}'",
            f"'{product.owner_count or ''}'",
            f"'{product.price or ''}'",
            f"'{product.text or ''}'".replace("'", "''"),
            f"'{product.images or ''}'",
            f"'{product.url or ''}'",
            f"'{product.dealer or ''}'",
            f"'{product.sku}'",
            f"'{product.seo_title or ''}'".replace("'", "''"),
            f"'{product.seo_description or ''}'".replace("'", "''"),
            f"'{product.seo_keywords or ''}'".replace("'", "''"),
            f"'{product.seo_alt or ''}'".replace("'", "''"),
            f"'{product.tab_one or ''}'".replace("'", "''"),
            f"'{product.tab_two or ''}'".replace("'", "''"),
            f"'{product.created_at.isoformat()}'",
            f"'{product.updated_at.isoformat()}'",
        ]

        return f"INSERT INTO products ({', '.join(fields)}) VALUES ({', '.join(values)});"

    def clear_database(self) -> bool:
        try:
            with self.get_session() as session:
                session.query(ProductDB).delete()
                session.commit()
                logger.bind(service="DatabaseService").info(
                    "Database cleared successfully"
                )
                return True
        except Exception as e:
            logger.bind(
                service="DatabaseService",
                error_type=type(e).__name__,
                error_message=str(e),
            ).error("Error clearing database")
            return False
