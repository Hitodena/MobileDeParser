import csv
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger

from shared.config.config_model import ConfigModel

# Telegram bot maximum file size is 50MB, we use 48MB as safety margin
MAX_ARCHIVE_SIZE_BYTES = 48 * 1024 * 1024


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


async def save_products_from_database(
    config: ConfigModel,
) -> Optional[Tuple[List[Path], int]]:
    """Export products from database to CSV archives using streaming.

    Returns:
        Optional[Tuple[List[Path], int]]: List of archive paths and total saved count,
            or None if no products found.

    Note:
        - Uses streaming to avoid loading all products into memory
        - CSV files split by line count (lines_limit)
        - Archives split by total size (48MB limit)
    """
    from shared.services.database_service import DatabaseService

    db_service = DatabaseService(config)

    # Check if any products exist
    total_products = db_service.get_products_count_streaming()
    if total_products == 0:
        logger.bind(service="StorageManagement").warning(
            "No products in database to export"
        )
        return None

    lines_limit = config.files.lines_limit
    files_dir = config.files.files_dir

    timestamp = datetime.now().strftime("%Y_%m_%d")
    temp_dir = files_dir / f"temp_{timestamp}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    created_files: List[Path] = []
    total_saved_products = 0

    try:
        logger.bind(
            service="StorageManagement",
            total_products=total_products,
            lines_limit=lines_limit,
        ).info(
            "Starting to save products from database (line-based CSV, size-based archives)"
        )

        # Stream products in chunks by line count
        current_chunk: List[Dict] = []
        chunk_number = 0

        for product in db_service.get_all_products_streaming():
            current_chunk.append(product)

            if len(current_chunk) >= lines_limit:
                chunk_number += 1
                filename = f"mobile_{chunk_number:03d}__{timestamp}.csv"
                file_path = temp_dir / filename

                saved_in_chunk = _save_dict_chunk_to_csv(
                    current_chunk, file_path
                )
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

                current_chunk = []

        # Save remaining products in the last chunk
        if current_chunk:
            chunk_number += 1
            filename = f"mobile_{chunk_number:03d}__{timestamp}.csv"
            file_path = temp_dir / filename

            saved_in_chunk = _save_dict_chunk_to_csv(current_chunk, file_path)
            total_saved_products += saved_in_chunk

            if saved_in_chunk > 0:
                created_files.append(file_path)
                logger.bind(
                    service="StorageManagement",
                    chunk_number=chunk_number,
                    saved_in_chunk=saved_in_chunk,
                    file_path=str(file_path),
                ).info("Saved final chunk")

        if not created_files:
            logger.bind(service="StorageManagement").warning(
                "No valid products to save, cleaning up temp directory"
            )
            temp_dir.rmdir()
            return None

        # Log final stats
        logger.bind(
            service="StorageManagement",
            total_files=len(created_files),
            total_products=total_saved_products,
        ).info("All CSV files created")

        # Create archives, grouping multiple CSV files until 48MB limit is reached
        archive_paths = _create_archives_split(
            created_files, files_dir, timestamp
        )

        # Clean up temporary CSV files
        for file_path in created_files:
            if file_path.exists():
                file_path.unlink()
        temp_dir.rmdir()
        logger.bind(service="StorageManagement").info(
            "Temporary files cleaned up"
        )

        return archive_paths, total_saved_products

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


def _create_archives_split(
    file_paths: List[Path], files_dir: Path, timestamp: str
) -> List[Path]:
    """Create archives, splitting into multiple files if any archive exceeds 48MB.

    Args:
        file_paths: List of CSV file paths to add to archives
        files_dir: Directory to save archives
        timestamp: Timestamp string for archive naming

    Returns:
        List of archive paths created
    """
    # Filter existing files
    existing_files = [f for f in file_paths if f.exists()]

    if not existing_files:
        logger.bind(service="StorageManagement").warning("No files to archive")
        return []

    # Calculate average file size for estimation
    total_size = sum(f.stat().st_size for f in existing_files)
    avg_file_size = total_size / len(existing_files) if existing_files else 0

    # CSV files compress very well (typically to 30-35% of original size)
    # Using 35% as conservative estimate for better packing
    estimated_compression_ratio = 0.35
    max_files_per_archive = (
        int(
            MAX_ARCHIVE_SIZE_BYTES
            / (avg_file_size * estimated_compression_ratio)
        )
        if avg_file_size > 0
        else len(existing_files)
    )

    # Ensure at least 1 file per archive
    max_files_per_archive = max(1, max_files_per_archive)

    archive_paths: List[Path] = []
    archive_part_number = 1

    # Split files into groups based on estimated size
    for i in range(0, len(existing_files), max_files_per_archive):
        group = existing_files[i : i + max_files_per_archive]

        # Create archive with this group
        archive_name = f"mobile_{timestamp}_part{archive_part_number:02d}.zip"
        archive_path = files_dir / archive_name
        _create_archive(group, archive_path)
        archive_paths.append(archive_path)

        logger.bind(
            service="StorageManagement",
            archive_path=str(archive_path),
            part_number=archive_part_number,
            files_count=len(group),
        ).info("Created archive part")

        archive_part_number += 1

    logger.bind(
        service="StorageManagement",
        total_archives=len(archive_paths),
    ).info("All archives created")

    return archive_paths
