from __future__ import annotations

import json
from datetime import date
from statistics import fmean

from src.domain.analytics_entities import FinanceForecastReport
from src.domain.ports.finance_advice_provider import FinanceAdviceProvider
from src.infrastructure.ai.gemini_text_generator import GeminiTextGenerator


class GeminiFinanceAdviceProvider(FinanceAdviceProvider):
    def __init__(
        self,
        *,
        api_key: str | None,
        models: list[str],
        max_output_tokens: int,
    ) -> None:
        self._generator = GeminiTextGenerator(
            api_key=api_key,
            models=models,
            default_max_output_tokens=max_output_tokens,
            timeout_seconds=22,
        )

    def build_finance_advice(self, report: FinanceForecastReport) -> tuple[str, str | None]:
        if not self._generator.enabled:
            return self._fallback_advice(report), None

        try:
            prompt = self._build_prompt(report)
            advice, model = self._generator.generate(
                prompt=prompt,
                temperature=0.35,
                max_output_tokens=220,
            )
            if not advice:
                return self._fallback_advice(report), None
            return advice, model
        except Exception:
            return self._fallback_advice(report), None

    def _build_prompt(self, report: FinanceForecastReport) -> str:
        vector = self._vectorize_context(report)
        vector_json = json.dumps(vector, ensure_ascii=False, separators=(",", ":"))
        mode_goal = self._mode_goal_text(report.analysis_mode)

        return (
            "Eres asesor financiero de Fintu. "
            "Con base en este contexto vectorizado, responde en espanol con consejo claro, accionable y profesional. "
            "Maximo 140 palabras. "
            "Formato obligatorio en 3 lineas numeradas: "
            "1) En que categoria gasto mas y cuanto represento. "
            "2) Que categorias deberia reducir primero (maximo 3). "
            "3) Plan concreto con una accion para hoy y una accion para la semana. "
            "No inventes datos ni uses relleno. "
            f"Objetivo del modo: {mode_goal}. "
            f"contexto_vectorizado={vector_json}"
        )

    @staticmethod
    def _vectorize_context(report: FinanceForecastReport) -> dict:
        kpis = report.kpis

        weekday_stats: dict[str, dict[str, float]] = {}
        grouped: dict[str, list[float]] = {}
        weekdays = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]

        for row in report.daily_history:
            try:
                weekday_idx = date.fromisoformat(row.date).weekday()
                weekday = weekdays[weekday_idx]
            except Exception:
                weekday = row.date
            grouped.setdefault(weekday, []).append(row.expense)

        for weekday, expenses in grouped.items():
            weekday_stats[weekday] = {
                "avg_expense": round(fmean(expenses), 2),
                "max_expense": round(max(expenses), 2),
            }

        forecast_net_series = [round(item.projected_net, 2) for item in report.forecast[:14]]

        top_categories = [
            {
                "name": item.category_name,
                "amount": round(item.amount, 2),
                "tx": item.transactions_count,
            }
            for item in report.top_expense_categories[:5]
        ]

        top_account_types = [
            {
                "type": item.account_type,
                "balance": round(item.current_balance, 2),
                "net": round(item.net, 2),
            }
            for item in report.account_type_breakdown[:4]
        ]

        top_transaction_types = [
            {
                "code": item.transaction_type_code,
                "income": round(item.income, 2),
                "expense": round(item.expense, 2),
                "tx": item.transactions_count,
            }
            for item in report.transaction_type_breakdown[:5]
        ]

        focus = report.spending_focus

        return {
            "analysis_mode": report.analysis_mode,
            "period": {
                "start": report.history_start,
                "end": report.history_end,
                "timezone": report.timezone,
            },
            "kpis": {
                "history_income": kpis.history_income,
                "history_expense": kpis.history_expense,
                "history_net": kpis.history_net,
                "avg_daily_income": kpis.avg_daily_income,
                "avg_daily_expense": kpis.avg_daily_expense,
                "avg_daily_net": kpis.avg_daily_net,
                "savings_rate_pct": kpis.savings_rate_pct,
                "expense_income_ratio": kpis.expense_income_ratio,
                "expense_volatility": kpis.expense_volatility,
                "projected_net": kpis.projected_net,
                "projected_end_balance": kpis.projected_end_balance,
            },
            "model_quality": {
                "confidence": report.model.confidence_score,
                "income_r2": report.model.income_r2,
                "expense_r2": report.model.expense_r2,
                "tx_r2": report.model.transactions_r2,
            },
            "alerts": [
                {
                    "level": alert.level,
                    "code": alert.code,
                }
                for alert in report.alerts
            ],
            "weekday_expense_pattern": weekday_stats,
            "forecast_net_series": forecast_net_series,
            "top_categories": top_categories,
            "top_account_types": top_account_types,
            "top_transaction_types": top_transaction_types,
            "spending_focus": {
                "period_label": focus.period_label,
                "top_category_name": focus.top_category_name,
                "top_category_amount": focus.top_category_amount,
                "top_category_share_pct": focus.top_category_share_pct,
                "categories_to_reduce": focus.categories_to_reduce,
            },
        }

    @staticmethod
    def _fallback_advice(report: FinanceForecastReport) -> str:
        top_name = report.spending_focus.top_category_name
        top_amount = report.spending_focus.top_category_amount
        top_share = report.spending_focus.top_category_share_pct
        categories_to_reduce = report.spending_focus.categories_to_reduce

        focus_label = f"en {top_name} (${top_amount:,.2f})" if top_name else "sin categoria dominante"
        if top_share is not None:
            focus_label += f", equivalente al {top_share:.2f}% del gasto"

        reduce_text = ", ".join(categories_to_reduce) if categories_to_reduce else "gastos variables no esenciales"

        ratio = report.kpis.expense_income_ratio
        projected = report.kpis.projected_net

        if ratio is not None and ratio > 1:
            return (
                f"1) Gastaste mas {focus_label}. "
                f"2) Categorias a reducir primero: {reduce_text}. "
                "3) Hoy congela compras no esenciales; esta semana aplica un recorte minimo del 10% en esas categorias."
            )

        if projected < 0:
            return (
                f"1) Gastaste mas {focus_label}. "
                f"2) Categorias a reducir primero: {reduce_text}. "
                "3) Hoy recorta un gasto variable y prioriza pagos fijos; en la semana controla tope diario para evitar flujo negativo."
            )

        return (
            f"1) Tu mayor gasto fue {focus_label}. "
            f"2) Mantener control en categorias: {reduce_text}. "
            "3) Hoy registra cada gasto en el momento; esta semana conserva una transferencia automatica a ahorro."
        )

    @staticmethod
    def _mode_goal_text(mode: str) -> str:
        if mode == "daily":
            return "Analiza exclusivamente el dia inmediatamente anterior"
        if mode == "weekly":
            return "Analiza la semana completa de los ultimos 7 dias cerrados"
        return "Analiza la ventana personalizada solicitada"
