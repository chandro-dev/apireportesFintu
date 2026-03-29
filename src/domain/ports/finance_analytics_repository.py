from __future__ import annotations

from datetime import datetime
from typing import Protocol

from src.domain.analytics_entities import AccountTypeMetric, TransactionTypeMetric
from src.domain.report_entities import CategoryPoint, DailyPoint


class FinanceAnalyticsRepository(Protocol):
    def fetch_daily_history(
        self,
        *,
        user_id: str,
        start_inclusive: datetime,
        end_exclusive: datetime,
        timezone_name: str,
    ) -> list[DailyPoint]:
        ...

    def fetch_account_type_breakdown(
        self,
        *,
        user_id: str,
        start_inclusive: datetime,
        end_exclusive: datetime,
    ) -> list[AccountTypeMetric]:
        ...

    def fetch_transaction_type_breakdown(
        self,
        *,
        user_id: str,
        start_inclusive: datetime,
        end_exclusive: datetime,
    ) -> list[TransactionTypeMetric]:
        ...

    def fetch_expense_category_breakdown(
        self,
        *,
        user_id: str,
        start_inclusive: datetime,
        end_exclusive: datetime,
        limit: int,
    ) -> list[CategoryPoint]:
        ...

    def fetch_total_current_balance(self, *, user_id: str) -> float | None:
        ...
