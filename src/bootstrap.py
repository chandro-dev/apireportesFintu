from flask import Flask, redirect
from flasgger import Swagger

from src.core.settings import load_settings
from src.infrastructure.container import AppContainer
from src.presentation.http.blueprints.analytics_blueprint import create_analytics_blueprint
from src.presentation.http.blueprints.catalog_blueprint import create_catalog_blueprint
from src.presentation.http.blueprints.health_blueprint import create_health_blueprint
from src.presentation.http.blueprints.reports_blueprint import create_reports_blueprint
from src.presentation.http.error_handlers import register_error_handlers


def _build_swagger_template(settings) -> dict:
    return {
        "swagger": "2.0",
        "info": {
            "title": f"{settings.app_name} API",
            "description": "Documentacion para pruebas de endpoints del backend de Fintu.",
            "version": settings.api_version,
        },
        "basePath": "/",
        "schemes": ["http", "https"],
        "tags": [
            {"name": "Health", "description": "Estado de salud del servicio"},
            {"name": "Catalog", "description": "Catalogo de contratos de API"},
            {"name": "Reports", "description": "Reportes diarios y semanales (JSON, HTML y PDF)"},
            {"name": "Analytics", "description": "Analitica y proyecciones financieras"},
        ],
    }


def _build_swagger_config() -> dict:
    return {
        "headers": [],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/apispec.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "specs_route": "/apidocs/",
        "uiversion": 3,
    }


def create_app() -> Flask:
    settings = load_settings()
    container = AppContainer.build(settings=settings)

    app = Flask(__name__)
    app.config["APP_SETTINGS"] = settings
    app.config["SWAGGER"] = {
        "title": f"{settings.app_name} API",
    }
    Swagger(
        app,
        template=_build_swagger_template(settings),
        config=_build_swagger_config(),
    )

    @app.get("/")
    def root() -> tuple:
        return redirect("/apidocs/", code=302)

    @app.get("/apidocs")
    def apidocs_redirect() -> tuple:
        return redirect("/apidocs/", code=302)

    app.register_blueprint(create_health_blueprint(container.health_status_use_case))
    app.register_blueprint(create_catalog_blueprint(container.list_api_catalog_use_case))
    app.register_blueprint(
        create_analytics_blueprint(
            container.finance_forecast_use_case,
            container.send_finance_forecast_email_use_case,
        )
    )
    app.register_blueprint(
        create_reports_blueprint(
            container.daily_report_use_case,
            container.daily_report_html_renderer,
            container.weekly_report_use_case,
            container.weekly_report_pdf_use_case,
            container.report_email_policy_use_case,
        )
    )

    register_error_handlers(app)
    return app
