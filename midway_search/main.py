import uvicorn
from prometheus_client import start_http_server

from src.backend import MidwaySearchBackendConfig, app


def main() -> None:
    config = MidwaySearchBackendConfig()
    start_http_server(config.prometheus.port, addr=config.prometheus.host)
    uvicorn.run(
        app,
        host=config.app_host,
        port=config.app_port,
        # workers=1,
    )


if __name__ == "__main__":
    main()
