from __future__ import annotations

from flask import Blueprint, current_app, jsonify

from src.application.use_cases.list_api_catalog import ListApiCatalogUseCase


def create_catalog_blueprint(use_case: ListApiCatalogUseCase) -> Blueprint:
    blueprint = Blueprint("catalog", __name__)

    @blueprint.get("/api/catalog")
    def api_catalog() -> tuple:
        """Catalogo de contratos API del backend.
        ---
        tags:
          - Catalog
        responses:
          200:
            description: Informacion de arquitectura y contratos activos/removidos.
            schema:
              type: object
              properties:
                app_name:
                  type: string
                  example: fintu-backend-core
                environment:
                  type: string
                  example: development
                api_version:
                  type: string
                  example: v1
                api_contracts:
                  type: array
                  items:
                    type: object
                    properties:
                      method:
                        type: string
                        example: GET
                      path:
                        type: string
                        example: /api/reports/weekly
                      lifecycle:
                        type: string
                        example: active
                      capability:
                        type: string
                        example: weekly_financial_report
                      owner_service:
                        type: string
                        example: fintu-backend-core
                      description:
                        type: string
                        example: Entrega reporte semanal agregado del usuario.
                api_design_criteria:
                  type: array
                  items:
                    type: string
        """
        settings = current_app.config["APP_SETTINGS"]
        return (
            jsonify(
                {
                    "app_name": settings.app_name,
                    "environment": settings.app_env,
                    "api_version": settings.api_version,
                    "api_contracts": use_case.execute(),
                    "api_design_criteria": [
                        "capability_first: cada endpoint nace desde una capacidad de negocio",
                        "single_responsibility: cada API expone una responsabilidad concreta",
                        "lifecycle_explicit: active/removed para gobernanza de cambios",
                        "owner_service: cada API define su servicio responsable",
                    ],
                }
            ),
            200,
        )

    return blueprint
