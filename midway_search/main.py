import uvicorn

from src.backend import MidwaySearchBackendConfig, app


def main() -> None:
    config = MidwaySearchBackendConfig()
    uvicorn.run(
        app,
        host=config.app_host,
        port=config.app_port,
        # workers=1,
    )


if __name__ == "__main__":
    main()
