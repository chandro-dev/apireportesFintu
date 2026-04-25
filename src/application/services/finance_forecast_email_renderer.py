from __future__ import annotations

from html import escape

from src.domain.analytics_entities import FinanceForecastReport


class FinanceForecastEmailRenderer:
    def render(self, *, report: FinanceForecastReport) -> str:
        kpis = report.kpis
        model = report.model
        focus = report.spending_focus
        health_label, health_class, health_message = self._build_period_health(report=report)
        top_category_label = (
            escape(focus.top_category_name) if focus.top_category_name else "Sin datos suficientes"
        )
        expense_income_label = (
            self._pct(kpis.expense_income_ratio * 100)
            if kpis.expense_income_ratio is not None
            else "-"
        )
        confidence_pct = round(model.confidence_score * 100, 2)

        alerts_html = "".join(
            f"<li><strong class='{self._alert_class(alert.level)}'>{escape(alert.level.upper())}</strong> - {escape(alert.message)}</li>"
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
        if not categories_rows:
            categories_rows = "<tr><td colspan='3' class='empty center'>Sin categorias de gasto para el periodo.</td></tr>"

        account_rows = account_rows or "<tr><td colspan='7' class='empty center'>Sin movimientos por tipo de cuenta.</td></tr>"
        tx_type_rows = tx_type_rows or "<tr><td colspan='6' class='empty center'>Sin movimientos por tipo de transaccion.</td></tr>"
        forecast_rows = forecast_rows or "<tr><td colspan='6' class='empty center'>Sin proyeccion disponible.</td></tr>"

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
    * {{ box-sizing: border-box; }}
    body {{ font-family: Arial, Helvetica, sans-serif; color: #0f172a; background: #eef2f8; margin: 0; padding: 20px; }}
    .container {{ max-width: 1140px; margin: 0 auto; display: grid; gap: 18px; }}
    .card {{ background: #ffffff; border-radius: 12px; padding: 20px; border: 1px solid #d5deec; }}
    .hero h1 {{ margin: 0 0 8px 0; font-size: 30px; color: #102a43; }}
    h2 {{ margin: 0 0 12px 0; font-size: 19px; color: #102a43; }}
    p {{ margin: 6px 0; color: #334155; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; min-width: 620px; }}
    th, td {{ border-bottom: 1px solid #e3e9f2; padding: 12px; text-align: left; color: #0f172a; }}
    th {{ background: #f1f5fb; color: #102a43; font-weight: 700; }}
    .table-wrap {{ overflow-x: auto; border: 1px solid #d6dfec; border-radius: 10px; }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }}
    .kpi {{ background: #ffffff; border: 1px solid #d5deec; border-radius: 12px; padding: 16px; }}
    .kpi .label {{ font-size: 11px; color: #475569; text-transform: uppercase; letter-spacing: .45px; }}
    .kpi .value {{ font-size: 22px; margin-top: 6px; font-weight: 700; color: #0f172a; }}
    .kpi .sub {{ margin-top: 5px; font-size: 12px; color: #475569; }}
    .decision-band {{ display: grid; grid-template-columns: 260px 1fr 240px; gap: 16px; align-items: center; }}
    .health-score {{ background: #f8fbff; border: 1px solid #d6dfec; border-radius: 10px; padding: 14px; }}
    .health-score .label {{ color: #475569; font-size: 12px; text-transform: uppercase; letter-spacing: .35px; }}
    .health-score .value {{ font-size: 24px; margin-top: 4px; font-weight: 700; }}
    .ratio-list {{ display: grid; gap: 8px; color: #334155; font-size: 13px; }}
    .ratio-list strong {{ color: #0f172a; }}
    .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
    .muted {{ color: #52667a; font-size: 12px; }}
    .advice {{ background: #f8fbff; border: 1px solid #d6dfec; border-left: 4px solid #1971c2; padding: 14px; border-radius: 8px; line-height: 1.5; }}
    .positive {{ color: #0f766e !important; }}
    .negative {{ color: #b91c1c !important; }}
    .warning {{ color: #b45309 !important; }}
    .empty {{ color: #475569; }}
    .center {{ text-align: center; }}
    @media (max-width: 980px) {{ .kpi-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} .decision-band, .two-col {{ grid-template-columns: 1fr; }} }}
    @media (max-width: 620px) {{ .kpi-grid {{ grid-template-columns: 1fr; }} body {{ padding: 12px; }} }}
  </style>
</head>
<body>
  <main class=\"container\">
  <div class=\"card hero\">
    <h1>{escape(self._title_for_mode(report.analysis_mode))}</h1>
    <p><strong>Usuario:</strong> {escape(report.user_id)}</p>
    <p><strong>Modo:</strong> {escape(mode_label)}</p>
    <p><strong>Periodo historico:</strong> {escape(report.history_start)} a {escape(report.history_end)} ({escape(report.timezone)})</p>
    <p><strong>Generado (UTC):</strong> {escape(report.generated_at_utc)}</p>
    <p class=\"muted\">Modelo predictivo: {escape(model.model_name)} | confianza: {confidence_pct}%</p>
  </div>

  <section class=\"kpi-grid\">
    <article class=\"kpi\"><div class=\"label\">Ingreso historico</div><div class=\"value positive\">{self._money(kpis.history_income)}</div><div class=\"sub\">Promedio diario {self._money(kpis.avg_daily_income)}</div></article>
    <article class=\"kpi\"><div class=\"label\">Gasto historico</div><div class=\"value negative\">{self._money(kpis.history_expense)}</div><div class=\"sub\">Promedio diario {self._money(kpis.avg_daily_expense)}</div></article>
    <article class=\"kpi\"><div class=\"label\">Neto historico</div><div class=\"value {self._amount_class(kpis.history_net)}\">{self._money(kpis.history_net)}</div><div class=\"sub\">Ahorro {self._pct(kpis.savings_rate_pct)}</div></article>
    <article class=\"kpi\"><div class=\"label\">Neto proyectado</div><div class=\"value {self._amount_class(kpis.projected_net)}\">{self._money(kpis.projected_net)}</div><div class=\"sub\">Horizonte: {model.forecast_days} dias</div></article>
  </section>

  <div class=\"card decision-band\">
    <div class=\"health-score\">
      <div class=\"label\">Salud del periodo</div>
      <div class=\"value {health_class}\">{escape(health_label)}</div>
      <div class=\"muted\">Basado en flujo, ahorro, proyeccion y alertas</div>
    </div>
    <div>{escape(health_message)}</div>
    <div class=\"ratio-list\">
      <div><strong>Gasto/ingreso:</strong> {expense_income_label}</div>
      <div><strong>Volatilidad gasto:</strong> {self._money(kpis.expense_volatility)}</div>
      <div><strong>Saldo proyectado:</strong> {self._money(kpis.projected_end_balance) if kpis.projected_end_balance is not None else '-'}</div>
    </div>
  </div>

  <div class=\"card\">
    <h2>Consejo de IA</h2>
    <div class=\"advice\">{escape(report.ai_advice)}</div>
    <p class=\"muted\">Modelo Gemini: {ai_model_label}</p>
  </div>

  <div class=\"two-col\">
  <div class=\"card\">
    <h2>Foco de gasto</h2>
    <p><strong>Categoria con mayor gasto:</strong> {top_category_label}</p>
    <p><strong>Monto:</strong> {self._money(focus.top_category_amount)}</p>
    <p><strong>Participacion:</strong> {self._pct(focus.top_category_share_pct)}</p>
    <p><strong>Categorias a reducir primero:</strong></p>
    <ul>{categories_to_reduce_html}</ul>
    <p class=\"muted\">Periodo de referencia: {escape(focus.period_label)}</p>
  </div>

  <div class=\"card\">
    <h2>Alertas</h2>
    <ul>{alerts_html}</ul>
  </div>
  </div>

  <div class=\"card\">
    <h2>Proyeccion diaria</h2>
    <div class=\"table-wrap\"><table>
      <thead>
        <tr>
          <th>Fecha</th><th>Ingreso</th><th>Gasto</th><th>Neto</th><th>Tx</th><th>Saldo</th>
        </tr>
      </thead>
      <tbody>{forecast_rows}</tbody>
    </table></div>
  </div>

  <div class=\"card\">
    <h2>Desglose por tipo de cuenta</h2>
    <div class=\"table-wrap\"><table>
      <thead>
        <tr>
          <th>Tipo</th><th>Cuentas activas</th><th>Saldo</th><th>Ingresos</th><th>Gastos</th><th>Neto</th><th>Tx</th>
        </tr>
      </thead>
      <tbody>{account_rows}</tbody>
    </table></div>
  </div>

  <div class=\"card\">
    <h2>Desglose por tipo de transaccion</h2>
    <div class=\"table-wrap\"><table>
      <thead>
        <tr>
          <th>Codigo</th><th>Nombre</th><th>Ingresos</th><th>Gastos</th><th>Neto</th><th>Tx</th>
        </tr>
      </thead>
      <tbody>{tx_type_rows}</tbody>
    </table></div>
  </div>

  <div class=\"card\">
    <h2>Top categorias de gasto</h2>
    <div class=\"table-wrap\"><table>
      <thead>
        <tr><th>Categoria</th><th>Monto</th><th>Tx</th></tr>
      </thead>
      <tbody>{categories_rows}</tbody>
    </table></div>
  </div>
  </main>
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

    @staticmethod
    def _title_for_mode(mode: str) -> str:
        if mode == "daily":
            return "Snapshot Financiero Diario"
        if mode == "weekly":
            return "Reporte Financiero Semanal"
        return "Reporte Financiero"

    @staticmethod
    def _amount_class(value: float | None) -> str:
        if value is not None and value < 0:
            return "negative"
        return "positive"

    @staticmethod
    def _alert_class(level: str) -> str:
        normalized = level.lower()
        if normalized == "critical":
            return "negative"
        if normalized == "warning":
            return "warning"
        return "positive"

    @staticmethod
    def _build_period_health(*, report: FinanceForecastReport) -> tuple[str, str, str]:
        kpis = report.kpis
        has_critical = any(alert.level.lower() == "critical" for alert in report.alerts)
        has_warning = any(alert.level.lower() == "warning" for alert in report.alerts)

        if has_critical or kpis.projected_end_balance is not None and kpis.projected_end_balance < 0:
            return (
                "Critica",
                "negative",
                "La tendencia puede dejar el periodo con deficit o saldo negativo. Congela gasto discrecional, revisa pagos fijos y prioriza liquidez antes de asumir nuevos compromisos.",
            )

        if kpis.projected_net < 0 or has_warning:
            return (
                "Vigilancia",
                "warning",
                "La proyeccion muestra presion de caja. Define topes semanales por categoria y recorta primero los gastos con mayor participacion.",
            )

        if kpis.savings_rate_pct is not None and kpis.savings_rate_pct >= 20:
            return (
                "Solida",
                "positive",
                "El periodo mantiene margen de ahorro sano. Se recomienda automatizar el excedente y conservar control sobre categorias variables para no deteriorar la proyeccion.",
            )

        return (
            "Estable",
            "positive",
            "El periodo esta controlado, aunque el margen de ahorro puede mejorar. Usa el foco de gasto para aplicar un recorte pequeno y medible durante la semana.",
        )
