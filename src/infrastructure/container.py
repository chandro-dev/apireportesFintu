from __future__ import annotations

from dataclasses import dataclass

from src.application.services.api_catalog_registry import ApiCatalogRegistry
from src.application.services.finance_forecast_email_renderer import FinanceForecastEmailRenderer
from src.application.services.financial_forecast_model import FinancialForecastModel
from src.application.use_cases.generate_weekly_report_pdf import GenerateWeeklyReportPdfUseCase
from src.application.use_cases.get_finance_forecast import GetFinanceForecastUseCase
from src.application.use_cases.get_health_status import GetHealthStatusUseCase
from src.application.use_cases.get_report_policy import GetReportPolicyUseCase
from src.application.use_cases.get_weekly_report import GetWeeklyReportUseCase
from src.application.use_cases.list_api_catalog import ListApiCatalogUseCase
from src.application.use_cases.send_finance_forecast_email import SendFinanceForecastEmailUseCase
from src.core.settings import Settings
from src.domain.api_contract import ApiContract
from src.infrastructure.ai.gemini_advice_provider import GeminiAdviceProvider
from src.infrastructure.ai.gemini_finance_advice_provider import GeminiFinanceAdviceProvider
from src.infrastructure.email.smtp_html_email_sender import SmtpHtmlEmailSender
from src.infrastructure.postgres.connection_factory import PostgresConnectionFactory
from src.infrastructure.postgres.supabase_report_repository import SupabaseReportRepository
from src.infrastructure.reporting.matplotlib_pdf_renderer import MatplotlibPdfRenderer


@dataclass(frozen=True)
class AppContainer:
    health_status_use_case: GetHealthStatusUseCase
    list_api_catalog_use_case: ListApiCatalogUseCase
    weekly_report_use_case: GetWeeklyReportUseCase
    weekly_report_pdf_use_case: GenerateWeeklyReportPdfUseCase
    report_email_policy_use_case: GetReportPolicyUseCase
    finance_forecast_use_case: GetFinanceForecastUseCase
    send_finance_forecast_email_use_case: SendFinanceForecastEmailUseCase

    @staticmethod
    def build(settings: Settings) -> "AppContainer":
        connection_uri = settings.database_url or settings.direct_url
        if not connection_uri:
            raise ValueError("DATABASE_URL o DIRECT_URL es obligatorio para reportes")

        connection_factory = PostgresConnectionFactory(connection_uri=connection_uri)
        report_repository = SupabaseReportRepository(connection_factory=connection_factory)
        weekly_advice_provider = GeminiAdviceProvider(
            api_key=settings.gemini_api_key,
            models=settings.gemini_models,
            max_output_tokens=settings.gemini_max_output_tokens,
        )
        finance_advice_provider = GeminiFinanceAdviceProvider(
            api_key=settings.gemini_api_key,
            models=settings.gemini_models,
            max_output_tokens=settings.gemini_max_output_tokens,
        )

        pdf_renderer = MatplotlibPdfRenderer()
        forecast_model = FinancialForecastModel()
        forecast_email_renderer = FinanceForecastEmailRenderer()
        email_sender = SmtpHtmlEmailSender(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            timeout_seconds=settings.smtp_timeout_seconds,
        )

        weekly_report_use_case = GetWeeklyReportUseCase(
            settings=settings,
            repository=report_repository,
            advice_provider=weekly_advice_provider,
        )
        weekly_report_pdf_use_case = GenerateWeeklyReportPdfUseCase(
            get_weekly_report_use_case=weekly_report_use_case,
            pdf_renderer=pdf_renderer,
        )
        report_email_policy_use_case = GetReportPolicyUseCase(settings=settings)
        finance_forecast_use_case = GetFinanceForecastUseCase(
            settings=settings,
            repository=report_repository,
            forecast_model=forecast_model,
            advice_provider=finance_advice_provider,
        )
        send_finance_forecast_email_use_case = SendFinanceForecastEmailUseCase(
            settings=settings,
            get_finance_forecast_use_case=finance_forecast_use_case,
            renderer=forecast_email_renderer,
            email_sender=email_sender,
        )

        contracts = [
            ApiContract(
                method="GET",
                path="/health",
                lifecycle="active",
                capability="platform_health",
                owner_service="fintu-backend-core",
                description="Verifica disponibilidad del backend.",
            ),
            ApiContract(
                method="GET",
                path="/api/catalog",
                lifecycle="active",
                capability="api_discovery",
                owner_service="fintu-backend-core",
                description="Entrega el catalogo y estado de APIs del backend.",
            ),
            ApiContract(
                method="GET",
                path="/api/reports/weekly",
                lifecycle="active",
                capability="weekly_reports",
                owner_service="fintu-backend-core",
                description="Retorna reporte semanal en JSON con consejo diario.",
            ),
            ApiContract(
                method="GET",
                path="/api/reports/weekly/pdf",
                lifecycle="active",
                capability="weekly_reports_pdf",
                owner_service="fintu-backend-core",
                description="Genera reporte semanal en PDF con graficas simples.",
            ),
            ApiContract(
                method="POST",
                path="/api/reports/weekly/email",
                lifecycle="removed",
                capability="weekly_reports_email",
                owner_service="reports-service",
                description="Removido. Debe consumirse en el servicio externo de reportes.",
            ),
            ApiContract(
                method="GET",
                path="/api/analytics/finance/forecast",
                lifecycle="active",
                capability="financial_predictive_analytics",
                owner_service="fintu-backend-core",
                description=(
                    "Analitica predictiva (daily/weekly/custom) con KPIs, proyeccion, foco de gasto y consejo IA."
                ),
            ),
            ApiContract(
                method="POST",
                path="/api/analytics/finance/forecast/email",
                lifecycle="active",
                capability="financial_predictive_analytics_email_html",
                owner_service="fintu-backend-core",
                description="Envia por correo el reporte predictivo en formato HTML.",
            ),
        ]
        registry = ApiCatalogRegistry(contracts=contracts)

        return AppContainer(
            health_status_use_case=GetHealthStatusUseCase(),
            list_api_catalog_use_case=ListApiCatalogUseCase(registry=registry),
            weekly_report_use_case=weekly_report_use_case,
            weekly_report_pdf_use_case=weekly_report_pdf_use_case,
            report_email_policy_use_case=report_email_policy_use_case,
            finance_forecast_use_case=finance_forecast_use_case,
            send_finance_forecast_email_use_case=send_finance_forecast_email_use_case,
        )

