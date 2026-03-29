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

