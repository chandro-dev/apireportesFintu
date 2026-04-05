from __future__ import annotations

from datetime import datetime
from typing import Protocol

from src.domain.report_entities import AccountMovementPoint, CategoryPoint, DailyPoint


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
