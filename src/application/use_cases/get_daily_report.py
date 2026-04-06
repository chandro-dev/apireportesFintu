from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from src.core.settings import Settings
from src.domain.ports.report_repository import ReportRepository
from src.domain.report_entities import (
    DailyComparison,
    DailyReport,
    DailySummary,
)


class GetDailyReportUseCase:
    def __init__(self, *, settings: Settings, repository: ReportRepository) -> None:
        self._settings = settings
        self._repository = repository

    def execute(
        self,
        *,
        user_id: str,
        report_day_str: str | None,
        timezone_name: str | None,
    ) -> DailyReport:
        tz_name = timezone_name or self._settings.default_timezone
        tz = self._parse_timezone(tz_name)
        now_local = datetime.now(tz=tz)

        report_day = self._resolve_report_day(report_day_str=report_day_str, tz=tz)
        start_dt = datetime.combine(report_day, time.min, tzinfo=tz)
        end_exclusive_dt = datetime.combine(report_day + timedelta(days=1), time.min, tzinfo=tz)

        summary = self._fetch_day_summary(
            user_id=user_id,
            day=report_day,
            start_inclusive=start_dt,
            end_exclusive=end_exclusive_dt,
            timezone_name=tz_name,
        )

        previous_day = report_day - timedelta(days=1)
        prev_start_dt = datetime.combine(previous_day, time.min, tzinfo=tz)
        prev_end_exclusive_dt = datetime.combine(report_day, time.min, tzinfo=tz)
        previous_summary = self._fetch_day_summary(
            user_id=user_id,
            day=previous_day,
            start_inclusive=prev_start_dt,
            end_exclusive=prev_end_exclusive_dt,
            timezone_name=tz_name,
        )

        comparison = DailyComparison(
            previous_day=previous_day.isoformat(),
            income_delta=round(summary.income - previous_summary.income, 2),
            expense_delta=round(summary.expense - previous_summary.expense, 2),
            net_delta=round(summary.net - previous_summary.net, 2),
        )

        top_expense_categories = self._repository.fetch_category_breakdown(
            user_id=user_id,
            start_inclusive=start_dt,
            end_exclusive=end_exclusive_dt,
            flow="EXPENSE",
            limit=6,
        )
        top_income_categories = self._repository.fetch_category_breakdown(
            user_id=user_id,
            start_inclusive=start_dt,
            end_exclusive=end_exclusive_dt,
            flow="INCOME",
            limit=6,
        )
        top_accounts_movement = self._repository.fetch_account_movement(
            user_id=user_id,
            start_inclusive=start_dt,
            end_exclusive=end_exclusive_dt,
            limit=5,
        )
        normal_accounts = self._repository.fetch_normal_accounts_balances(user_id=user_id)
        normal_accounts_total_balance = round(
            sum(account.current_amount for account in normal_accounts), 2
        )
        credit_cards_total_debt = self._repository.fetch_credit_cards_total_debt(user_id=user_id)
        recent_outgoing_normal_transactions = self._repository.fetch_recent_outgoing_normal_transactions(
            user_id=user_id,
            end_exclusive=now_local,
            timezone_name=tz_name,
            limit=10,
        )

        weekly_start_date = now_local.date() - timedelta(days=6)
        weekly_start_dt = datetime.combine(weekly_start_date, time.min, tzinfo=tz)
        weekly_end_exclusive_dt = datetime.combine(now_local.date() + timedelta(days=1), time.min, tzinfo=tz)
        weekly_expense_categories = self._repository.fetch_category_breakdown(
            user_id=user_id,
            start_inclusive=weekly_start_dt,
            end_exclusive=weekly_end_exclusive_dt,
            flow="EXPENSE",
            limit=7,
        )

        insights = self._build_insights(
            summary=summary,
            comparison=comparison,
            top_expense_categories=top_expense_categories,
            top_accounts_movement=top_accounts_movement,
            credit_cards_total_debt=credit_cards_total_debt,
            weekly_expense_categories=weekly_expense_categories,
        )

        return DailyReport(
            user_id=user_id,
            timezone=tz_name,
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            summary=summary,
            comparison=comparison,
            normal_accounts_total_balance=normal_accounts_total_balance,
            normal_accounts=normal_accounts,
            credit_cards_total_debt=credit_cards_total_debt,
            recent_outgoing_normal_transactions=recent_outgoing_normal_transactions,
            weekly_expense_window_start=weekly_start_date.isoformat(),
            weekly_expense_window_end=now_local.date().isoformat(),
            weekly_expense_categories=weekly_expense_categories,
            top_expense_categories=top_expense_categories,
            top_income_categories=top_income_categories,
            top_accounts_movement=top_accounts_movement,
            insights=insights,
        )

    @staticmethod
    def _parse_timezone(timezone_name: str) -> ZoneInfo:
        try:
            return ZoneInfo(timezone_name)
        except Exception as exc:
            raise ValueError(f"Timezone invalida: {timezone_name}") from exc

    @staticmethod
    def _resolve_report_day(*, report_day_str: str | None, tz: ZoneInfo) -> date:
        if report_day_str:
            try:
                return date.fromisoformat(report_day_str)
            except ValueError as exc:
                raise ValueError("report_day debe tener formato YYYY-MM-DD") from exc

        today = datetime.now(tz=tz).date()
        return today - timedelta(days=1)

    def _fetch_day_summary(
        self,
        *,
        user_id: str,
        day: date,
        start_inclusive: datetime,
        end_exclusive: datetime,
        timezone_name: str,
    ) -> DailySummary:
        daily_rows = self._repository.fetch_daily_overview(
            user_id=user_id,
            week_start=start_inclusive,
            week_end_exclusive=end_exclusive,
            timezone_name=timezone_name,
        )

        if daily_rows:
            row = daily_rows[0]
            return DailySummary(
                day=day.isoformat(),
                income=row.income,
                expense=row.expense,
                net=row.net,
                transactions_count=row.transactions_count,
            )

        return DailySummary(
            day=day.isoformat(),
            income=0.0,
            expense=0.0,
            net=0.0,
            transactions_count=0,
        )

    @staticmethod
    def _build_insights(
        *,
        summary: DailySummary,
        comparison: DailyComparison,
        top_expense_categories,
        top_accounts_movement,
        credit_cards_total_debt: float,
        weekly_expense_categories,
    ) -> list[str]:
        insights: list[str] = []

        if summary.net < 0:
            insights.append(
                "El dia cerro en negativo. Prioriza reducir gasto variable en las siguientes 24 horas."
            )
        else:
            insights.append(
                "El dia cerro en positivo o neutro. Mantener disciplina de registro mejora tu control semanal."
            )

        if top_expense_categories and summary.expense > 0:
            top = top_expense_categories[0]
            share = round((top.amount / summary.expense) * 100, 2)
            insights.append(
                f"La categoria con mayor gasto fue '{top.category_name}' con ${top.amount:,.2f} ({share}% del gasto diario)."
            )

        if top_accounts_movement:
            account = top_accounts_movement[0]
            insights.append(
                f"La cuenta con mas movimiento fue '{account.account_name}' (${account.total_movement:,.2f}, {account.transactions_count} tx)."
            )

        if weekly_expense_categories:
            weekly_top = weekly_expense_categories[0]
            insights.append(
                f"En la ultima semana la categoria de mayor gasto fue '{weekly_top.category_name}' (${weekly_top.amount:,.2f})."
            )

        if credit_cards_total_debt > 0:
            insights.append(
                f"Tu deuda total estimada en tarjetas es ${credit_cards_total_debt:,.2f}. Prioriza pagos de alto interes."
            )

        if comparison.expense_delta > 0:
            insights.append(
                f"El gasto subio ${comparison.expense_delta:,.2f} vs {comparison.previous_day}. Revisa el origen de ese aumento."
            )
        elif comparison.expense_delta < 0:
            insights.append(
                f"El gasto bajo ${abs(comparison.expense_delta):,.2f} vs {comparison.previous_day}. Buen ajuste diario."
            )

        return insights[:6]
