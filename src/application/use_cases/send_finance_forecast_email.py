from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from src.application.services.daily_report_html_renderer import DailyReportHtmlRenderer
from src.application.services.finance_forecast_email_renderer import FinanceForecastEmailRenderer
from src.application.use_cases.get_daily_report import GetDailyReportUseCase
from src.application.use_cases.get_finance_forecast import GetFinanceForecastUseCase
from src.core.settings import Settings
from src.domain.ports.html_email_sender import HtmlEmailSender


class SendFinanceForecastEmailUseCase:
    def __init__(
        self,
        *,
        settings: Settings,
        get_finance_forecast_use_case: GetFinanceForecastUseCase,
        get_daily_report_use_case: GetDailyReportUseCase,
        daily_renderer: DailyReportHtmlRenderer,
        renderer: FinanceForecastEmailRenderer,
        email_sender: HtmlEmailSender,
    ) -> None:
        self._settings = settings
        self._get_finance_forecast_use_case = get_finance_forecast_use_case
        self._get_daily_report_use_case = get_daily_report_use_case
        self._daily_renderer = daily_renderer
        self._renderer = renderer
        self._email_sender = email_sender

    def execute(
        self,
        *,
        user_id: str,
        to_email: str,
        history_days: int | None,
        forecast_days: int | None,
        timezone_name: str | None,
        analysis_mode: str | None,
        subject: str | None,
    ) -> dict[str, str]:
        recipient = self._validate_email(to_email)
        tz_name = timezone_name or self._settings.default_timezone
        mode = self._normalize_analysis_mode(analysis_mode)

        report_template = "forecast"
        inline_images: dict[str, bytes] | None = None
        if mode == "daily":
            daily_report = self._get_daily_report_use_case.execute(
                user_id=user_id,
                report_day_str=None,
                timezone_name=tz_name,
            )
            weekly_pie_cid = "weekly_expense_pie"
            html_body = self._daily_renderer.render(
                report=daily_report,
                weekly_pie_image_src=f"cid:{weekly_pie_cid}",
            )
            inline_images = {
                weekly_pie_cid: self._daily_renderer.build_weekly_pie_png(report=daily_report)
            }
            report_template = "daily_snapshot"
        else:
            report = self._get_finance_forecast_use_case.execute(
                user_id=user_id,
                history_days=history_days,
                forecast_days=forecast_days,
                timezone_name=tz_name,
                analysis_mode=mode,
            )
            html_body = self._renderer.render(report=report)

        final_subject = self._resolve_subject(
            subject=subject,
            timezone_name=tz_name,
            analysis_mode=mode,
        )

        from_email = self._settings.mail_from or self._settings.smtp_user
        if not from_email:
            raise ValueError("MAIL_FROM o SMTP_USER es obligatorio para enviar correos")

        self._email_sender.send_html_email(
            to_email=recipient,
            subject=final_subject,
            html_body=html_body,
            from_email=from_email,
            inline_images=inline_images,
        )

        return {
            "status": "sent",
            "to_email": recipient,
            "subject": final_subject,
            "format": "html",
            "analysis_mode": mode,
            "report_template": report_template,
            "generated_at_utc": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def _validate_email(value: str) -> str:
        candidate = (value or "").strip()
        if not candidate:
            raise ValueError("to_email es obligatorio")
        if "@" not in candidate or "." not in candidate.split("@")[-1]:
            raise ValueError("to_email no tiene formato valido")
        return candidate

    @staticmethod
    def _normalize_analysis_mode(value: str | None) -> str:
        if value is None or value.strip() == "":
            return "custom"

        mode = value.strip().lower()
        if mode not in {"daily", "weekly", "custom"}:
            raise ValueError("analysis_mode debe ser 'daily', 'weekly' o 'custom'")
        return mode

    def _resolve_subject(
        self,
        *,
        subject: str | None,
        timezone_name: str,
        analysis_mode: str,
    ) -> str:
        if subject and subject.strip():
            return subject.strip()

        try:
            tz = ZoneInfo(timezone_name)
        except Exception:
            tz = ZoneInfo(self._settings.default_timezone)

        now_local = datetime.now(tz=tz)

        if analysis_mode == "daily":
            prefix = "Reporte diario"
        elif analysis_mode == "weekly":
            prefix = "Reporte semanal"
        else:
            prefix = "Reporte financiero"

        return f"Fintu | {prefix} generado {now_local.date().isoformat()}"
