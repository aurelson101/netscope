from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiscoveryResult:
    source: str
    target: str
    raw: dict[str, Any]
    facts: list[dict[str, Any]] = field(default_factory=list)


class DiscoveryPlugin(ABC):
    name: str

    @abstractmethod
    async def discover(self, target: str, options: dict) -> list[DiscoveryResult]: ...
