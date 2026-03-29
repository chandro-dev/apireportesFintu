from __future__ import annotations

from datetime import datetime, timezone


class GetHealthStatusUseCase:
    def execute(self) -> dict[str, str]:
        return {
            "status": "ok",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }

