from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class InferenceRequest:
    user_message: str
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InferenceResponse:
    text: str
    backend_name: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseInferenceBackend(ABC):
    @abstractmethod
    def generate(self, request: InferenceRequest) -> InferenceResponse:
        raise NotImplementedError
