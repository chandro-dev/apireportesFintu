from __future__ import annotations

from typing import Protocol

from src.domain.report_entities import WeeklyReport


class PdfRenderer(Protocol):
    def render_weekly_report(self, report: WeeklyReport) -> bytes:
        ...

