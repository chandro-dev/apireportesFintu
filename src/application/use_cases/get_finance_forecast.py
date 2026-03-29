from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from statistics import pstdev
from zoneinfo import ZoneInfo

from src.application.services.financial_forecast_model import FinancialForecastModel
from src.core.settings import Settings
from src.domain.analytics_entities import (
    FinanceAlert,
    FinanceForecastReport,
    FinanceKpis,
    ForecastModelDiagnostics,
    SpendingFocus,
)
from src.domain.ports.finance_advice_provider import FinanceAdviceProvider
from src.domain.ports.finance_analytics_repository import FinanceAnalyticsRepository
from src.domain.report_entities import CategoryPoint, DailyPoint


class GetFinanceForecastUseCase:
    _ANALYSIS_MODES = {"custom", "daily", "weekly"}

    def __init__(
        self,
        *,
        settings: Settings,
        repository: FinanceAnalyticsRepository,
        forecast_model: FinancialForecastModel,
        advice_provider: FinanceAdviceProvider,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._forecast_model = forecast_model
        self._advice_provider = advice_provider

    def execute(
        self,
        *,
        user_id: str,
        history_days: int | None,
        forecast_days: int | None,
        timezone_name: str | None,
        analysis_mode: str | None,
    ) -> FinanceForecastReport:
        tz_name = timezone_name or self._settings.default_timezone
        tz = self._parse_timezone(tz_name)
        mode = self._normalize_analysis_mode(analysis_mode)
        safe_history_days, safe_forecast_days, history_end_date, period_label = (
            self._resolve_analysis_window(
                mode=mode,
                history_days=history_days,
                forecast_days=forecast_days,
                tz=tz,
            )
        )
        history_start_date = history_end_date - timedelta(days=safe_history_days - 1)

        history_start_dt = datetime.combine(history_start_date, time.min, tzinfo=tz)
        history_end_exclusive_dt = datetime.combine(
            history_end_date + timedelta(days=1),
            time.min,
            tzinfo=tz,
        )

        raw_daily = self._repository.fetch_daily_history(
            user_id=user_id,
            start_inclusive=history_start_dt,
            end_exclusive=history_end_exclusive_dt,
            timezone_name=tz_name,
        )
        daily_history = self._fill_missing_days(
            start_date=history_start_date,
            end_date=history_end_date,
            raw_daily=raw_daily,
        )

        account_type_breakdown = self._repository.fetch_account_type_breakdown(
            user_id=user_id,
            start_inclusive=history_start_dt,
            end_exclusive=history_end_exclusive_dt,
        )
        transaction_type_breakdown = self._repository.fetch_transaction_type_breakdown(
            user_id=user_id,
            start_inclusive=history_start_dt,
            end_exclusive=history_end_exclusive_dt,
        )
        top_expense_categories = self._repository.fetch_expense_category_breakdown(
            user_id=user_id,
            start_inclusive=history_start_dt,
            end_exclusive=history_end_exclusive_dt,
            limit=8,
        )
        current_total_balance = self._repository.fetch_total_current_balance(user_id=user_id)

        forecast_computation = self._forecast_model.predict(
            history=daily_history,
            forecast_days=safe_forecast_days,
            current_total_balance=current_total_balance,
        )

        kpis = self._build_kpis(
            daily_history=daily_history,
            forecast=forecast_computation.forecast,
            current_total_balance=current_total_balance,
        )
        alerts = self._build_alerts(
            kpis=kpis,
            top_expense_categories=top_expense_categories,
            model_confidence=forecast_computation.confidence_score,
        )
        spending_focus = self._build_spending_focus(
            top_expense_categories=top_expense_categories,
            history_expense=kpis.history_expense,
            period_label=period_label,
        )

        model = ForecastModelDiagnostics(
            model_name="linear-trend + weekly-seasonality + moving-average",
            history_days=safe_history_days,
            forecast_days=safe_forecast_days,
            income_r2=forecast_computation.income_r2,
            expense_r2=forecast_computation.expense_r2,
            transactions_r2=forecast_computation.transactions_r2,
            confidence_score=forecast_computation.confidence_score,
        )

        draft_report = FinanceForecastReport(
            user_id=user_id,
            analysis_mode=mode,
            timezone=tz_name,
            history_start=history_start_date.isoformat(),
            history_end=history_end_date.isoformat(),
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            model=model,
            kpis=kpis,
            daily_history=daily_history,
            forecast=forecast_computation.forecast,
            account_type_breakdown=account_type_breakdown,
            transaction_type_breakdown=transaction_type_breakdown,
            top_expense_categories=top_expense_categories,
            alerts=alerts,
            spending_focus=spending_focus,
            ai_advice="",
            ai_model=None,
        )

        advice_text, advice_model = self._advice_provider.build_finance_advice(draft_report)

        return FinanceForecastReport(
            user_id=draft_report.user_id,
            analysis_mode=draft_report.analysis_mode,
            timezone=draft_report.timezone,
            history_start=draft_report.history_start,
            history_end=draft_report.history_end,
            generated_at_utc=draft_report.generated_at_utc,
            model=draft_report.model,
            kpis=draft_report.kpis,
            daily_history=draft_report.daily_history,
            forecast=draft_report.forecast,
            account_type_breakdown=draft_report.account_type_breakdown,
            transaction_type_breakdown=draft_report.transaction_type_breakdown,
            top_expense_categories=draft_report.top_expense_categories,
            alerts=draft_report.alerts,
            spending_focus=draft_report.spending_focus,
            ai_advice=advice_text,
            ai_model=advice_model,
        )

    @staticmethod
    def _parse_timezone(timezone_name: str) -> ZoneInfo:
        try:
            return ZoneInfo(timezone_name)
        except Exception as exc:
            raise ValueError(f"Timezone invalida: {timezone_name}") from exc

    @staticmethod
    def _normalize_history_days(value: int | None) -> int:
        if value is None:
            return 90
        if value < 14 or value > 365:
            raise ValueError("history_days debe estar entre 14 y 365")
        return value

    @staticmethod
    def _normalize_forecast_days(value: int | None) -> int:
        if value is None:
            return 7
        if value < 1 or value > 30:
            raise ValueError("forecast_days debe estar entre 1 y 30")
        return value

    @classmethod
    def _normalize_analysis_mode(cls, value: str | None) -> str:
        if value is None or value.strip() == "":
            return "custom"

        mode = value.strip().lower()
        if mode not in cls._ANALYSIS_MODES:
            raise ValueError("analysis_mode debe ser 'daily', 'weekly' o 'custom'")
        return mode

    def _resolve_analysis_window(
        self,
        *,
        mode: str,
        history_days: int | None,
        forecast_days: int | None,
        tz: ZoneInfo,
    ) -> tuple[int, int, date, str]:
        today = datetime.now(tz=tz).date()

        if mode == "daily":
            end_date = today - timedelta(days=1)
            resolved_forecast_days = 1 if forecast_days is None else self._normalize_forecast_days(
                forecast_days
            )
            return 1, resolved_forecast_days, end_date, "dia_anterior"

        if mode == "weekly":
            end_date = today - timedelta(days=1)
            resolved_forecast_days = 7 if forecast_days is None else self._normalize_forecast_days(
                forecast_days
            )
            return 7, resolved_forecast_days, end_date, "ultima_semana_completa"

        resolved_history_days = self._normalize_history_days(history_days)
        resolved_forecast_days = self._normalize_forecast_days(forecast_days)
        return resolved_history_days, resolved_forecast_days, today, "ventana_personalizada"

    @staticmethod
    def _fill_missing_days(
        *,
        start_date: date,
        end_date: date,
        raw_daily: list[DailyPoint],
    ) -> list[DailyPoint]:
        by_date = {row.date: row for row in raw_daily}

        result: list[DailyPoint] = []
        current = start_date
        while current <= end_date:
            key = current.isoformat()
            row = by_date.get(key)
            if row is None:
                result.append(
                    DailyPoint(
                        date=key,
                        income=0.0,
                        expense=0.0,
                        net=0.0,
                        transactions_count=0,
                    )
                )
            else:
                result.append(row)
            current += timedelta(days=1)

        return result

    @staticmethod
    def _build_kpis(
        *,
        daily_history: list[DailyPoint],
        forecast,
        current_total_balance: float | None,
    ) -> FinanceKpis:
        periods = max(1, len(daily_history))

        history_income = round(sum(day.income for day in daily_history), 2)
        history_expense = round(sum(day.expense for day in daily_history), 2)
        history_net = round(sum(day.net for day in daily_history), 2)

        avg_daily_income = round(history_income / periods, 2)
        avg_daily_expense = round(history_expense / periods, 2)
        avg_daily_net = round(history_net / periods, 2)

        savings_rate_pct = None
        expense_income_ratio = None
        if history_income > 0:
            savings_rate_pct = round((history_net / history_income) * 100, 2)
            expense_income_ratio = round(history_expense / history_income, 4)

        expenses = [day.expense for day in daily_history]
        expense_volatility = round(pstdev(expenses), 2) if len(expenses) > 1 else 0.0

        projected_income = round(sum(day.projected_income for day in forecast), 2)
        projected_expense = round(sum(day.projected_expense for day in forecast), 2)
        projected_net = round(sum(day.projected_net for day in forecast), 2)

        if forecast:
            projected_end_balance = forecast[-1].projected_balance
        else:
            projected_end_balance = current_total_balance

        return FinanceKpis(
            history_income=history_income,
            history_expense=history_expense,
            history_net=history_net,
            avg_daily_income=avg_daily_income,
            avg_daily_expense=avg_daily_expense,
            avg_daily_net=avg_daily_net,
            savings_rate_pct=savings_rate_pct,
            expense_income_ratio=expense_income_ratio,
            expense_volatility=expense_volatility,
            projected_income=projected_income,
            projected_expense=projected_expense,
            projected_net=projected_net,
            projected_end_balance=projected_end_balance,
        )

    @staticmethod
    def _build_alerts(
        *,
        kpis: FinanceKpis,
        top_expense_categories: list[CategoryPoint],
        model_confidence: float,
    ) -> list[FinanceAlert]:
        alerts: list[FinanceAlert] = []

        if model_confidence < 0.35:
            alerts.append(
                FinanceAlert(
                    level="warning",
                    code="model_low_confidence",
                    message="La calidad del ajuste historico es baja; considera ampliar history_days.",
                )
            )

        if kpis.expense_income_ratio is not None and kpis.expense_income_ratio > 1:
            alerts.append(
                FinanceAlert(
                    level="critical",
                    code="overspending",
                    message="Tus gastos historicos superan tus ingresos en la ventana analizada.",
                )
            )
        elif kpis.expense_income_ratio is not None and kpis.expense_income_ratio > 0.85:
            alerts.append(
                FinanceAlert(
                    level="warning",
                    code="high_expense_ratio",
                    message="Tu ratio gasto/ingreso es alto (>0.85).",
                )
            )

        if kpis.projected_net < 0:
            alerts.append(
                FinanceAlert(
                    level="warning",
                    code="negative_projection",
                    message="La proyeccion del horizonte seleccionado indica flujo neto negativo.",
                )
            )

        if kpis.projected_end_balance is not None and kpis.projected_end_balance < 0:
            alerts.append(
                FinanceAlert(
                    level="critical",
                    code="negative_balance_projection",
                    message="El saldo proyectado cae por debajo de cero si se mantiene la tendencia.",
                )
            )

        if top_expense_categories and kpis.history_expense > 0:
            top = top_expense_categories[0]
            dominance = (top.amount / kpis.history_expense) * 100
            if dominance >= 40:
                alerts.append(
                    FinanceAlert(
                        level="info",
                        code="expense_concentration",
                        message=(
                            f"La categoria '{top.category_name}' concentra {round(dominance, 2)}% "
                            "del gasto historico."
                        ),
                    )
                )

        return alerts

    @staticmethod
    def _build_spending_focus(
        *,
        top_expense_categories: list[CategoryPoint],
        history_expense: float,
        period_label: str,
    ) -> SpendingFocus:
        if not top_expense_categories or history_expense <= 0:
            return SpendingFocus(
                period_label=period_label,
                top_category_name=None,
                top_category_amount=0.0,
                top_category_share_pct=None,
                categories_to_reduce=[],
            )

        top = top_expense_categories[0]
        top_share = round((top.amount / history_expense) * 100, 2)
        categories_to_reduce = [
            item.category_name for item in top_expense_categories[:3] if item.amount > 0
        ]

        return SpendingFocus(
            period_label=period_label,
            top_category_name=top.category_name,
            top_category_amount=round(top.amount, 2),
            top_category_share_pct=top_share,
            categories_to_reduce=categories_to_reduce,
        )
