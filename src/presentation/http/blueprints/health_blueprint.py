from __future__ import annotations

from flask import Blueprint, jsonify

from src.application.use_cases.get_health_status import GetHealthStatusUseCase


def create_health_blueprint(use_case: GetHealthStatusUseCase) -> Blueprint:
    blueprint = Blueprint("health", __name__)

    @blueprint.get("/health")
    def health() -> tuple:
        """Estado de salud del backend.
        ---
        tags:
          - Health
        responses:
          200:
            description: Servicio disponible.
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: ok
                timestamp_utc:
                  type: string
                  format: date-time
                  example: "2026-03-29T20:20:11.508221+00:00"
        """
        return jsonify(use_case.execute()), 200

    return blueprint
