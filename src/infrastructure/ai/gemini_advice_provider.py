from __future__ import annotations

from src.domain.ports.advice_provider import AdviceProvider
from src.domain.report_entities import WeeklyReport
from src.infrastructure.ai.gemini_text_generator import GeminiTextGenerator


class GeminiAdviceProvider(AdviceProvider):
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
            timeout_seconds=20,
        )

    def build_daily_advice(self, report: WeeklyReport) -> str:
        if not self._generator.enabled:
            return self._fallback_advice(report)

        try:
            prompt = self._build_prompt(report)
            text, _model = self._generator.generate(
                prompt=prompt,
                temperature=0.45,
                max_output_tokens=180,
            )
            if not text:
                return self._fallback_advice(report)
            return text
        except Exception:
            return self._fallback_advice(report)

    def _build_prompt(self, report: WeeklyReport) -> str:
        latest_day = report.daily_overview[-1] if report.daily_overview else None
        latest_text = "No recent transactions in this week."
        if latest_day:
            latest_text = (
                f"Last day ({latest_day.date}): income={latest_day.income}, "
                f"expense={latest_day.expense}, net={latest_day.net}, tx={latest_day.transactions_count}."
            )

        top_category = report.expense_categories[0] if report.expense_categories else None
        top_category_text = (
            f"{top_category.category_name} por {top_category.amount}"
            if top_category
            else "No dominant category"
        )
        savings_rate = (
            round((report.summary.net / report.summary.income) * 100, 2)
            if report.summary.income > 0
            else None
        )
        expense_ratio = (
            round((report.summary.expense / report.summary.income) * 100, 2)
            if report.summary.income > 0
            else None
        )

        return (
            "Actua como asesor financiero personal de Fintu. "
            "Entrega un consejo semanal accionable, claro y breve (maximo 90 palabras) en espanol. "
            "Usa buenas practicas financieras: flujo de caja, tasa de ahorro, control de gasto variable, deuda cara y concentracion por categoria. "
            "Formato obligatorio en 3 frases: diagnostico, riesgo principal y accion concreta para los proximos 7 dias. "
            "No uses saludos, no inventes datos y no prometas rendimientos. "
            f"Resumen semanal: ingresos={report.summary.income}, gastos={report.summary.expense}, neto={report.summary.net}. "
            f"tasa_ahorro_pct={savings_rate}, ratio_gasto_ingreso_pct={expense_ratio}. "
            f"Categoria de gasto principal: {top_category_text}. "
            f"{latest_text}"
        )

    @staticmethod
    def _fallback_advice(report: WeeklyReport) -> str:
        if report.summary.net < 0:
            return (
                "La semana cerro con flujo negativo. El riesgo principal es financiar consumo con deuda o reducir liquidez; durante los proximos 7 dias fija un tope diario de gasto variable y recorta primero la categoria con mayor participacion."
            )
        return (
            "La semana mantiene flujo positivo. El riesgo principal es que el excedente se diluya en gasto discrecional; durante los proximos 7 dias separa el ahorro al inicio y controla la categoria de mayor gasto con un limite semanal."
        )
