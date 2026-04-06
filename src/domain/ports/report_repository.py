from __future__ import annotations

from datetime import datetime
from typing import Protocol

from src.domain.report_entities import (
    AccountBalancePoint,
    AccountMovementPoint,
    CategoryPoint,
    DailyPoint,
    OutgoingTransactionPoint,
)


class ReportRepository(Protocol):
    def fetch_daily_overview(
        self,
        *,
        user_id: str,
        week_start: datetime,
        week_end_exclusive: datetime,
        timezone_name: str,
    ) -> list[DailyPoint]:
        ...

    def fetch_expense_categories(
        self,
        *,
        user_id: str,
        week_start: datetime,
        week_end_exclusive: datetime,
    ) -> list[CategoryPoint]:
        ...

    def fetch_category_breakdown(
        self,
        *,
        user_id: str,
        start_inclusive: datetime,
        end_exclusive: datetime,
        flow: str,
        limit: int,
    ) -> list[CategoryPoint]:
        ...

    def fetch_account_movement(
        self,
        *,
        user_id: str,
        start_inclusive: datetime,
        end_exclusive: datetime,
        limit: int,
    ) -> list[AccountMovementPoint]:
        ...

    def fetch_normal_accounts_balances(self, *, user_id: str) -> list[AccountBalancePoint]:
        ...

    def fetch_credit_cards_total_debt(self, *, user_id: str) -> float:
        ...

    def fetch_recent_outgoing_normal_transactions(
        self,
        *,
        user_id: str,
        end_exclusive: datetime,
        timezone_name: str,
        limit: int,
    ) -> list[OutgoingTransactionPoint]:
        ...
