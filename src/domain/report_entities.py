from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DailyPoint:
    date: str
    income: float
    expense: float
    net: float
    transactions_count: int

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "income": self.income,
            "expense": self.expense,
            "net": self.net,
            "transactions_count": self.transactions_count,
        }


@dataclass(frozen=True)
class CategoryPoint:
    category_name: str
    amount: float
    transactions_count: int

    def to_dict(self) -> dict:
        return {
            "category_name": self.category_name,
            "amount": self.amount,
            "transactions_count": self.transactions_count,
        }


@dataclass(frozen=True)
class AccountMovementPoint:
    account_id: str
    account_name: str
    account_type: str
    income: float
    expense: float
    net: float
    total_movement: float
    transactions_count: int

    def to_dict(self) -> dict:
        return {
            "account_id": self.account_id,
            "account_name": self.account_name,
            "account_type": self.account_type,
            "income": self.income,
            "expense": self.expense,
            "net": self.net,
            "total_movement": self.total_movement,
            "transactions_count": self.transactions_count,
        }


@dataclass(frozen=True)
class WeeklySummary:
    income: float
    expense: float
    net: float
    transactions_count: int

    def to_dict(self) -> dict:
        return {
            "income": self.income,
            "expense": self.expense,
            "net": self.net,
            "transactions_count": self.transactions_count,
        }


@dataclass(frozen=True)
class DailySummary:
    day: str
    income: float
    expense: float
    net: float
    transactions_count: int

    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "income": self.income,
            "expense": self.expense,
            "net": self.net,
            "transactions_count": self.transactions_count,
        }


@dataclass(frozen=True)
class DailyComparison:
    previous_day: str
    income_delta: float
    expense_delta: float
    net_delta: float

    def to_dict(self) -> dict:
        return {
            "previous_day": self.previous_day,
            "income_delta": self.income_delta,
            "expense_delta": self.expense_delta,
            "net_delta": self.net_delta,
        }


@dataclass(frozen=True)
class DailyReport:
    user_id: str
    timezone: str
    generated_at_utc: str
    summary: DailySummary
    comparison: DailyComparison
    top_expense_categories: list[CategoryPoint]
    top_income_categories: list[CategoryPoint]
    top_accounts_movement: list[AccountMovementPoint]
    insights: list[str]

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "timezone": self.timezone,
            "generated_at_utc": self.generated_at_utc,
            "summary": self.summary.to_dict(),
            "comparison_vs_previous_day": self.comparison.to_dict(),
            "top_expense_categories": [row.to_dict() for row in self.top_expense_categories],
            "top_income_categories": [row.to_dict() for row in self.top_income_categories],
            "top_accounts_movement": [row.to_dict() for row in self.top_accounts_movement],
            "insights": self.insights,
        }


@dataclass(frozen=True)
class WeeklyReport:
    user_id: str
    week_start: str
    week_end: str
    timezone: str
    summary: WeeklySummary
    daily_overview: list[DailyPoint]
    expense_categories: list[CategoryPoint]
    advice: str

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "week": {
                "start_date": self.week_start,
                "end_date": self.week_end,
                "timezone": self.timezone,
            },
            "summary": self.summary.to_dict(),
            "daily_overview": [row.to_dict() for row in self.daily_overview],
            "expense_categories": [row.to_dict() for row in self.expense_categories],
            "daily_advice": self.advice,
        }
