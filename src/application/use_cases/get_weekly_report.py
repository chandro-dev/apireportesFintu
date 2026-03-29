from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from src.core.settings import Settings
from src.domain.ports.advice_provider import AdviceProvider
from src.domain.ports.report_repository import ReportRepository
from src.domain.report_entities import DailyPoint, WeeklyReport, WeeklySummary


class GetWeeklyReportUseCase:
    def __init__(
        self,
        *,
        settings: Settings,
        repository: ReportRepository,
        advice_provider: AdviceProvider,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._advice_provider = advice_provider

    def execute(
        self,
        *,
        user_id: str,
        week_start_str: str | None,
        timezone_name: str | None,
    ) -> WeeklyReport:
        tz_name = timezone_name or self._settings.default_timezone
        week_start_date, week_end_date, week_start_dt, week_end_exclusive_dt = self._build_week_window(
            week_start_str=week_start_str,
            timezone_name=tz_name,
        )

        raw_daily = self._repository.fetch_daily_overview(
            user_id=user_id,
            week_start=week_start_dt,
            week_end_exclusive=week_end_exclusive_dt,
            timezone_name=tz_name,
        )
        full_daily = self._fill_week_days(
            start_date=week_start_date,
            end_date=week_end_date,
            raw_daily=raw_daily,
        )

        expense_categories = self._repository.fetch_expense_categories(
            user_id=user_id,
            week_start=week_start_dt,
            week_end_exclusive=week_end_exclusive_dt,
        )

        summary = WeeklySummary(
            income=round(sum(p.income for p in full_daily), 2),
            expense=round(sum(p.expense for p in full_daily), 2),
            net=round(sum(p.net for p in full_daily), 2),
            transactions_count=sum(p.transactions_count for p in full_daily),
        )

        report = WeeklyReport(
            user_id=user_id,
            week_start=week_start_date.isoformat(),
            week_end=week_end_date.isoformat(),
            timezone=tz_name,
            summary=summary,
            daily_overview=full_daily,
            expense_categories=expense_categories,
            advice="",
        )

        advice = self._advice_provider.build_daily_advice(report)

        return WeeklyReport(
            user_id=report.user_id,
            week_start=report.week_start,
            week_end=report.week_end,
            timezone=report.timezone,
            summary=report.summary,
            daily_overview=report.daily_overview,
            expense_categories=report.expense_categories,
            advice=advice,
        )

    @staticmethod
    def _build_week_window(
        *,
        week_start_str: str | None,
        timezone_name: str,
    ) -> tuple[date, date, datetime, datetime]:
        try:
            tz = ZoneInfo(timezone_name)
        except Exception as exc:
            raise ValueError(f"Timezone invalida: {timezone_name}") from exc

        if week_start_str:
            try:
                start_date = date.fromisoformat(week_start_str)
            except ValueError as exc:
                raise ValueError("week_start debe tener formato YYYY-MM-DD") from exc
        else:
            today = datetime.now(tz=tz).date()
            start_date = today - timedelta(days=today.weekday())

        end_date = start_date + timedelta(days=6)
        start_dt = datetime.combine(start_date, time.min, tzinfo=tz)
        end_exclusive = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=tz)

        return start_date, end_date, start_dt, end_exclusive

    @staticmethod
    def _fill_week_days(
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
