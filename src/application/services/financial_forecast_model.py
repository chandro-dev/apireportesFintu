from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from statistics import fmean

from src.domain.analytics_entities import ForecastDailyPoint
from src.domain.report_entities import DailyPoint


@dataclass(frozen=True)
class _SeriesFit:
    slope: float
    intercept: float
    r2: float
    seasonality_by_weekday: dict[int, float]


@dataclass(frozen=True)
class ForecastComputation:
    forecast: list[ForecastDailyPoint]
    income_r2: float
    expense_r2: float
    transactions_r2: float
    confidence_score: float


class FinancialForecastModel:
    def predict(
        self,
        *,
        history: list[DailyPoint],
        forecast_days: int,
        current_total_balance: float | None,
    ) -> ForecastComputation:
        if not history or forecast_days <= 0:
            return ForecastComputation(
                forecast=[],
                income_r2=0.0,
                expense_r2=0.0,
                transactions_r2=0.0,
                confidence_score=0.0,
            )

        ordered_history = sorted(history, key=lambda row: row.date)
        history_dates = [date.fromisoformat(row.date) for row in ordered_history]

        income_values = [row.income for row in ordered_history]
        expense_values = [row.expense for row in ordered_history]
        tx_values = [float(row.transactions_count) for row in ordered_history]

        income_fit = self._fit_series(income_values, history_dates)
        expense_fit = self._fit_series(expense_values, history_dates)
        tx_fit = self._fit_series(tx_values, history_dates)

        last_date = history_dates[-1]
        balance = current_total_balance
        daily_forecast: list[ForecastDailyPoint] = []

        for step in range(1, forecast_days + 1):
            target_date = last_date + timedelta(days=step)
            idx = len(history_dates) + (step - 1)

            projected_income = self._predict_from_fit(
                fit=income_fit,
                x=idx,
                target_date=target_date,
                min_value=0.0,
            )
            projected_expense = self._predict_from_fit(
                fit=expense_fit,
                x=idx,
                target_date=target_date,
                min_value=0.0,
            )
            projected_net = round(projected_income - projected_expense, 2)

            projected_tx = self._predict_from_fit(
                fit=tx_fit,
                x=idx,
                target_date=target_date,
                min_value=0.0,
            )
            projected_tx_count = int(round(projected_tx))

            projected_balance: float | None
            if balance is None:
                projected_balance = None
            else:
                balance = round(balance + projected_net, 2)
                projected_balance = balance

            daily_forecast.append(
                ForecastDailyPoint(
                    date=target_date.isoformat(),
                    projected_income=round(projected_income, 2),
                    projected_expense=round(projected_expense, 2),
                    projected_net=projected_net,
                    projected_transactions_count=max(0, projected_tx_count),
                    projected_balance=projected_balance,
                )
            )

        confidence = self._confidence_score(
            history_size=len(ordered_history),
            income_r2=income_fit.r2,
            expense_r2=expense_fit.r2,
            tx_r2=tx_fit.r2,
        )

        return ForecastComputation(
            forecast=daily_forecast,
            income_r2=round(income_fit.r2, 4),
            expense_r2=round(expense_fit.r2, 4),
            transactions_r2=round(tx_fit.r2, 4),
            confidence_score=confidence,
        )

    @staticmethod
    def _fit_series(values: list[float], dates: list[date]) -> _SeriesFit:
        if not values:
            return _SeriesFit(slope=0.0, intercept=0.0, r2=0.0, seasonality_by_weekday={})

        smoothed = FinancialForecastModel._moving_average(values)
        slope, intercept, r2 = FinancialForecastModel._linear_regression(smoothed)

        seasonality: dict[int, list[float]] = {}
        for idx, value in enumerate(values):
            trend = intercept + slope * idx
            weekday = dates[idx].weekday()
            seasonality.setdefault(weekday, []).append(value - trend)

        avg_seasonality = {
            weekday: fmean(residuals) for weekday, residuals in seasonality.items() if residuals
        }

        return _SeriesFit(
            slope=slope,
            intercept=intercept,
            r2=max(0.0, min(1.0, r2)),
            seasonality_by_weekday=avg_seasonality,
        )

    @staticmethod
    def _moving_average(values: list[float], window: int = 7) -> list[float]:
        if not values:
            return []

        result: list[float] = []
        for idx in range(len(values)):
            start = max(0, idx - window + 1)
            sample = values[start : idx + 1]
            result.append(fmean(sample))
        return result

    @staticmethod
    def _linear_regression(values: list[float]) -> tuple[float, float, float]:
        n = len(values)
        if n <= 1:
            return 0.0, values[0] if values else 0.0, 0.0

        mean_x = (n - 1) / 2
        mean_y = fmean(values)

        num = 0.0
        den = 0.0
        for idx, value in enumerate(values):
            dx = idx - mean_x
            num += dx * (value - mean_y)
            den += dx * dx

        slope = (num / den) if den else 0.0
        intercept = mean_y - slope * mean_x

        predictions = [intercept + slope * idx for idx in range(n)]
        ss_res = sum((values[idx] - predictions[idx]) ** 2 for idx in range(n))
        ss_tot = sum((value - mean_y) ** 2 for value in values)

        if ss_tot == 0:
            r2 = 0.0
        else:
            r2 = 1 - (ss_res / ss_tot)

        return slope, intercept, r2

    @staticmethod
    def _predict_from_fit(*, fit: _SeriesFit, x: int, target_date: date, min_value: float) -> float:
        trend = fit.intercept + (fit.slope * x)
        seasonal_adjustment = fit.seasonality_by_weekday.get(target_date.weekday(), 0.0)
        value = trend + seasonal_adjustment
        return max(min_value, value)

    @staticmethod
    def _confidence_score(
        *,
        history_size: int,
        income_r2: float,
        expense_r2: float,
        tx_r2: float,
    ) -> float:
        data_factor = max(0.1, min(1.0, history_size / 90))
        fit_quality = max(0.0, min(1.0, (income_r2 + expense_r2 + tx_r2) / 3))
        confidence = (fit_quality * 0.75) + (data_factor * 0.25)
        return round(max(0.0, min(1.0, confidence)), 4)
