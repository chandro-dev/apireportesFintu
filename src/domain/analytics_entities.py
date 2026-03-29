from __future__ import annotations

from dataclasses import dataclass

from src.domain.report_entities import CategoryPoint, DailyPoint


@dataclass(frozen=True)
class AccountTypeMetric:
    account_type: str
    active_accounts: int
    current_balance: float
    income: float
    expense: float
    net: float
    transactions_count: int

    def to_dict(self) -> dict:
        return {
            "account_type": self.account_type,
            "active_accounts": self.active_accounts,
            "current_balance": self.current_balance,
            "income": self.income,
            "expense": self.expense,
            "net": self.net,
            "transactions_count": self.transactions_count,
        }


@dataclass(frozen=True)
class TransactionTypeMetric:
    transaction_type_code: str
    transaction_type_name: str
    income: float
    expense: float
    net: float
    transactions_count: int

    def to_dict(self) -> dict:
        return {
            "transaction_type_code": self.transaction_type_code,
            "transaction_type_name": self.transaction_type_name,
            "income": self.income,
            "expense": self.expense,
            "net": self.net,
            "transactions_count": self.transactions_count,
        }


@dataclass(frozen=True)
class ForecastDailyPoint:
    date: str
    projected_income: float
    projected_expense: float
    projected_net: float
    projected_transactions_count: int
    projected_balance: float | None

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "projected_income": self.projected_income,
            "projected_expense": self.projected_expense,
            "projected_net": self.projected_net,
            "projected_transactions_count": self.projected_transactions_count,
            "projected_balance": self.projected_balance,
        }


@dataclass(frozen=True)
class ForecastModelDiagnostics:
    model_name: str
    history_days: int
    forecast_days: int
    income_r2: float
    expense_r2: float
    transactions_r2: float
    confidence_score: float

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "history_days": self.history_days,
            "forecast_days": self.forecast_days,
            "income_r2": self.income_r2,
            "expense_r2": self.expense_r2,
            "transactions_r2": self.transactions_r2,
            "confidence_score": self.confidence_score,
        }


@dataclass(frozen=True)
class FinanceKpis:
    history_income: float
    history_expense: float
    history_net: float
    avg_daily_income: float
    avg_daily_expense: float
    avg_daily_net: float
    savings_rate_pct: float | None
    expense_income_ratio: float | None
    expense_volatility: float
    projected_income: float
    projected_expense: float
    projected_net: float
    projected_end_balance: float | None

    def to_dict(self) -> dict:
        return {
            "history_income": self.history_income,
            "history_expense": self.history_expense,
            "history_net": self.history_net,
            "avg_daily_income": self.avg_daily_income,
            "avg_daily_expense": self.avg_daily_expense,
            "avg_daily_net": self.avg_daily_net,
            "savings_rate_pct": self.savings_rate_pct,
            "expense_income_ratio": self.expense_income_ratio,
            "expense_volatility": self.expense_volatility,
            "projected_income": self.projected_income,
            "projected_expense": self.projected_expense,
            "projected_net": self.projected_net,
            "projected_end_balance": self.projected_end_balance,
        }


@dataclass(frozen=True)
class FinanceAlert:
    level: str
    code: str
    message: str

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "code": self.code,
            "message": self.message,
        }


@dataclass(frozen=True)
class SpendingFocus:
    period_label: str
    top_category_name: str | None
    top_category_amount: float
    top_category_share_pct: float | None
    categories_to_reduce: list[str]

    def to_dict(self) -> dict:
        return {
            "period_label": self.period_label,
            "top_category_name": self.top_category_name,
            "top_category_amount": self.top_category_amount,
            "top_category_share_pct": self.top_category_share_pct,
            "categories_to_reduce": self.categories_to_reduce,
        }


@dataclass(frozen=True)
class FinanceForecastReport:
    user_id: str
    analysis_mode: str
    timezone: str
    history_start: str
    history_end: str
    generated_at_utc: str
    model: ForecastModelDiagnostics
    kpis: FinanceKpis
    daily_history: list[DailyPoint]
    forecast: list[ForecastDailyPoint]
    account_type_breakdown: list[AccountTypeMetric]
    transaction_type_breakdown: list[TransactionTypeMetric]
    top_expense_categories: list[CategoryPoint]
    alerts: list[FinanceAlert]
    spending_focus: SpendingFocus
    ai_advice: str
    ai_model: str | None

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "analysis_mode": self.analysis_mode,
            "timezone": self.timezone,
            "history_window": {
                "start_date": self.history_start,
                "end_date": self.history_end,
                "generated_at_utc": self.generated_at_utc,
            },
            "model": self.model.to_dict(),
            "kpis": self.kpis.to_dict(),
            "daily_history": [row.to_dict() for row in self.daily_history],
            "forecast": [row.to_dict() for row in self.forecast],
            "breakdown": {
                "by_account_type": [row.to_dict() for row in self.account_type_breakdown],
                "by_transaction_type": [row.to_dict() for row in self.transaction_type_breakdown],
                "top_expense_categories": [row.to_dict() for row in self.top_expense_categories],
            },
            "alerts": [alert.to_dict() for alert in self.alerts],
            "spending_focus": self.spending_focus.to_dict(),
            "ai_advice": {
                "text": self.ai_advice,
                "model": self.ai_model,
            },
        }
