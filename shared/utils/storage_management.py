import csv
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger

from shared.config.config_model import ConfigModel
from shared.services.database_service import DatabaseService


def read_csv_file(file_path: Path, delimiter: str = ";"):
    encodings = [
        "utf-8-sig",
    ]
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
            logger.bind(
                service="StorageManagement",
                file_path=str(file_path),
                encoding=encoding,
                error_type=type(e).__name__,
                error_message=str(e),
            ).error("UnicodeDecodeError")
            continue
        except Exception as e:
            logger.bind(
                service="StorageManagement",
                file_path=str(file_path),
                encoding=encoding,
                error_type=type(e).__name__,
                error_message=str(e),
            ).error("Error reading CSV file")
            continue

    return []


def save_products_from_database(
    config: ConfigModel,
) -> Optional[Tuple[Path, int]]:
    db_service = DatabaseService(config.files.db_path)
    db_products = db_service.get_all_products()

    if not db_products:
        logger.bind(service="StorageManagement").warning(
            "No products in database to export"
        )
        return None

    lines_limit = config.files.lines_limit
    files_dir = config.files.files_dir

    timestamp = datetime.now().strftime("%Y_%m_%d")
    temp_dir = files_dir / f"temp_{timestamp}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    created_files = []
    total_saved_products = 0

    try:
        total_products = len(db_products)
        logger.bind(
            service="StorageManagement",
            total_products=total_products,
            lines_limit=lines_limit,
        ).info("Starting to save products from database")

        for i in range(0, total_products, lines_limit):
            chunk = db_products[i : i + lines_limit]
            chunk_number = (i // lines_limit) + 1

            filename = f"mobile_{chunk_number:03d}__{timestamp}.csv"
            file_path = temp_dir / filename

            saved_in_chunk = _save_dict_chunk_to_csv(chunk, file_path)
            total_saved_products += saved_in_chunk

            if saved_in_chunk > 0:
                created_files.append(file_path)
                logger.bind(
                    service="StorageManagement",
                    chunk_number=chunk_number,
                    saved_in_chunk=saved_in_chunk,
                    file_path=str(file_path),
                ).info("Saved chunk")
            else:
                logger.bind(
                    service="StorageManagement", chunk_number=chunk_number
                ).warning("Chunk: no valid products to save")

        if not created_files:
            logger.bind(service="StorageManagement").warning(
                "No valid products to save, cleaning up temp directory"
            )
            temp_dir.rmdir()
            return None

        archive_name = f"mobile_{timestamp}.zip"
        archive_path = files_dir / archive_name

        _create_archive(created_files, archive_path)
        logger.bind(
            service="StorageManagement", archive_path=str(archive_path)
        ).info("Created archive")

        if archive_path.exists():
            for file_path in created_files:
                if file_path.exists():
                    file_path.unlink()
            temp_dir.rmdir()
            logger.bind(service="StorageManagement").info(
                "Temporary files cleaned up"
            )
        else:
            logger.bind(
                service="StorageManagement", archive_path=str(archive_path)
            ).error("Archive was not created, keeping temporary files")
            raise FileNotFoundError(f"Archive was not created: {archive_path}")

        return archive_path, total_saved_products

    except Exception as e:
        logger.bind(
            service="StorageManagement",
            error_type=type(e).__name__,
            error_message=str(e),
        ).error("Error saving products from database")
        for file_path in created_files:
            if file_path.exists():
                file_path.unlink()
        if temp_dir.exists():
            temp_dir.rmdir()
        raise


def _save_dict_chunk_to_csv(products: List[Dict], file_path: Path) -> int:
    if not products:
        return 0

    first_product_dict = None
    valid_products = []

    for product in products:
        if product:
            if first_product_dict is None:
                first_product_dict = product
            valid_products.append(product)

    if not first_product_dict:
        logger.bind(service="StorageManagement").warning(
            "No valid products found in chunk, skipping"
        )
        return 0

    fieldnames = list(first_product_dict.keys())
    saved_count = len(valid_products)

    try:
        with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(
                csvfile, fieldnames=fieldnames, delimiter=";"
            )
            writer.writeheader()

            for product_dict in valid_products:
                writer.writerow(product_dict)

        logger.bind(
            service="StorageManagement",
            saved_count=saved_count,
            file_path=str(file_path),
        ).debug("Successfully saved products to CSV")

    except Exception as e:
        logger.bind(
            service="StorageManagement",
            file_path=str(file_path),
            error_type=type(e).__name__,
            error_message=str(e),
        ).error("Error saving products chunk to CSV")
        raise

    return saved_count


def _create_archive(file_paths: List[Path], archive_path: Path) -> None:
    try:
        logger.bind(
            service="StorageManagement",
            archive_path=str(archive_path),
            files_count=len(file_paths),
        ).info("Creating archive")

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in file_paths:
                if file_path.exists():
                    zipf.write(file_path, file_path.name)
                    logger.bind(
                        service="StorageManagement", file_name=file_path.name
                    ).debug("Added file to archive")
                else:
                    logger.bind(
                        service="StorageManagement", file_path=str(file_path)
                    ).warning("File not found")

        if archive_path.exists():
            archive_size = archive_path.stat().st_size
            logger.bind(
                service="StorageManagement",
                archive_path=str(archive_path),
                archive_size=archive_size,
            ).info("Archive created successfully")
        else:
            raise FileNotFoundError(f"Archive was not created: {archive_path}")

    except Exception as e:
        logger.bind(
            service="StorageManagement",
            archive_path=str(archive_path),
            error_type=type(e).__name__,
            error_message=str(e),
        ).error("Error creating archive")
        raise
