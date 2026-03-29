from __future__ import annotations

from html import escape

from src.domain.analytics_entities import FinanceForecastReport


class FinanceForecastEmailRenderer:
    def render(self, *, report: FinanceForecastReport) -> str:
        kpis = report.kpis
        model = report.model
        focus = report.spending_focus

        alerts_html = "".join(
            f"<li><strong>{escape(alert.level.upper())}</strong> - {escape(alert.message)}</li>"
            for alert in report.alerts
        )
        if not alerts_html:
            alerts_html = "<li>Sin alertas relevantes para el periodo analizado.</li>"

        forecast_rows = "".join(
            "".join(
                [
                    "<tr>",
                    f"<td>{escape(day.date)}</td>",
                    f"<td>{self._money(day.projected_income)}</td>",
                    f"<td>{self._money(day.projected_expense)}</td>",
                    f"<td>{self._money(day.projected_net)}</td>",
                    f"<td>{day.projected_transactions_count}</td>",
                    f"<td>{self._money(day.projected_balance) if day.projected_balance is not None else '-'}</td>",
                    "</tr>",
                ]
            )
            for day in report.forecast
        )

        account_rows = "".join(
            "".join(
                [
                    "<tr>",
                    f"<td>{escape(item.account_type)}</td>",
                    f"<td>{item.active_accounts}</td>",
                    f"<td>{self._money(item.current_balance)}</td>",
                    f"<td>{self._money(item.income)}</td>",
                    f"<td>{self._money(item.expense)}</td>",
                    f"<td>{self._money(item.net)}</td>",
                    f"<td>{item.transactions_count}</td>",
                    "</tr>",
                ]
            )
            for item in report.account_type_breakdown
        )

        tx_type_rows = "".join(
            "".join(
                [
                    "<tr>",
                    f"<td>{escape(item.transaction_type_code)}</td>",
                    f"<td>{escape(item.transaction_type_name)}</td>",
                    f"<td>{self._money(item.income)}</td>",
                    f"<td>{self._money(item.expense)}</td>",
                    f"<td>{self._money(item.net)}</td>",
                    f"<td>{item.transactions_count}</td>",
                    "</tr>",
                ]
            )
            for item in report.transaction_type_breakdown
        )

        categories_rows = "".join(
            "".join(
                [
                    "<tr>",
                    f"<td>{escape(item.category_name)}</td>",
                    f"<td>{self._money(item.amount)}</td>",
                    f"<td>{item.transactions_count}</td>",
                    "</tr>",
                ]
            )
            for item in report.top_expense_categories
        )

        categories_to_reduce_html = "".join(
            f"<li>{escape(category)}</li>" for category in focus.categories_to_reduce
        )
        if not categories_to_reduce_html:
            categories_to_reduce_html = "<li>Sin categorias relevantes para recorte en el periodo.</li>"

        ai_model_label = escape(report.ai_model) if report.ai_model else "fallback-local"
        mode_label = self._mode_label(report.analysis_mode)

        return f"""
<!DOCTYPE html>
<html lang=\"es\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Fintu - Analitica Predictiva</title>
  <style>
    body {{ font-family: Arial, Helvetica, sans-serif; color: #17212b; background: #f5f8fb; margin: 0; padding: 24px; }}
    .card {{ background: #ffffff; border-radius: 12px; padding: 20px; margin-bottom: 16px; border: 1px solid #dde6ef; }}
    h1 {{ margin: 0 0 8px 0; font-size: 24px; color: #0f2d4d; }}
    h2 {{ margin: 0 0 12px 0; font-size: 18px; color: #123e67; }}
    p {{ margin: 6px 0; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border: 1px solid #d9e3ee; padding: 8px; text-align: left; }}
    th {{ background: #eef4fa; color: #1f3f5d; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
    .kpi {{ background: #f8fbff; border: 1px solid #dce8f4; border-radius: 10px; padding: 10px; }}
    .muted {{ color: #52667a; font-size: 12px; }}
    .advice {{ background: #eef7ff; border-left: 4px solid #1971c2; padding: 12px; border-radius: 8px; }}
    @media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class=\"card\">
    <h1>Reporte Predictivo de Finanzas - Fintu</h1>
    <p><strong>Usuario:</strong> {escape(report.user_id)}</p>
    <p><strong>Modo:</strong> {escape(mode_label)}</p>
    <p><strong>Periodo historico:</strong> {escape(report.history_start)} a {escape(report.history_end)} ({escape(report.timezone)})</p>
    <p><strong>Generado (UTC):</strong> {escape(report.generated_at_utc)}</p>
    <p class=\"muted\">Modelo predictivo: {escape(model.model_name)} | confianza: {round(model.confidence_score * 100, 2)}%</p>
  </div>

  <div class=\"card\">
    <h2>Foco de gasto</h2>
    <p><strong>Categoria con mayor gasto:</strong> {escape(focus.top_category_name) if focus.top_category_name else 'Sin datos suficientes'}</p>
    <p><strong>Monto:</strong> {self._money(focus.top_category_amount)}</p>
    <p><strong>Participacion:</strong> {self._pct(focus.top_category_share_pct)}</p>
    <p><strong>Categorias a reducir:</strong></p>
    <ul>{categories_to_reduce_html}</ul>
    <p class=\"muted\">Periodo de referencia: {escape(focus.period_label)}</p>
  </div>

  <div class=\"card\">
    <h2>Consejo de IA</h2>
    <div class=\"advice\">{escape(report.ai_advice)}</div>
    <p class=\"muted\">Modelo Gemini: {ai_model_label}</p>
  </div>

  <div class=\"card\">
    <h2>KPIs Financieros</h2>
    <div class=\"grid\">
      <div class=\"kpi\"><strong>Ingreso historico:</strong> {self._money(kpis.history_income)}</div>
      <div class=\"kpi\"><strong>Gasto historico:</strong> {self._money(kpis.history_expense)}</div>
      <div class=\"kpi\"><strong>Neto historico:</strong> {self._money(kpis.history_net)}</div>
      <div class=\"kpi\"><strong>Tasa de ahorro:</strong> {self._pct(kpis.savings_rate_pct)}</div>
      <div class=\"kpi\"><strong>Ingreso proyectado:</strong> {self._money(kpis.projected_income)}</div>
      <div class=\"kpi\"><strong>Gasto proyectado:</strong> {self._money(kpis.projected_expense)}</div>
      <div class=\"kpi\"><strong>Neto proyectado:</strong> {self._money(kpis.projected_net)}</div>
      <div class=\"kpi\"><strong>Saldo final proyectado:</strong> {self._money(kpis.projected_end_balance) if kpis.projected_end_balance is not None else '-'}</div>
    </div>
  </div>

  <div class=\"card\">
    <h2>Alertas</h2>
    <ul>{alerts_html}</ul>
  </div>

  <div class=\"card\">
    <h2>Proyeccion diaria</h2>
    <table>
      <thead>
        <tr>
          <th>Fecha</th><th>Ingreso</th><th>Gasto</th><th>Neto</th><th>Tx</th><th>Saldo</th>
        </tr>
      </thead>
      <tbody>{forecast_rows}</tbody>
    </table>
  </div>

  <div class=\"card\">
    <h2>Desglose por tipo de cuenta</h2>
    <table>
      <thead>
        <tr>
          <th>Tipo</th><th>Cuentas activas</th><th>Saldo</th><th>Ingresos</th><th>Gastos</th><th>Neto</th><th>Tx</th>
        </tr>
      </thead>
      <tbody>{account_rows}</tbody>
    </table>
  </div>

  <div class=\"card\">
    <h2>Desglose por tipo de transaccion</h2>
    <table>
      <thead>
        <tr>
          <th>Codigo</th><th>Nombre</th><th>Ingresos</th><th>Gastos</th><th>Neto</th><th>Tx</th>
        </tr>
      </thead>
      <tbody>{tx_type_rows}</tbody>
    </table>
  </div>

  <div class=\"card\">
    <h2>Top categorias de gasto</h2>
    <table>
      <thead>
        <tr><th>Categoria</th><th>Monto</th><th>Tx</th></tr>
      </thead>
      <tbody>{categories_rows}</tbody>
    </table>
  </div>
</body>
</html>
"""

    @staticmethod
    def _money(value: float | None) -> str:
        if value is None:
            return "-"
        return f"${value:,.2f}"

    @staticmethod
    def _pct(value: float | None) -> str:
        if value is None:
            return "-"
        return f"{value:.2f}%"

    @staticmethod
    def _mode_label(mode: str) -> str:
        if mode == "daily":
            return "Diario (dia anterior)"
        if mode == "weekly":
            return "Semanal (ultimos 7 dias cerrados)"
        return "Personalizado"
