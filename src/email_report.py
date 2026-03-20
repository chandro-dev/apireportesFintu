from __future__ import annotations

import math
import smtplib
import ssl
from email.message import EmailMessage
from html import escape
from typing import Any

from src.config import SmtpSettings


def _money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "$0.00"


def _int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _safe(value: Any) -> str:
    if value is None:
        return ""
    return escape(str(value))


def _render_summary_cards(summary: dict[str, Any]) -> str:
    items = [
        ("Cuentas", _int(summary.get("accounts_count"))),
        ("Cuentas activas", _int(summary.get("active_accounts"))),
        ("Transacciones", _int(summary.get("transactions_count"))),
        ("Ingresos", _money(summary.get("income"))),
        ("Gastos", _money(summary.get("expense"))),
        ("Neto", _money(summary.get("net"))),
        ("Saldo inicial est.", _money(summary.get("estimated_opening_balance"))),
        ("Saldo final est.", _money(summary.get("estimated_closing_balance"))),
    ]

    cards = []
    for label, value in items:
        cards.append(
            f"""
            <div class=\"card\">
              <div class=\"card-label\">{_safe(label)}</div>
              <div class=\"card-value\">{_safe(value)}</div>
            </div>
            """
        )
    return "\n".join(cards)


def _render_daily_overview(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p class='muted'>Sin datos diarios para esta semana.</p>"

    body = []
    for row in rows:
        body.append(
            f"""
            <tr>
              <td>{_safe(row.get('date'))}</td>
              <td class=\"num\">{_money(row.get('income'))}</td>
              <td class=\"num\">{_money(row.get('expense'))}</td>
              <td class=\"num\">{_money(row.get('net'))}</td>
              <td class=\"num\">{_int(row.get('transactions_count'))}</td>
            </tr>
            """
        )

    return f"""
      <table>
        <thead>
          <tr>
            <th>Fecha</th>
            <th class=\"num\">Ingresos</th>
            <th class=\"num\">Gastos</th>
            <th class=\"num\">Neto</th>
            <th class=\"num\">Transacciones</th>
          </tr>
        </thead>
        <tbody>
          {''.join(body)}
        </tbody>
      </table>
    """


def _render_categories(title: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return f"<h4>{_safe(title)}</h4><p class='muted'>Sin categorias.</p>"

    body = []
    for row in rows:
        body.append(
            f"""
            <tr>
              <td>{_safe(row.get('category_name'))}</td>
              <td class=\"num\">{_money(row.get('amount'))}</td>
              <td class=\"num\">{_int(row.get('transactions_count'))}</td>
            </tr>
            """
        )

    return f"""
      <h4>{_safe(title)}</h4>
      <table>
        <thead>
          <tr>
            <th>Categoria</th>
            <th class=\"num\">Monto</th>
            <th class=\"num\">Tx</th>
          </tr>
        </thead>
        <tbody>
          {''.join(body)}
        </tbody>
      </table>
    """


def _pie_point(cx: float, cy: float, radius: float, angle_deg: float) -> tuple[float, float]:
    angle_rad = math.radians(angle_deg)
    return (cx + radius * math.cos(angle_rad), cy + radius * math.sin(angle_rad))


def _render_expense_pie(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p class='muted'>Sin categorias de gasto para graficar.</p>"

    expense_rows = [row for row in rows if _float(row.get("amount")) > 0]
    total = sum(_float(row.get("amount")) for row in expense_rows)
    if total <= 0:
        return "<p class='muted'>Sin montos de gasto para graficar.</p>"

    colors = ["#2563eb", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#06b6d4"]
    slices: list[str] = []
    legend: list[str] = []
    center = 100.0
    radius = 86.0
    start_angle = -90.0

    for idx, row in enumerate(expense_rows[:6]):
        amount = _float(row.get("amount"))
        if amount <= 0:
            continue

        sweep = (amount / total) * 360.0
        end_angle = start_angle + sweep
        x1, y1 = _pie_point(center, center, radius, start_angle)
        x2, y2 = _pie_point(center, center, radius, end_angle)
        large_arc = 1 if sweep > 180 else 0
        color = colors[idx % len(colors)]

        path = (
            f"M {center:.2f} {center:.2f} "
            f"L {x1:.2f} {y1:.2f} "
            f"A {radius:.2f} {radius:.2f} 0 {large_arc} 1 {x2:.2f} {y2:.2f} Z"
        )
        slices.append(f"<path d=\"{path}\" fill=\"{color}\"></path>")

        pct = (amount / total) * 100
        legend.append(
            "<li>"
            f"<span class=\"dot\" style=\"background:{color};\"></span>"
            f"<span>{_safe(row.get('category_name'))}</span>"
            f"<span class=\"legend-num\">{_money(amount)} ({pct:.1f}%)</span>"
            "</li>"
        )
        start_angle = end_angle

    return f"""
      <div class="pie-wrap">
        <svg viewBox="0 0 200 200" width="220" height="220" role="img" aria-label="Distribucion de gastos por categoria">
          {''.join(slices)}
        </svg>
        <ul class="legend">
          {''.join(legend)}
        </ul>
      </div>
    """


def _render_latest_categories(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p class='muted'>Sin categorias recientes.</p>"

    body = []
    for row in rows:
        body.append(
            f"""
            <tr>
              <td>{_safe(row.get('category_name'))}</td>
              <td>{_safe(row.get('flow'))}</td>
              <td>{_safe(row.get('last_occurred_at'))}</td>
              <td class="num">{_money(row.get('last_amount'))}</td>
            </tr>
            """
        )

    return f"""
      <table>
        <thead>
          <tr>
            <th>Categoria</th>
            <th>Flujo</th>
            <th>Ultimo uso</th>
            <th class="num">Ultimo monto</th>
          </tr>
        </thead>
        <tbody>
          {''.join(body)}
        </tbody>
      </table>
    """


def _render_account(account: dict[str, Any]) -> str:
    daily_rows = account.get("daily", [])
    daily_html = _render_daily_overview(daily_rows)

    return f"""
      <section class=\"account\">
        <h3>{_safe(account.get('account_name'))}</h3>
        <p class=\"muted\">
          Tipo: {_safe(account.get('account_type'))} |
          Banco: {_safe(account.get('bank_name') or 'N/A')} |
          Activa: {_safe('Si' if account.get('is_active') else 'No')}
        </p>
        <div class=\"mini-grid\">
          <div><span>Saldo actual</span><strong>{_money(account.get('current_amount'))}</strong></div>
          <div><span>Saldo inicial est.</span><strong>{_money(account.get('estimated_opening_balance'))}</strong></div>
          <div><span>Saldo final est.</span><strong>{_money(account.get('estimated_closing_balance'))}</strong></div>
          <div><span>Ingresos</span><strong>{_money(account.get('income'))}</strong></div>
          <div><span>Gastos</span><strong>{_money(account.get('expense'))}</strong></div>
          <div><span>Neto</span><strong>{_money(account.get('net'))}</strong></div>
          <div><span>Transacciones</span><strong>{_int(account.get('transactions_count'))}</strong></div>
        </div>
        <div class=\"account-daily\">
          <h4>Detalle diario</h4>
          {daily_html}
        </div>
      </section>
    """


def build_weekly_report_html(report: dict[str, Any]) -> str:
    week = report.get("week", {})
    summary = report.get("summary", {})
    top_categories = report.get("top_categories", {})
    latest_categories = report.get("latest_categories", [])
    accounts = report.get("accounts", [])
    user_email = report.get("user_email")

    account_sections = "\n".join(_render_account(a) for a in accounts)
    daily_overview_html = _render_daily_overview(report.get("daily_overview", []))
    expense_pie_html = _render_expense_pie(top_categories.get("expense", []))
    latest_categories_html = _render_latest_categories(latest_categories)

    top_expense_html = _render_categories("Top categorias de gasto", top_categories.get("expense", []))
    top_income_html = _render_categories("Top categorias de ingreso", top_categories.get("income", []))

    return f"""
<!DOCTYPE html>
<html lang=\"es\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Reporte semanal</title>
  <style>
    body {{ font-family: Arial, sans-serif; background: #f4f7fb; color: #1f2937; margin: 0; padding: 0; }}
    .container {{ max-width: 980px; margin: 0 auto; padding: 24px; }}
    .header {{ background: #0f172a; color: #fff; border-radius: 12px; padding: 20px; }}
    .header h1 {{ margin: 0 0 8px; font-size: 24px; }}
    .header p {{ margin: 0; color: #cbd5e1; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin-top: 16px; }}
    .card {{ background: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; }}
    .card-label {{ font-size: 12px; color: #6b7280; margin-bottom: 6px; }}
    .card-value {{ font-size: 20px; font-weight: 700; }}
    section {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; margin-top: 16px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; padding: 8px; text-align: left; font-size: 14px; }}
    th {{ background: #f8fafc; }}
    .num {{ text-align: right; }}
    .muted {{ color: #6b7280; font-size: 13px; }}
    .mini-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin-top: 12px; }}
    .mini-grid div {{ border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px; background: #fafafa; }}
    .mini-grid span {{ display: block; color: #6b7280; font-size: 12px; }}
    .mini-grid strong {{ font-size: 16px; }}
    .pie-wrap {{ display: flex; flex-wrap: wrap; align-items: center; gap: 16px; }}
    .legend {{ list-style: none; margin: 0; padding: 0; flex: 1; min-width: 260px; }}
    .legend li {{ display: flex; align-items: center; gap: 8px; padding: 4px 0; border-bottom: 1px solid #f1f5f9; }}
    .dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; }}
    .legend-num {{ margin-left: auto; font-weight: 600; }}
    .footer {{ margin-top: 18px; color: #6b7280; font-size: 12px; }}
  </style>
</head>
<body>
  <div class=\"container\">
    <div class=\"header\">
      <h1>Reporte financiero semanal</h1>
      <p>
        Usuario: {_safe(report.get('user_id'))} |
        Correo: {_safe(user_email or 'No disponible')} |
        Semana: {_safe(week.get('start_date'))} a {_safe(week.get('end_date'))} |
        Zona horaria: {_safe(week.get('timezone'))}
      </p>
    </div>

    <section>
      <h2>Resumen general</h2>
      <div class=\"grid\">{_render_summary_cards(summary)}</div>
    </section>

    <section>
      <h2>Resumen diario de la semana</h2>
      {daily_overview_html}
    </section>

    <section>
      <h2>Distribucion de gastos (torta)</h2>
      {expense_pie_html}
      {top_expense_html}
    </section>

    <section>
      <h2>Otras categorias</h2>
      {top_income_html}
    </section>

    <section>
      <h2>Ultimas categorias usadas</h2>
      {latest_categories_html}
    </section>

    <section>
      <h2>Detalle por cuenta</h2>
      {account_sections if account_sections else "<p class='muted'>No hay cuentas para este usuario.</p>"}
    </section>

    <div class=\"footer\">
      Generado en: {_safe(report.get('generated_at'))}
    </div>
  </div>
</body>
</html>
"""


def send_weekly_report_email(
    *,
    report: dict[str, Any],
    to_email: str,
    subject: str,
    smtp_settings: SmtpSettings | None,
) -> None:
    if smtp_settings is None:
        raise ValueError("SMTP no configurado. Define SMTP_HOST y credenciales en .env")

    if not smtp_settings.host:
        raise ValueError("SMTP_HOST es obligatorio")

    if not smtp_settings.user or not smtp_settings.password:
        raise ValueError("SMTP_USER y SMTP_PASS son obligatorios")

    sender = smtp_settings.mail_from or smtp_settings.user
    if not sender:
        raise ValueError("MAIL_FROM o SMTP_USER es obligatorio")

    html = build_weekly_report_html(report)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to_email
    message.set_content(
        "Reporte semanal generado. Visualiza este correo en un cliente compatible con HTML para ver el detalle completo."
    )
    message.add_alternative(html, subtype="html")

    context = ssl.create_default_context()
    if smtp_settings.port == 465:
        with smtplib.SMTP_SSL(
            smtp_settings.host,
            smtp_settings.port,
            timeout=smtp_settings.timeout_seconds,
            context=context,
        ) as server:
            server.login(smtp_settings.user, smtp_settings.password)
            server.send_message(message)
    else:
        with smtplib.SMTP(
            smtp_settings.host,
            smtp_settings.port,
            timeout=smtp_settings.timeout_seconds,
        ) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(smtp_settings.user, smtp_settings.password)
            server.send_message(message)
