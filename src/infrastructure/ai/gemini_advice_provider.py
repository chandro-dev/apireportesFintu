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

        top_category = (
            report.expense_categories[0].category_name
            if report.expense_categories
            else "No dominant category"
        )

        return (
            "Actua como asesor financiero personal de Fintu. "
            "Entrega un consejo diario accionable, claro y breve (maximo 60 palabras) en espanol. "
            "No uses listas ni saludos largos. "
            f"Resumen semanal: ingresos={report.summary.income}, gastos={report.summary.expense}, neto={report.summary.net}. "
            f"Categoria de gasto principal: {top_category}. "
            f"{latest_text}"
        )

    @staticmethod
    def _fallback_advice(report: WeeklyReport) -> str:
        if report.summary.net < 0:
            return (
                "Hoy enfocate en reducir un gasto variable pequeno y evita compras no planificadas; "
                "tu semana va en negativo y ese ajuste diario ayuda a recuperar control."
            )
        return (
            "Hoy manten el ritmo: registra cada gasto en el momento y separa una parte de tu ingreso "
            "como ahorro automatico para consolidar una semana positiva."
        )
