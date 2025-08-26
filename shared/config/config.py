from pathlib import Path
from typing import Dict, List, Optional

import yaml
from loguru import logger

from shared.config.config_model import ConfigModel, DataConfig
from shared.utils.storage_management import read_csv_file


class ConfigLoader:
    _instance: Optional["ConfigLoader"] = None
    _initialized: bool = False

    def __new__(cls, config_path: str | None = None) -> "ConfigLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_path: str | None = None) -> None:
        if self._initialized:
            return

        if config_path is None:
            root = Path(__file__).parent.parent.parent.resolve()
            self._config_path = root / "configuration.yaml"
            if not self._config_path.exists():
                raise FileNotFoundError(
                    f"Config file does not exist: {self._config_path}"
                )
        elif isinstance(config_path, str):
            self._config_path = Path(config_path).resolve()
            if not self._config_path.exists():
                raise FileNotFoundError(
                    f"Config file does not exist: {self._config_path}"
                )

        self._load_config()
        self._initialized = True
        logger.success("Config initialized successfully")

    def _load_config(self) -> None:
        with open(self._config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)

        self._config = ConfigModel(**config)
        self._load_csv_data()

    def _load_csv_data(self) -> None:
        replacement_rules = self._load_replacement_rules()
        dealer_exclusions = self._load_dealer_exclusions()
        image_exclusions = self._load_image_exclusions()
        brand_exclusions = self._load_brand_exclusions()
        self._config.data = DataConfig(
            replacement_rules=replacement_rules,
            dealer_exclusions=dealer_exclusions,
            image_exclusions=image_exclusions,
            brand_exclusions=brand_exclusions,
        )

    def _load_replacement_rules(self) -> Dict[str, str]:
        replacements = {}
        file_path = self._config.files.replaces_file
        try:
            rows = read_csv_file(file_path)
            loaded_count = 0
            for row in rows:
                original = row.get("НАЗВАНИЕ", "")
                replacement = row.get("ЗАМЕНА", "")
                if original and replacement:
                    replacements[original] = replacement
                    loaded_count += 1
            logger.debug(
                "Text replacement rules loaded successfully",
                rules_count=loaded_count,
                file_path=str(file_path),
            )
        except FileNotFoundError:
            logger.warning(
                "Replacement rules file not found", file_path=str(file_path)
            )
        except Exception as e:
            logger.error(
                "Failed to load replacement rules",
                error=str(e),
                error_type=type(e).__name__,
                file_path=str(file_path),
            )
        return replacements

    def _load_dealer_exclusions(self) -> List[str]:
        exclusions = []
        file_path = self._config.files.dealer_excludes_file
        try:
            rows = read_csv_file(file_path)
            loaded_count = 0
            for row in rows:
                dealer = row.get("ДИЛЕР", "").strip()
                if dealer:
                    exclusions.append(dealer)
                loaded_count += 1
            if loaded_count == 0:
                logger.warning(
                    "No dealer exclusions found", file_path=str(file_path)
                )
            logger.debug(
                "Dealer exclusions loaded successfully",
                exclusions_count=loaded_count,
                file_path=str(file_path),
            )
        except Exception as e:
            logger.error(
                "Failed to load dealer exclusions",
                error=str(e),
                error_type=type(e).__name__,
                file_path=str(file_path),
            )
        return exclusions

    def _load_image_exclusions(self) -> Dict[str, Dict[str, str]]:
        exclusions = {}
        file_path = self._config.files.dealer_exclude_images_file
        try:
            rows = read_csv_file(file_path)
            loaded_count = 0
            for row in rows:
                dealer = row.get("ДИЛЕР", "").strip()
                if dealer:
                    exclusions[dealer] = {
                        "start": row.get("НАЧАЛО", "1"),
                        "penultimate": row.get("ПРЕДПОСЛЕДНЯЯ", "*"),
                        "last": row.get("ПОСЛЕДНЯЯ", "*"),
                    }
                loaded_count += 1
            if loaded_count == 0:
                logger.warning(
                    "No image exclusions found", file_path=str(file_path)
                )
            logger.debug(
                "Image exclusion rules loaded successfully",
                rules_count=loaded_count,
                file_path=str(file_path),
            )
        except Exception as e:
            logger.error(
                "Failed to load image exclusions",
                error=str(e),
                error_type=type(e).__name__,
                file_path=str(file_path),
            )
        return exclusions

    def _load_brand_exclusions(self) -> List[str]:
        exclusions = []
        file_path = self._config.files.brand_excludes_file
        try:
            rows = read_csv_file(file_path)
            loaded_count = 0
            for row in rows:
                brand = row.get("МАРКИ", "").strip()
                if brand:
                    exclusions.append(brand)
                loaded_count += 1
            if loaded_count == 0:
                logger.warning(
                    "No brand exclusions found", file_path=str(file_path)
                )
            logger.debug(
                "Brand exclusions loaded successfully",
                exclusions_count=loaded_count,
                file_path=str(file_path),
            )
        except Exception as e:
            logger.error(
                "Failed to load brand exclusions",
                error=str(e),
                error_type=type(e).__name__,
                file_path=str(file_path),
            )
        return exclusions

    @property
    def config(self) -> ConfigModel:
        return self._config


config_loader = ConfigLoader("configuration_dev.yaml")
config = config_loader.config
