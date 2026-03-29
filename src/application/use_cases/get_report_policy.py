from __future__ import annotations

from src.core.settings import Settings


class GetReportPolicyUseCase:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def execute(self) -> tuple[dict[str, str], int]:
        payload = {
            "error": "Endpoint deshabilitado",
            "message": (
                "El envio de reportes por correo fue removido de este backend. "
                "Ahora lo gestiona un servicio externo."
            ),
        }
        if self._settings.reports_service_url:
            payload["reports_service_url"] = self._settings.reports_service_url
        return payload, 410
