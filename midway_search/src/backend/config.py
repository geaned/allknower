from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class QueryEmbedderAPIConfig(BaseSettings):
    text_endpoint: str = "http://195.70.199.13:8766/embed/texts"
    image_endpoint: str = "http://195.70.199.13:8765/embed/texts"


class BaseSearchAPIConfig(BaseSettings):
    base_url: str = "http://0.0.0.0:7867"
    full_text_search_enpoint: str = "full_text_search"
    vector_search_endpoint: str = "vector_search"


class PrometheusMetricsConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8090
    app_name: str = "midway_search"


class MidwaySearchBackendConfig(BaseSettings):
    app_host: str = "0.0.0.0"
    app_port: int = 7866
    prometheus: PrometheusMetricsConfig
    query_embedder: QueryEmbedderAPIConfig
    basesearch: BaseSearchAPIConfig
    blender_api_enpoint: str

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
