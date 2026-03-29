from __future__ import annotations

from typing import Protocol

from src.domain.analytics_entities import FinanceForecastReport


class FinanceAdviceProvider(Protocol):
    def build_finance_advice(self, report: FinanceForecastReport) -> tuple[str, str | None]:
        ...
