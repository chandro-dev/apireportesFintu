from __future__ import annotations

from html import escape

from src.domain.report_entities import CategoryPoint, DailyReport


class DailyReportHtmlRenderer:
    def render(self, *, report: DailyReport) -> str:
        summary = report.summary
        comparison = report.comparison

        expense_chart = self._build_donut(
            values=[item.amount for item in report.top_expense_categories],
            colors=["#ef4444", "#f97316", "#f59e0b", "#fb7185", "#f43f5e", "#dc2626"],
        )
        income_chart = self._build_donut(
            values=[item.amount for item in report.top_income_categories],
            colors=["#22c55e", "#16a34a", "#10b981", "#84cc16", "#4ade80", "#14b8a6"],
        )

        expense_rows = self._build_category_rows(
            categories=report.top_expense_categories,
            total=max(0.01, summary.expense),
            bar_color="#ef4444",
        )
        income_rows = self._build_category_rows(
            categories=report.top_income_categories,
            total=max(0.01, summary.income),
            bar_color="#16a34a",
        )

        movement_cards = "".join(
            (
                "<div class='movement-card'>"
                f"<div class='movement-header'><span>{escape(account.account_name)}</span><span>{escape(account.account_type)}</span></div>"
                f"<div class='movement-total'>{self._money(account.total_movement)}</div>"
                f"<div class='movement-meta'>Ingresos {self._money(account.income)} | Gastos {self._money(account.expense)} | {account.transactions_count} tx</div>"
                "</div>"
            )
            for account in report.top_accounts_movement
        )
        if not movement_cards:
            movement_cards = "<p class='empty'>No hubo movimiento en cuentas reportables para este dia.</p>"

        insights_html = "".join(f"<li>{escape(item)}</li>" for item in report.insights)
        if not insights_html:
            insights_html = "<li>Sin insights para este dia.</li>"

        net_class = "positive" if summary.net >= 0 else "negative"

        return f"""
<!DOCTYPE html>
<html lang=\"es\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Fintu - Reporte Diario</title>
  <style>
    :root {{
      --bg: #0b1220;
      --card: #111a2e;
      --card-soft: #17233a;
      --text: #e8eefc;
      --muted: #8ea2c9;
      --green: #22c55e;
      --red: #ef4444;
      --amber: #f59e0b;
      --line: #233454;
      --shadow: 0 16px 40px rgba(0,0,0,.35);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "SF Pro Display", "Helvetica Neue", sans-serif;
      background: radial-gradient(1200px 700px at 20% -10%, #1f2d4d 0%, transparent 40%),
                  radial-gradient(900px 600px at 100% 0%, #173a5a 0%, transparent 35%),
                  var(--bg);
      color: var(--text);
      padding: 24px;
    }}
    .container {{ max-width: 1080px; margin: 0 auto; display: grid; gap: 18px; }}
    .hero {{
      background: linear-gradient(135deg, #0f172a 0%, #132b46 45%, #0d3b35 100%);
      border: 1px solid #25436b;
      border-radius: 18px;
      padding: 22px;
      box-shadow: var(--shadow);
    }}
    .hero h1 {{ margin: 0 0 8px 0; font-size: 30px; letter-spacing: .3px; }}
    .hero p {{ margin: 4px 0; color: var(--muted); }}
    .net-pill {{
      display: inline-flex;
      margin-top: 10px;
      padding: 8px 14px;
      border-radius: 999px;
      font-weight: 700;
      font-size: 14px;
      border: 1px solid #2d4d7c;
      background: rgba(255,255,255,.06);
    }}
    .net-pill.positive {{ color: #86efac; border-color: #14532d; background: rgba(34,197,94,.15); }}
    .net-pill.negative {{ color: #fecaca; border-color: #7f1d1d; background: rgba(239,68,68,.15); }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
    .kpi {{ background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 16px; }}
    .kpi .label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .5px; }}
    .kpi .value {{ margin-top: 6px; font-size: 24px; font-weight: 700; }}
    .kpi .delta {{ margin-top: 6px; font-size: 13px; color: var(--muted); }}
    .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 16px; box-shadow: var(--shadow); }}
    .card h2 {{ margin: 0 0 10px 0; font-size: 18px; }}
    .chart-wrap {{ display: flex; align-items: center; gap: 14px; margin-bottom: 8px; }}
    .donut {{ width: 110px; height: 110px; border-radius: 50%; border: 1px solid #2a3e63; flex: 0 0 auto; position: relative; }}
    .donut::after {{ content: ""; position: absolute; inset: 24px; border-radius: 50%; background: var(--card); border: 1px solid #2a3e63; }}
    .rows {{ display: grid; gap: 8px; }}
    .row {{ display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: center; }}
    .row .meta {{ color: var(--muted); font-size: 12px; margin-top: 2px; }}
    .bar {{ height: 8px; border-radius: 99px; background: var(--card-soft); margin-top: 6px; overflow: hidden; border: 1px solid #25395f; }}
    .bar > span {{ display: block; height: 100%; border-radius: 99px; }}
    .value {{ font-weight: 700; }}
    .movement-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    .movement-card {{ background: var(--card-soft); border: 1px solid #2a3e63; border-radius: 12px; padding: 12px; }}
    .movement-header {{ display: flex; justify-content: space-between; gap: 8px; color: var(--muted); font-size: 12px; }}
    .movement-total {{ margin-top: 6px; font-size: 20px; font-weight: 700; }}
    .movement-meta {{ margin-top: 4px; color: var(--muted); font-size: 12px; }}
    .insights ul {{ margin: 0; padding-left: 18px; }}
    .insights li {{ margin: 7px 0; line-height: 1.38; }}
    .empty {{ color: var(--muted); margin: 4px 0; }}
    @media (max-width: 920px) {{
      .kpi-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .two-col {{ grid-template-columns: 1fr; }}
      .movement-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main class=\"container\">
    <section class=\"hero\">
      <h1>Reporte Diario Operativo</h1>
      <p>Usuario: {escape(report.user_id)} | Fecha: {escape(summary.day)} | Zona horaria: {escape(report.timezone)}</p>
      <p>Generado en UTC: {escape(report.generated_at_utc)}</p>
      <span class=\"net-pill {net_class}\">Neto del dia: {self._money(summary.net)}</span>
    </section>

    <section class=\"kpi-grid\">
      <article class=\"kpi\">
        <div class=\"label\">Ingresos del dia</div>
        <div class=\"value\">{self._money(summary.income)}</div>
        <div class=\"delta\">Vs {escape(comparison.previous_day)}: {self._signed_money(comparison.income_delta)}</div>
      </article>
      <article class=\"kpi\">
        <div class=\"label\">Gastos del dia</div>
        <div class=\"value\">{self._money(summary.expense)}</div>
        <div class=\"delta\">Vs {escape(comparison.previous_day)}: {self._signed_money(comparison.expense_delta)}</div>
      </article>
      <article class=\"kpi\">
        <div class=\"label\">Balance neto</div>
        <div class=\"value\">{self._money(summary.net)}</div>
        <div class=\"delta\">Vs {escape(comparison.previous_day)}: {self._signed_money(comparison.net_delta)}</div>
      </article>
      <article class=\"kpi\">
        <div class=\"label\">Transacciones</div>
        <div class=\"value\">{summary.transactions_count}</div>
        <div class=\"delta\">Solo cuentas y movimientos reportables</div>
      </article>
    </section>

    <section class=\"two-col\">
      <article class=\"card\">
        <h2>Top categorias de gasto</h2>
        <div class=\"chart-wrap\">
          <div class=\"donut\" style=\"background:{expense_chart};\"></div>
          <p class=\"empty\">Distribucion del gasto diario por categoria.</p>
        </div>
        <div class=\"rows\">{expense_rows}</div>
      </article>

      <article class=\"card\">
        <h2>Top categorias de ingreso</h2>
        <div class=\"chart-wrap\">
          <div class=\"donut\" style=\"background:{income_chart};\"></div>
          <p class=\"empty\">Distribucion del ingreso diario por categoria.</p>
        </div>
        <div class=\"rows\">{income_rows}</div>
      </article>
    </section>

    <section class=\"card\">
      <h2>Cuentas con mayor movimiento</h2>
      <div class=\"movement-grid\">{movement_cards}</div>
    </section>

    <section class=\"card insights\">
      <h2>Lectura rapida del dia</h2>
      <ul>{insights_html}</ul>
    </section>
  </main>
</body>
</html>
"""

    def _build_category_rows(
        self,
        *,
        categories: list[CategoryPoint],
        total: float,
        bar_color: str,
    ) -> str:
        if not categories:
            return "<p class='empty'>No hay categorias registradas en este flujo para el dia.</p>"

        rows = []
        for item in categories:
            pct = max(0.0, min(100.0, round((item.amount / total) * 100, 2)))
            rows.append(
                "".join(
                    [
                        "<div class='row'>",
                        "<div>",
                        f"<div>{escape(item.category_name)}</div>",
                        f"<div class='meta'>{item.transactions_count} tx | {pct}%</div>",
                        f"<div class='bar'><span style='width:{pct}%;background:{bar_color};'></span></div>",
                        "</div>",
                        f"<div class='value'>{self._money(item.amount)}</div>",
                        "</div>",
                    ]
                )
            )

        return "".join(rows)

    @staticmethod
    def _build_donut(*, values: list[float], colors: list[str]) -> str:
        if not values or sum(values) <= 0:
            return "conic-gradient(#263754 0 360deg)"

        total = sum(values)
        start = 0.0
        parts: list[str] = []
        for idx, value in enumerate(values):
            share = (value / total) * 360
            end = start + share
            color = colors[idx % len(colors)]
            parts.append(f"{color} {start:.2f}deg {end:.2f}deg")
            start = end

        if start < 360:
            parts.append(f"#263754 {start:.2f}deg 360deg")

        return f"conic-gradient({', '.join(parts)})"

    @staticmethod
    def _money(value: float) -> str:
        return f"${value:,.2f}"

    @staticmethod
    def _signed_money(value: float) -> str:
        if value >= 0:
            return f"+${value:,.2f}"
        return f"-${abs(value):,.2f}"
