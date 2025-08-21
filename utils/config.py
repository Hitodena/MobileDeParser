from pathlib import Path
from typing import Optional

import yaml

from models.config_model import ConfigModel


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
            root = Path(__file__).parent.parent.resolve()
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

    def _load_config(self) -> None:
        with open(self._config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)

        self._config = ConfigModel(**config)

    @property
    def config(self) -> ConfigModel:
        return self._config


config_loader = ConfigLoader("configuration_dev.yaml")
config = config_loader.config
