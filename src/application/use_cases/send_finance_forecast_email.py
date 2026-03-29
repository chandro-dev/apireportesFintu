from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from src.application.services.finance_forecast_email_renderer import FinanceForecastEmailRenderer
from src.application.use_cases.get_finance_forecast import GetFinanceForecastUseCase
from src.core.settings import Settings
from src.domain.ports.html_email_sender import HtmlEmailSender


class SendFinanceForecastEmailUseCase:
    def __init__(
        self,
        *,
        settings: Settings,
        get_finance_forecast_use_case: GetFinanceForecastUseCase,
        renderer: FinanceForecastEmailRenderer,
        email_sender: HtmlEmailSender,
    ) -> None:
        self._settings = settings
        self._get_finance_forecast_use_case = get_finance_forecast_use_case
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

        report = self._get_finance_forecast_use_case.execute(
            user_id=user_id,
            history_days=history_days,
            forecast_days=forecast_days,
            timezone_name=tz_name,
            analysis_mode=analysis_mode,
        )

        final_subject = self._resolve_subject(
            subject=subject,
            timezone_name=tz_name,
            analysis_mode=report.analysis_mode,
        )
        html_body = self._renderer.render(report=report)

        from_email = self._settings.mail_from or self._settings.smtp_user
        if not from_email:
            raise ValueError("MAIL_FROM o SMTP_USER es obligatorio para enviar correos")

        self._email_sender.send_html_email(
            to_email=recipient,
            subject=final_subject,
            html_body=html_body,
            from_email=from_email,
        )

        return {
            "status": "sent",
            "to_email": recipient,
            "subject": final_subject,
            "format": "html",
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
