import json
from datetime import datetime
from typing import Dict, List

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from core.models.product_model import ProductModel
from shared.config.config_model import ConfigModel
from shared.models.database_model import Base, ProductDB


class DatabaseService:
    _instance = None
    _initialized = False

    def __new__(cls, config_obj: ConfigModel | None = None):
        if cls._instance is None:
            cls._instance = super(DatabaseService, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_obj: ConfigModel | None = None):
        if not self._initialized and config_obj is not None:
            self.db_path = config_obj.files.db_path
            self.config_obj = config_obj
            self.engine = create_engine(self.db_path, echo=False)
            self.SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine
            )

            Base.metadata.create_all(bind=self.engine)
            logger.bind(service="DatabaseService", db_path=self.db_path).info(
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

    def get_all_existing_skus(self) -> set[str]:
        try:
            with self.get_session() as session:
                skus = session.query(ProductDB.sku).all()
                return {sku[0] for sku in skus}
        except Exception as e:
            logger.bind(
                service="DatabaseService",
                error_type=type(e).__name__,
                error_message=str(e),
            ).error("Failed to get existing SKUs")
            return set()

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
        return ProductDB(
            title=product.formatted_title,
            category=product.category,
            model=product.processed_model,
            year_of_release=product.year_of_release,
            mileage=product.mileage,
            transmission=product.processed_transmission,
            fuel=product.processed_fuel,
            engine_volume=product.engine_volume,
            body=product.processed_body,
            color=product.processed_color,
            door_count=product.processed_door_count,
            seat_count=product.seat_count,
            owner_count=product.owner_count,
            price=product.price,
            text=product.processed_text,
            images=product.processed_images_string,
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
        images_field = (
            str(db_product.images) if db_product.images is not None else ""
        )

        if (
            images_field
            and isinstance(images_field, str)
            and images_field.startswith("[")
            and images_field.endswith("]")
        ):
            try:
                images_list = json.loads(images_field)
                if isinstance(images_list, list):
                    clean_images = [
                        img.strip()
                        for img in images_list
                        if img and img.strip()
                    ]
                    images_field = ",".join(clean_images)
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            self.config_obj.database.title: db_product.title,
            self.config_obj.database.category: db_product.category,
            self.config_obj.database.model: db_product.model,
            self.config_obj.database.year_of_release: db_product.year_of_release,
            self.config_obj.database.mileage: db_product.mileage,
            self.config_obj.database.transmission: db_product.transmission,
            self.config_obj.database.fuel: db_product.fuel,
            self.config_obj.database.engine_volume: db_product.engine_volume,
            self.config_obj.database.body: db_product.body,
            self.config_obj.database.color: db_product.color,
            self.config_obj.database.door_count: db_product.door_count,
            self.config_obj.database.seat_count: db_product.seat_count,
            self.config_obj.database.owner_count: db_product.owner_count,
            self.config_obj.database.price: db_product.price,
            self.config_obj.database.text: db_product.text,
            self.config_obj.database.images: images_field,
            self.config_obj.database.url: db_product.url,
            self.config_obj.database.dealer: db_product.dealer,
            self.config_obj.database.sku: db_product.sku,
            self.config_obj.database.seo_title: db_product.seo_title,
            self.config_obj.database.seo_description: db_product.seo_description,
            self.config_obj.database.seo_keywords: db_product.seo_keywords,
            self.config_obj.database.seo_alt: db_product.seo_alt,
            self.config_obj.database.tab_one: db_product.tab_one,
            self.config_obj.database.tab_two: db_product.tab_two,
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
