from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class MidwaySearchBackendConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MIDWAY_SEARCH_BACKEND__",
        env_ignore_empty=True,
        env_nested_delimiter="__",
    )

    app_host: str = "0.0.0.0"
    app_port: int = 7866
    basesearch_endpoint: str = "http://0.0.0.0:7867/get_documents"

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
