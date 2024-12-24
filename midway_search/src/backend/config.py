from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class PrometheusMetricsConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8090
    app_name: str = "midway_search"


class MidwaySearchBackendConfig(BaseSettings):
    app_host: str = "0.0.0.0"
    app_port: int = 7866
    prometheus: PrometheusMetricsConfig
    basesearch_endpoint: str = "http://0.0.0.0:7867/get_documents"

    model_config = SettingsConfigDict(
        env_prefix="MIDWAY_SEARCH_BACKEND__",
        env_ignore_empty=True,
        env_nested_delimiter="__",
    )

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
