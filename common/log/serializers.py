import base64
import logging
import os
import traceback
from datetime import date, datetime, timezone
from enum import Enum
from functools import lru_cache
from typing import (
    Any,
    Callable,
    Dict,
    Hashable,
    Iterable,
    Mapping,
    Optional,
    Protocol,
    Type,
    TypeVar,
    cast,
)


def obj_path(obj: Any) -> str:
    """Return fully qualified import path of an object provided"""
    classname = obj.__qualname__
    if (module := obj.__module__) not in ("__main__", "builtins"):
        if not isinstance(module, str):
            module = "<unknown>"
        classname = f"{module}.{classname}"
    return classname


def obj_classname(obj: Any) -> str:
    """Return fully qualified import path of provided object class"""
    return obj_path(type(obj))


T = TypeVar("T")
DT = Dict[Type[T], Callable[[T], Any]]


class _PydanticModelProto(Protocol):
    def model_dump(self, *, mode: str) -> Dict[str, Any]: ...


class LogSerializer:
    def __init__(
        self,
        type_to_serializer: Optional[DT] = None,
        *,
        prepend_value_types: bool = False,
    ) -> None:
        self.type_to_serializer = (type_to_serializer or {}).copy()
        # https://rednafi.com/python/lru_cache_on_methods/
        self._get_serializer = lru_cache(typed=True)(self._get_serializer_inner)
        self._prepend_value_types = prepend_value_types
        self._pydantic_base_model = self._get_pydantic_base_model()

    @staticmethod
    def _get_pydantic_base_model() -> Optional[Type[_PydanticModelProto]]:
        try:
            from pydantic import BaseModel

            return BaseModel
        except ImportError:
            return None

    def serialize(self, record: logging.LogRecord) -> Dict[str, Any]:
        log = self.record2dict(record)
        log = self.extend_log(log)
        log = self._serialize(log)
        if self._prepend_value_types:
            log = _maybe_prepend_value_type(log)
        return log

    @staticmethod
    def record2dict(record: logging.LogRecord) -> Dict[str, Any]:
        log_record = record.__dict__.copy()
        log_record["msg"] = record.getMessage()
        exc_text = (log_record.get("exc_text") or "").strip()
        if record.exc_info and record.exc_info[1] and not exc_text:
            log_record["exc_text"] = "".join(
                traceback.format_exception_only(record.exc_info[0], record.exc_info[1])
            ).strip()
        if record.exc_info:
            log_record["exc_info"] = logging.Formatter().formatException(
                record.exc_info
            )
        return log_record

    @staticmethod
    def extend_log(log: Dict[str, Any]) -> Dict[str, Any]:
        t = datetime.fromtimestamp(log["created"], tz=timezone.utc)
        log.update(
            {
                "datetime": t,
                "year": t.year,
                "month": t.month,
                "day": t.day,
                "hour": t.hour,
                "minute": t.minute,
                "second": t.second,
                "pid": log.get("process", os.getpid()),
                "gpid": os.getpgid(os.getpid()),
                "extra": log.get("extra", {}),
            }
        )
        return log

    def _get_serializer_inner(self, value_type: type) -> Optional[Callable[..., Any]]:
        for type_, serializer in self.type_to_serializer.items():
            if issubclass(value_type, type_):
                return serializer
        return None

    def _serialize(self, value: Any) -> Any:  # noqa: PLR0911
        type_ = cast(Hashable, type(value))
        try:
            if (serializer := self._get_serializer(type_)) is not None:
                return serializer(value)
            if value is None:
                return None
            if isinstance(value, BaseException):
                return f"{obj_classname(value)}: {str(value)}"
            if isinstance(value, (bytes, bytearray)):
                try:
                    return value.decode("utf-8")
                except UnicodeDecodeError:
                    return base64.urlsafe_b64encode(value).decode("utf-8")
            if isinstance(value, Enum):
                return self._serialize(value.value)
            if self._pydantic_base_model and isinstance(
                value, self._pydantic_base_model
            ):
                return self._serialize(value.model_dump(mode="json"))
            if isinstance(value, (str, datetime, date, bool, int, float)):
                return value
            if isinstance(value, dict):
                return {
                    self._serialize(k): self._serialize(v) for k, v in value.items()
                }
            if isinstance(value, (set, list, tuple)):
                return [self._serialize(each) for each in value]
            return str(value)
        except Exception as e:  # noqa: BLE001
            return f"got error during serialization: {obj_classname(e)}: {str(e)}"


def _approximate_type(value: Any) -> str:  # noqa: PLR0911
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, (date, datetime)):
        return "date"
    if isinstance(value, Mapping):
        return "object"
    if isinstance(value, Iterable):
        return "array"
    return "unknown"


def _maybe_prepend_value_type(value: Any) -> Any:
    if isinstance(value, dict):
        prepended: Dict[Any, Any] = {}
        for k, v in value.items():
            if v is None:
                prepended[k] = v
            else:
                prepended[k] = {_approximate_type(v): _maybe_prepend_value_type(v)}
        return prepended
    if isinstance(value, list):
        return [_maybe_prepend_value_type(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_maybe_prepend_value_type(v) for v in value)
    if isinstance(value, set):
        return {_maybe_prepend_value_type(v) for v in value}
    return value
