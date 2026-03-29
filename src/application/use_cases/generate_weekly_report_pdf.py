from __future__ import annotations

from src.domain.ports.pdf_renderer import PdfRenderer

from .get_weekly_report import GetWeeklyReportUseCase


class GenerateWeeklyReportPdfUseCase:
    def __init__(
        self,
        *,
        get_weekly_report_use_case: GetWeeklyReportUseCase,
        pdf_renderer: PdfRenderer,
    ) -> None:
        self._get_weekly_report_use_case = get_weekly_report_use_case
        self._pdf_renderer = pdf_renderer

    def execute(
        self,
        *,
        user_id: str,
        week_start_str: str | None,
        timezone_name: str | None,
    ) -> tuple[bytes, str]:
        report = self._get_weekly_report_use_case.execute(
            user_id=user_id,
            week_start_str=week_start_str,
            timezone_name=timezone_name,
        )
        pdf_bytes = self._pdf_renderer.render_weekly_report(report)
        filename = f"fintu-weekly-report-{report.week_start}-to-{report.week_end}.pdf"
        return pdf_bytes, filename
