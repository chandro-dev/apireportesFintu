from __future__ import annotations

import math
from io import BytesIO
from html import escape

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from src.domain.report_entities import CategoryPoint, DailyReport


class DailyReportHtmlRenderer:
    def render(self, *, report: DailyReport, weekly_pie_image_src: str | None = None) -> str:
        summary = report.summary
        comparison = report.comparison

        weekly_expense_total = round(sum(item.amount for item in report.weekly_expense_categories), 2)
        weekly_expense_svg = self._build_weekly_pie_svg(
            categories=report.weekly_expense_categories,
            total=weekly_expense_total,
        )
        weekly_expense_legend = self._build_category_rows(
            categories=report.weekly_expense_categories,
            total=max(0.01, weekly_expense_total),
            bar_color="#d946ef",
        )

        outgoing_total = round(
            sum(item.amount for item in report.recent_outgoing_normal_transactions),
            2,
        )

        outgoing_rows = "".join(
            (
                "<tr>"
                f"<td>{escape(item.occurred_at)}</td>"
                f"<td>{escape(item.account_name)}</td>"
                f"<td>{escape(item.category_name)}</td>"
                f"<td>{escape(item.title)}</td>"
                f"<td class='amount-col'>{self._money(item.amount)}</td>"
                "</tr>"
            )
            for item in report.recent_outgoing_normal_transactions
        )
        if not outgoing_rows:
            outgoing_rows = "<tr><td colspan='5' class='empty center'>No hay salidas recientes en cuentas normales.</td></tr>"

        normal_accounts_cards = "".join(
            (
                "<article class='account-card'>"
                f"<div class='account-title'>{escape(account.account_name)}</div>"
                f"<div class='account-bank'>{escape(account.bank_name) if account.bank_name else 'Sin banco asociado'}</div>"
                f"<div class='account-balance'>{self._money(account.current_amount)}</div>"
                "</article>"
            )
            for account in report.normal_accounts
        )
        if not normal_accounts_cards:
            normal_accounts_cards = "<p class='empty'>No hay cuentas normales reportables activas.</p>"

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
        debt_class = "negative" if report.credit_cards_total_debt > 0 else "positive"

        if weekly_pie_image_src:
            pie_visual = (
                f"<img src='{escape(weekly_pie_image_src)}' alt='Grafico de gasto semanal por categoria' "
                "style='width:320px;height:320px;display:block;border:1px solid #d6dfec;border-radius:50%;background:#ffffff;'/>"
            )
        else:
            pie_visual = weekly_expense_svg

        return f"""
<!DOCTYPE html>
<html lang=\"es\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Fintu - Reporte Diario Visual</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: #0f172a;
      background: #eef2f8;
      padding: 20px;
    }}
    .container {{ max-width: 1140px; margin: 0 auto; display: grid; gap: 24px; }}
    .hero {{
      background: #ffffff;
      border: 1px solid #d5deec;
      border-radius: 14px;
      padding: 22px;
    }}
    .hero h1 {{ margin: 0 0 8px 0; font-size: 30px; color: #0b2b4a; }}
    .hero p {{ margin: 4px 0; color: #334155; }}
    .pill {{
      display: inline-block;
      margin-top: 10px;
      padding: 8px 12px;
      border-radius: 999px;
      font-weight: 700;
      font-size: 13px;
      border: 1px solid #bfd0e8;
      background: #f8fbff;
    }}

    .kpi-grid {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 16px; }}
    .kpi {{ background: #ffffff; border: 1px solid #d5deec; border-radius: 12px; padding: 16px; }}
    .kpi .label {{ font-size: 11px; color: #475569; text-transform: uppercase; letter-spacing: .45px; }}
    .kpi .value {{ font-size: 23px; margin-top: 6px; font-weight: 700; color: #0f172a; }}
    .kpi .sub {{ margin-top: 5px; font-size: 12px; color: #475569; }}

    .positive {{ color: #0f766e !important; }}
    .negative {{ color: #b91c1c !important; }}

    .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
    .card {{ background: #ffffff; border: 1px solid #d5deec; border-radius: 12px; padding: 20px; }}
    .card h2 {{ margin: 0 0 10px 0; font-size: 19px; color: #102a43; }}

    .pie-layout {{ display: grid; grid-template-columns: 320px 1fr; gap: 22px; align-items: center; }}
    .pie-box {{ width: 320px; height: 320px; display: flex; align-items: center; justify-content: center; }}

    .rows {{ display: grid; gap: 12px; margin-top: 14px; }}
    .row {{ display: grid; grid-template-columns: 1fr auto; gap: 12px; align-items: center; }}
    .row .meta {{ color: #475569; font-size: 12px; margin-top: 2px; }}
    .bar {{ height: 8px; border-radius: 99px; background: #e6ebf4; margin-top: 6px; overflow: hidden; border: 1px solid #d6dfec; }}
    .bar > span {{ display: block; height: 100%; border-radius: 99px; }}
    .value {{ font-weight: 700; color: #0f172a; }}

    .table-wrap {{ overflow-x: auto; border: 1px solid #d6dfec; border-radius: 10px; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 560px; }}
    th, td {{ padding: 14px; border-bottom: 1px solid #e3e9f2; text-align: left; font-size: 13px; color: #0f172a; }}
    th {{ background: #f1f5fb; color: #102a43; font-weight: 700; }}
    .amount-col {{ font-weight: 700; color: #b91c1c; }}

    .accounts-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }}
    .account-card {{ background: #f8fbff; border: 1px solid #d6dfec; border-radius: 10px; padding: 12px; }}
    .account-title {{ font-weight: 700; color: #102a43; }}
    .account-bank {{ margin-top: 3px; color: #475569; font-size: 12px; }}
    .account-balance {{ margin-top: 7px; font-size: 21px; font-weight: 700; color: #0f766e; }}

    .movement-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    .movement-card {{ background: #f8fbff; border: 1px solid #d6dfec; border-radius: 10px; padding: 12px; }}
    .movement-header {{ display: flex; justify-content: space-between; gap: 8px; color: #475569; font-size: 12px; }}
    .movement-total {{ margin-top: 6px; font-size: 20px; font-weight: 700; color: #0f172a; }}
    .movement-meta {{ margin-top: 4px; color: #475569; font-size: 12px; }}

    .insights ul {{ margin: 0; padding-left: 18px; }}
    .insights li {{ margin: 9px 0; line-height: 1.45; color: #0f172a; }}
    .empty {{ color: #475569; margin: 6px 0; }}
    .center {{ text-align: center; }}

    @media (max-width: 1100px) {{
      .kpi-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .accounts-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 860px) {{
      .two-col {{ grid-template-columns: 1fr; }}
      .kpi-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .accounts-grid {{ grid-template-columns: 1fr; }}
      .movement-grid {{ grid-template-columns: 1fr; }}
      .pie-layout {{ grid-template-columns: 1fr; }}
      .pie-box {{ width: 100%; }}
    }}
  </style>
</head>
<body>
  <main class=\"container\">
    <section class=\"hero\">
      <h1>Snapshot Financiero Diario</h1>
      <p>Usuario: {escape(report.user_id)} | Fecha operativa: {escape(summary.day)} | Zona horaria: {escape(report.timezone)}</p>
      <p>Generado en UTC: {escape(report.generated_at_utc)}</p>
      <span class=\"pill {net_class}\">Neto del dia: {self._money(summary.net)}</span>
    </section>

    <section class=\"kpi-grid\">
      <article class=\"kpi\">
        <div class=\"label\">Cuentas normales</div>
        <div class=\"value positive\">{self._money(report.normal_accounts_total_balance)}</div>
        <div class=\"sub\">Valor actual disponible</div>
      </article>
      <article class=\"kpi\">
        <div class=\"label\">Deuda tarjetas</div>
        <div class=\"value {debt_class}\">{self._money(report.credit_cards_total_debt)}</div>
        <div class=\"sub\">Estimado al dia de hoy</div>
      </article>
      <article class=\"kpi\">
        <div class=\"label\">Ingresos del dia</div>
        <div class=\"value\">{self._money(summary.income)}</div>
        <div class=\"sub\">Vs {escape(comparison.previous_day)}: {self._signed_money(comparison.income_delta)}</div>
      </article>
      <article class=\"kpi\">
        <div class=\"label\">Gastos del dia</div>
        <div class=\"value\">{self._money(summary.expense)}</div>
        <div class=\"sub\">Vs {escape(comparison.previous_day)}: {self._signed_money(comparison.expense_delta)}</div>
      </article>
      <article class=\"kpi\">
        <div class=\"label\">Ultimas 10 salidas</div>
        <div class=\"value\">{self._money(outgoing_total)}</div>
        <div class=\"sub\">{len(report.recent_outgoing_normal_transactions)} transacciones</div>
      </article>
    </section>

    <section class=\"two-col\">
      <article class=\"card\">
        <h2>Gasto semanal por categoria</h2>
        <p class=\"empty\">Ventana: {escape(report.weekly_expense_window_start)} a {escape(report.weekly_expense_window_end)}</p>
        <div class=\"pie-layout\">
          <div class=\"pie-box\">{pie_visual}</div>
          <div>
            <div class=\"value\">{self._money(weekly_expense_total)}</div>
            <div class=\"empty\">Total gasto semanal</div>
            <div class=\"rows\">{weekly_expense_legend}</div>
          </div>
        </div>
      </article>

      <article class=\"card\">
        <h2>Ultimas 10 transacciones salientes (cuentas normales)</h2>
        <div class=\"table-wrap\">
          <table>
            <thead>
              <tr>
                <th>Fecha</th><th>Cuenta</th><th>Categoria</th><th>Concepto</th><th>Monto</th>
              </tr>
            </thead>
            <tbody>{outgoing_rows}</tbody>
          </table>
        </div>
      </article>
    </section>

    <section class=\"card\">
      <h2>Valor actual en cuentas normales</h2>
      <div class=\"accounts-grid\">{normal_accounts_cards}</div>
    </section>

    <section class=\"card\">
      <h2>Cuentas con mayor movimiento en el dia</h2>
      <div class=\"movement-grid\">{movement_cards}</div>
    </section>

    <section class=\"card insights\">
      <h2>Lectura rapida</h2>
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
            return "<p class='empty'>No hay categorias de gasto para la semana seleccionada.</p>"

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

    def _build_weekly_pie_svg(self, *, categories: list[CategoryPoint], total: float) -> str:
        size = 320
        cx = size / 2
        cy = size / 2
        radius = 126
        inner_radius = 68

        if not categories or total <= 0:
            return (
                "<svg width='320' height='320' viewBox='0 0 320 320' role='img' aria-label='Sin gastos semanales'>"
                "<circle cx='160' cy='160' r='126' fill='#e2e8f0' stroke='#cbd5e1' stroke-width='1'/>"
                "<circle cx='160' cy='160' r='68' fill='#ffffff' stroke='#cbd5e1' stroke-width='1'/>"
                "<text x='160' y='166' text-anchor='middle' font-size='12' fill='#334155'>Sin gasto</text>"
                "</svg>"
            )

        colors = [
            "#ef4444",
            "#f97316",
            "#f59e0b",
            "#ec4899",
            "#d946ef",
            "#8b5cf6",
            "#3b82f6",
            "#06b6d4",
        ]

        start_angle = -90.0
        slices: list[str] = []

        for idx, item in enumerate(categories):
            sweep = (item.amount / total) * 360
            end_angle = start_angle + sweep
            large_arc = 1 if sweep > 180 else 0

            x1 = cx + radius * math.cos(math.radians(start_angle))
            y1 = cy + radius * math.sin(math.radians(start_angle))
            x2 = cx + radius * math.cos(math.radians(end_angle))
            y2 = cy + radius * math.sin(math.radians(end_angle))

            path = (
                f"M {cx:.2f} {cy:.2f} "
                f"L {x1:.2f} {y1:.2f} "
                f"A {radius:.2f} {radius:.2f} 0 {large_arc} 1 {x2:.2f} {y2:.2f} Z"
            )
            color = colors[idx % len(colors)]
            slices.append(f"<path d='{path}' fill='{color}' stroke='#ffffff' stroke-width='1' />")

            start_angle = end_angle

        return (
            "<svg width='320' height='320' viewBox='0 0 320 320' role='img' aria-label='Distribucion semanal de gastos por categoria'>"
            + "".join(slices)
            + f"<circle cx='{cx:.2f}' cy='{cy:.2f}' r='{inner_radius:.2f}' fill='#ffffff' stroke='#e2e8f0' stroke-width='1'/>"
            + f"<text x='{cx:.2f}' y='{cy - 4:.2f}' text-anchor='middle' font-size='12' fill='#334155'>Semana</text>"
            + f"<text x='{cx:.2f}' y='{cy + 14:.2f}' text-anchor='middle' font-size='12' fill='#0f172a'>{self._money(total)}</text>"
            + "</svg>"
        )

    def build_weekly_pie_png(self, *, report: DailyReport) -> bytes:
        values = [item.amount for item in report.weekly_expense_categories if item.amount > 0]
        labels = [item.category_name for item in report.weekly_expense_categories if item.amount > 0]

        colors = [
            "#ef4444",
            "#f97316",
            "#f59e0b",
            "#ec4899",
            "#d946ef",
            "#8b5cf6",
            "#3b82f6",
            "#06b6d4",
        ]

        fig, ax = plt.subplots(figsize=(5.6, 5.6), dpi=150)
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")

        if values:
            ax.pie(
                values,
                labels=labels,
                colors=[colors[idx % len(colors)] for idx in range(len(values))],
                autopct="%1.0f%%",
                startangle=90,
                textprops={"fontsize": 8, "color": "#0f172a"},
                wedgeprops={"linewidth": 1, "edgecolor": "white"},
            )
            ax.axis("equal")
        else:
            ax.text(
                0.5,
                0.5,
                "Sin gasto semanal",
                ha="center",
                va="center",
                fontsize=10,
                color="#334155",
                transform=ax.transAxes,
            )
            ax.axis("off")

        buffer = BytesIO()
        fig.savefig(buffer, format="png", bbox_inches="tight", facecolor="white")
        plt.close(fig)
        buffer.seek(0)
        return buffer.read()

    @staticmethod
    def _money(value: float) -> str:
        return f"${value:,.2f}"

    @staticmethod
    def _signed_money(value: float) -> str:
        if value >= 0:
            return f"+${value:,.2f}"
        return f"-${abs(value):,.2f}"
