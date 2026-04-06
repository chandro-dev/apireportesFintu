from __future__ import annotations

from smtplib import SMTPException

from flask import Blueprint, current_app, jsonify, request
from psycopg import OperationalError

from src.application.use_cases.get_finance_forecast import GetFinanceForecastUseCase
from src.application.use_cases.send_finance_forecast_email import SendFinanceForecastEmailUseCase


def create_analytics_blueprint(
    forecast_use_case: GetFinanceForecastUseCase,
    send_email_use_case: SendFinanceForecastEmailUseCase,
) -> Blueprint:
    blueprint = Blueprint("analytics", __name__)

    @blueprint.get("/api/analytics/finance/forecast")
    def finance_forecast() -> tuple:
        """Analitica predictiva de finanzas personales (modo diario, semanal o personalizado).
        ---
        tags:
          - Analytics
        parameters:
          - in: query
            name: user_id
            type: string
            required: true
            description: UUID del usuario.
          - in: query
            name: mode
            type: string
            required: false
            description: Modo de analisis (`daily`, `weekly`, `custom`).
            enum: [daily, weekly, custom]
            example: daily
          - in: query
            name: history_days
            type: integer
            required: false
            description: Dias historicos a analizar (14-365). Solo aplica en mode=custom. Default 90.
            example: 90
          - in: query
            name: forecast_days
            type: integer
            required: false
            description: Dias a proyectar (1-30). Default 1 para daily, 7 para weekly/custom.
            example: 7
          - in: query
            name: timezone
            type: string
            required: false
            description: Zona horaria IANA. Default DEFAULT_TIMEZONE.
            example: America/Bogota
        responses:
          200:
            description: Forecast generado correctamente.
          400:
            description: Parametros invalidos.
            schema:
              type: object
              properties:
                error:
                  type: string
          503:
            description: Error de conectividad con base de datos.
            schema:
              type: object
              properties:
                error:
                  type: string
          500:
            description: Error interno.
            schema:
              type: object
              properties:
                error:
                  type: string
        """
        user_id = request.args.get("user_id")
        if not user_id:
            return jsonify({"error": "query param 'user_id' es obligatorio"}), 400

        try:
            history_days = _parse_optional_int_query("history_days")
            forecast_days = _parse_optional_int_query("forecast_days")
            timezone_name = request.args.get("timezone")
            analysis_mode = request.args.get("mode")

            report = forecast_use_case.execute(
                user_id=user_id,
                history_days=history_days,
                forecast_days=forecast_days,
                timezone_name=timezone_name,
                analysis_mode=analysis_mode,
            )
            return jsonify(report.to_dict()), 200
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except OperationalError:
            current_app.logger.exception("Error de conexion a base de datos en analitica predictiva")
            return jsonify({"error": "No se pudo conectar a la base de datos"}), 503
        except Exception:
            current_app.logger.exception("Error generando analitica predictiva")
            return jsonify({"error": "Error interno generando analitica predictiva"}), 500

    @blueprint.post("/api/analytics/finance/forecast/email")
    def finance_forecast_email() -> tuple:
        """Envia analitica por correo en HTML (sin adjuntos).
        ---
        tags:
          - Analytics
        consumes:
          - application/json
        parameters:
          - in: body
            name: payload
            required: true
            schema:
              type: object
              required:
                - user_id
                - to_email
              properties:
                user_id:
                  type: string
                  example: 11111111-1111-1111-1111-111111111111
                to_email:
                  type: string
                  example: usuario@correo.com
                mode:
                  type: string
                  enum: [daily, weekly, custom]
                  description: |
                    daily: envia snapshot diario visual.
                    weekly/custom: envia analitica predictiva.
                  example: daily
                history_days:
                  type: integer
                  example: 90
                forecast_days:
                  type: integer
                  example: 7
                timezone:
                  type: string
                  example: America/Bogota
                subject:
                  type: string
                  example: Fintu | Reporte semanal generado 2026-03-29
        responses:
          200:
            description: Correo enviado en formato HTML.
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: sent
                to_email:
                  type: string
                subject:
                  type: string
                format:
                  type: string
                  example: html
                generated_at_utc:
                  type: string
          400:
            description: Error de validacion.
          502:
            description: Error SMTP al enviar correo.
          503:
            description: Error de conectividad con base de datos.
          500:
            description: Error interno.
        """
        payload = request.get_json(silent=True) or {}

        user_id = (payload.get("user_id") or "").strip()
        if not user_id:
            return jsonify({"error": "user_id es obligatorio"}), 400

        to_email = (payload.get("to_email") or "").strip()
        if not to_email:
            return jsonify({"error": "to_email es obligatorio"}), 400

        try:
            response = send_email_use_case.execute(
                user_id=user_id,
                to_email=to_email,
                history_days=_parse_optional_int_payload(payload, "history_days"),
                forecast_days=_parse_optional_int_payload(payload, "forecast_days"),
                timezone_name=(payload.get("timezone") or None),
                analysis_mode=(payload.get("mode") or None),
                subject=(payload.get("subject") or None),
            )
            return jsonify(response), 200
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except OperationalError:
            current_app.logger.exception("Error de conexion a base de datos enviando email analitico")
            return jsonify({"error": "No se pudo conectar a la base de datos"}), 503
        except SMTPException:
            current_app.logger.exception("Error SMTP enviando email analitico")
            return jsonify({"error": "No se pudo enviar el correo por SMTP"}), 502
        except Exception:
            current_app.logger.exception("Error enviando analitica predictiva por correo")
            return jsonify({"error": "Error interno enviando correo"}), 500

    return blueprint


def _parse_optional_int_query(name: str) -> int | None:
    value = request.args.get(name)
    if value is None or value.strip() == "":
        return None

    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} debe ser entero") from exc


def _parse_optional_int_payload(payload: dict, name: str) -> int | None:
    value = payload.get(name)
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value

    try:
        return int(str(value))
    except ValueError as exc:
        raise ValueError(f"{name} debe ser entero") from exc
