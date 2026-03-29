from __future__ import annotations

from typing import Protocol

from src.domain.report_entities import WeeklyReport


class AdviceProvider(Protocol):
    def build_daily_advice(self, report: WeeklyReport) -> str:
        ...

