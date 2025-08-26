import csv
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List

from loguru import logger

from core.models.product_model import ProductModel
from shared.config.config_model import ConfigModel


def read_csv_file(file_path: Path, delimiter: str = ";"):
    encodings = ["utf-8-sig", "utf-8", "cp1251", "latin-1"]

    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
                if content.startswith("\ufeff"):
                    content = content[1:]

                lines = content.splitlines()
                reader = csv.DictReader(lines, delimiter=delimiter)

                rows = list(reader)
                return rows

        except UnicodeDecodeError as e:
            logger.error(f"UnicodeDecodeError: {e}")
            continue
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            continue

    return []


def save_products_to_files(
    products: List[ProductModel], config: ConfigModel
) -> List[Path]:
    if not products:
        logger.warning("No products to save")
        return []

    lines_limit = config.files.lines_limit
    files_dir = config.files.files_dir

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    temp_dir = files_dir / f"temp_{timestamp}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    created_files = []

    try:
        total_products = len(products)
        logger.info(
            f"Starting to save {total_products} products with limit {lines_limit} per file"
        )

        for i in range(0, total_products, lines_limit):
            chunk = products[i : i + lines_limit]
            chunk_number = (i // lines_limit) + 1

            filename = f"products_part_{chunk_number:03d}_{timestamp}.csv"
            file_path = temp_dir / filename

            _save_products_chunk_to_csv(chunk, file_path)
            created_files.append(file_path)

            logger.info(
                f"Saved chunk {chunk_number}: {len(chunk)} products to {file_path}"
            )

        archive_name = f"products_{timestamp}.zip"
        archive_path = files_dir / archive_name

        _create_archive(created_files, archive_path)
        logger.info(f"Created archive: {archive_path}")

        for file_path in created_files:
            file_path.unlink()

        temp_dir.rmdir()

        return [archive_path]

    except Exception as e:
        logger.error(f"Error saving products to files: {e}")
        for file_path in created_files:
            if file_path.exists():
                file_path.unlink()
        if temp_dir.exists():
            temp_dir.rmdir()
        raise


def _save_products_chunk_to_csv(
    products: List[ProductModel], file_path: Path
) -> None:
    if not products:
        return

    first_product_dict = products[0].to_csv_dict()
    if not first_product_dict:
        logger.warning(
            "First product returned empty dictionary, skipping chunk"
        )
        return

    fieldnames = list(first_product_dict.keys())

    try:
        with open(file_path, "w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.DictWriter(
                csvfile, fieldnames=fieldnames, delimiter=";"
            )
            writer.writeheader()

            for product in products:
                product_dict = product.to_csv_dict()
                if product_dict:
                    writer.writerow(product_dict)

        logger.debug(
            f"Successfully saved {len(products)} products to {file_path}"
        )

    except Exception as e:
        logger.error(f"Error saving products chunk to CSV: {e}")
        raise


def _create_archive(file_paths: List[Path], archive_path: Path) -> None:
    try:
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in file_paths:
                if file_path.exists():
                    zipf.write(file_path, file_path.name)
                    logger.debug(f"Added {file_path.name} to archive")

        logger.info(f"Archive created successfully: {archive_path}")

    except Exception as e:
        logger.error(f"Error creating archive: {e}")
        raise
