import logging
import sys
from typing import Any, Dict, List, Optional, Union

from loguru import logger


__all__ = ("setup_logging", "get_logger")


SinkType = Union[logging.Handler, Dict[str, Any]]


def _define_sink(sink_config: SinkType, sink_kwargs: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(sink_config, dict):
        return sink_config
    return {**sink_kwargs, "sink": sink_config}


def _default_formatter(*args: Any, **kwargs: Any) -> str:  # noqa: ARG001
    return "{message}"


def setup_logging(
    logger_name: Optional[str] = None,
    log_level: Union[int, str] = logging.INFO,
    extra_handlers: Optional[List[SinkType]] = None,
    extra_sink_kwargs: Optional[Dict[str, Any]] = None,
):
    """Setup log handlers for loguru logger. Every call to `setup_logging`
    is destructive in the sense that it removes all previously added loguru
    handlers.

    If (and only if) no `extra_handlers` were provided, default stream handler
    is used. Default stream handler writes logs to stdout using a pipe delimited
    format. Configuration of any MongoDB arguments doesn't affect whether
    the default handler is added or not.

    Args:
        logger_name: Logger name for loguru, leave it unspecified unless
            you know why you need a logger with a different name.
        log_level: Logging level to use for the configured sinks.
        extra_handlers: Extra handlers to configure for loguru logger.
            2 formats are accepted:
            (a) an instance of `logging.Logger`
            (b) a dictionary with keyword arguments for `loguru.add()`
        extra_sink_kwargs: Optional extra keyword arguments, which will only
            be added to handlers from `extra_handlers` list if such extra handler
            was passed as an instance of `logging.Logger` (i.e. in format (a)).

    """

    _logger = logger.bind(logger_name=logger_name) if logger_name else logger

    setup_third_party_loggers()

    sink_kwargs = {
        "level": log_level,
        # fix for https://github.com/Delgan/loguru/issues/1081#issuecomment-1949894683
        "format": _default_formatter,
        "diagnose": False,  # do not print local variables in the exception trace
        "catch": True,  # catch logging failures and prevent the client crash
        **(extra_sink_kwargs or {}),
    }
    extra_handlers = extra_handlers or []
    handlers: List[Dict[str, Any]] = [
        _define_sink(handler, sink_kwargs) for handler in extra_handlers
    ]
    if not extra_handlers:
        handlers.append(setup_default_sink(sink_kwargs))

    _logger.configure(handlers=handlers)
    return _logger


def setup_default_sink(sink_kwargs: Dict[str, Any]) -> Dict[str, Any]:
    log_format_fstyle = (
        "[{time:YYYY-MM-DDTHH:mm:ss zz!UTC} | {level} | {process} | {file}:{line} |"
        " {function}() | extra={extra}] {message}"
    )
    return {**sink_kwargs, "sink": sys.stdout, "format": log_format_fstyle}


def setup_third_party_loggers() -> None:
    logging.disable(logging.DEBUG)
    logging.getLogger("pika").setLevel(logging.ERROR)


def get_logger(logger_name: Optional[str] = None):
    return logger.bind(logger_name=logger_name) if logger_name else logger
