from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiContract:
    method: str
    path: str
    lifecycle: str
    capability: str
    owner_service: str
    description: str

    def to_dict(self) -> dict[str, str]:
        return {
            "method": self.method,
            "path": self.path,
            "lifecycle": self.lifecycle,
            "capability": self.capability,
            "owner_service": self.owner_service,
            "description": self.description,
        }

