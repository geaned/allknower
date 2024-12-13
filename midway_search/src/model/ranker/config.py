from __future__ import annotations

from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class TokenizerConfig(BaseModel):
    tokenizer_path: str
    lower: bool = True
    stopwords: str = "english"


class RankerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    catboost_ranker_path: str
    tokenizer_config: TokenizerConfig
    processes_num: int = 10

    @classmethod
    def from_file(cls, config_file_path: str) -> RankerConfig:
        with open(config_file_path) as config_file:
            return cls.model_validate_json(config_file.read())

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],  # noqa: ARG003
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return env_settings, dotenv_settings, file_secret_settings, init_settings
