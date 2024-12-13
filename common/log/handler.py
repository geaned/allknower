import datetime as dt
import json
import logging
from typing import Any, Optional


from common.log.serializers import LogSerializer


class StreamJsonHandler(logging.StreamHandler):
    def __init__(
        self, stream: Optional[Any] = None, *, prepend_value_types: bool = False
    ) -> None:
        super().__init__(stream=stream)
        self.serializer = LogSerializer(
            type_to_serializer={
                dt.datetime: lambda x: x.isoformat(),
                dt.date: lambda x: x.isoformat(),
            },
            prepend_value_types=prepend_value_types,
        )

    def format(self, record: logging.LogRecord) -> str:
        serialized_record = self.serializer.serialize(record)
        return json.dumps(serialized_record)
