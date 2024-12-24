from http import HTTPStatus


class ServiceError(Exception):
    detail: str = "Unknown error"
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, detail: str | None = None) -> None:
        if detail:
            self.detail = detail


class NoDocumentsFoundError(ServiceError):
    pass


class RankingError(ServiceError):
    pass
