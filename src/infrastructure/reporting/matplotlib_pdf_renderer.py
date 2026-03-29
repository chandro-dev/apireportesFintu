from __future__ import annotations

from io import BytesIO

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from src.domain.ports.pdf_renderer import PdfRenderer
from src.domain.report_entities import WeeklyReport


class MatplotlibPdfRenderer(PdfRenderer):
    def render_weekly_report(self, report: WeeklyReport) -> bytes:
        buffer = BytesIO()
        with PdfPages(buffer) as pdf:
            pdf.savefig(self._build_summary_page(report), bbox_inches="tight")
            pdf.savefig(self._build_charts_page(report), bbox_inches="tight")

        buffer.seek(0)
        return buffer.read()

    def _build_summary_page(self, report: WeeklyReport):
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.suptitle("Fintu - Reporte Semanal", fontsize=18, fontweight="bold")

        ax_text = fig.add_axes([0.08, 0.67, 0.84, 0.24])
        ax_text.axis("off")
        summary_lines = [
            f"Usuario: {report.user_id}",
            f"Semana: {report.week_start} a {report.week_end}",
            f"Zona horaria: {report.timezone}",
            "",
            f"Ingresos: ${report.summary.income:,.2f}",
            f"Gastos: ${report.summary.expense:,.2f}",
            f"Neto: ${report.summary.net:,.2f}",
            f"Transacciones: {report.summary.transactions_count}",
        ]
        ax_text.text(0, 1, "\n".join(summary_lines), va="top", fontsize=11)

        ax_advice = fig.add_axes([0.08, 0.08, 0.84, 0.5])
        ax_advice.axis("off")
        ax_advice.text(0, 1, "Consejo diario", fontsize=13, fontweight="bold", va="top")
        ax_advice.text(0, 0.92, report.advice, fontsize=11, va="top", wrap=True)

        return fig

    def _build_charts_page(self, report: WeeklyReport):
        fig, (ax_bar, ax_pie) = plt.subplots(2, 1, figsize=(8.27, 11.69))
        fig.suptitle("Graficas del Reporte", fontsize=16, fontweight="bold")

        days = [row.date[-5:] for row in report.daily_overview]
        incomes = [row.income for row in report.daily_overview]
        expenses = [row.expense for row in report.daily_overview]

        if days:
            x = range(len(days))
            ax_bar.bar(x, incomes, label="Ingresos", color="#16a34a")
            ax_bar.bar(x, expenses, label="Gastos", color="#dc2626", alpha=0.8)
            ax_bar.set_xticks(list(x))
            ax_bar.set_xticklabels(days)
        ax_bar.set_title("Ingresos vs Gastos por dia")
        ax_bar.set_ylabel("Monto")
        ax_bar.legend()
        ax_bar.grid(axis="y", alpha=0.2)

        cat_labels = [c.category_name for c in report.expense_categories]
        cat_amounts = [c.amount for c in report.expense_categories]
        if cat_amounts and sum(cat_amounts) > 0:
            ax_pie.pie(cat_amounts, labels=cat_labels, autopct="%1.1f%%", startangle=120)
            ax_pie.axis("equal")
        else:
            ax_pie.text(0.5, 0.5, "Sin categorias de gasto en la semana", ha="center", va="center")
            ax_pie.axis("off")
        ax_pie.set_title("Distribucion de gastos por categoria")

        return fig
