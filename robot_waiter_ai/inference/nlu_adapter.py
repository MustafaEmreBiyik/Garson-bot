from __future__ import annotations

from abc import ABC, abstractmethod

from .nlu_schema import ParsedUserIntent


class BaseNLUAdapter(ABC):
    @abstractmethod
    def parse(self, message: str) -> ParsedUserIntent:
        raise NotImplementedError
