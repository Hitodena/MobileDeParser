from shared.config.config_model import ConfigModel


class BotConfig(ConfigModel):

    @property
    def token(self) -> str:
        return self.api.telegram

    @property
    def allowed_users(self) -> set[int]:
        return self.api.tg_users

    def is_user_allowed(self, user_id: int) -> bool:
        return user_id in self.allowed_users

    @classmethod
    def from_config_model(cls, config: ConfigModel) -> "BotConfig":
        return cls.model_validate(config.model_dump())
