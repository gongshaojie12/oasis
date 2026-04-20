from __future__ import annotations
from enum import Enum
from typing import Any
from pydantic import BaseModel
import time


class MessageType(str, Enum):
    COMMAND = "command"
    EVENT = "event"
    DATA = "data"
    STATUS = "status"


class WSMessage(BaseModel):
    type: str
    payload: dict[str, Any] = {}
    timestamp: float = 0.0

    def __init__(self, **data):
        if "timestamp" not in data or data["timestamp"] == 0.0:
            data["timestamp"] = time.time()
        super().__init__(**data)


class CommandType(str, Enum):
    PAUSE = "command:pause"
    RESUME = "command:resume"
    SPEED = "command:speed"
    INJECT = "command:inject"
    STEP = "command:step"


class DataType(str, Enum):
    POST = "data:post"
    ACTION = "data:action"
    METRICS = "data:metrics"
    HEALTH = "data:health"
