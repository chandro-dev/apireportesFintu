from __future__ import annotations

from io import BytesIO

from flask import Blueprint, current_app, jsonify, request, send_file

from src.application.use_cases.generate_weekly_report_pdf import GenerateWeeklyReportPdfUseCase
from src.application.use_cases.get_report_policy import GetReportPolicyUseCase
from src.application.use_cases.get_weekly_report import GetWeeklyReportUseCase


def create_reports_blueprint(
    weekly_report_use_case: GetWeeklyReportUseCase,
    weekly_report_pdf_use_case: GenerateWeeklyReportPdfUseCase,
    report_email_policy_use_case: GetReportPolicyUseCase,
) -> Blueprint:
    blueprint = Blueprint("reports", __name__)

    @blueprint.get("/api/reports/weekly")
    def weekly_report() -> tuple:
        """Genera el reporte semanal en JSON.
        ---
        tags:
          - Reports
        parameters:
          - in: query
            name: user_id
            type: string
            required: true
            description: UUID del usuario.
            example: 11111111-1111-1111-1111-111111111111
          - in: query
            name: week_start
            type: string
            required: false
            description: Fecha inicio semana (YYYY-MM-DD). Si no se envia, usa la semana actual.
            example: "2026-03-23"
          - in: query
            name: timezone
            type: string
            required: false
            description: Zona horaria IANA (ej. America/Bogota).
            example: America/Bogota
        responses:
          200:
            description: Reporte semanal generado correctamente.
            schema:
              type: object
              properties:
                user_id:
                  type: string
                week:
                  type: object
                  properties:
                    start_date:
                      type: string
                      example: "2026-03-23"
                    end_date:
                      type: string
                      example: "2026-03-29"
                    timezone:
                      type: string
                      example: America/Bogota
                summary:
                  type: object
                  properties:
                    income:
                      type: number
                      format: float
                    expense:
                      type: number
                      format: float
                    net:
                      type: number
                      format: float
                    transactions_count:
                      type: integer
                daily_overview:
                  type: array
                  items:
                    type: object
                    properties:
                      date:
                        type: string
                      income:
                        type: number
                        format: float
                      expense:
                        type: number
                        format: float
                      net:
                        type: number
                        format: float
                      transactions_count:
                        type: integer
                expense_categories:
                  type: array
                  items:
                    type: object
                    properties:
                      category_name:
                        type: string
                      amount:
                        type: number
                        format: float
                      transactions_count:
                        type: integer
                daily_advice:
                  type: string
          400:
            description: Parametros invalidos.
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

        week_start = request.args.get("week_start")
        timezone_name = request.args.get("timezone")

        try:
            report = weekly_report_use_case.execute(
                user_id=user_id,
                week_start_str=week_start,
                timezone_name=timezone_name,
            )
            return jsonify(report.to_dict()), 200
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception:
            current_app.logger.exception("Error generando reporte semanal")
            return jsonify({"error": "Error interno generando el reporte"}), 500

    @blueprint.get("/api/reports/weekly/pdf")
    def weekly_report_pdf():
        """Genera y descarga el reporte semanal en PDF.
        ---
        tags:
          - Reports
        produces:
          - application/pdf
        parameters:
          - in: query
            name: user_id
            type: string
            required: true
            description: UUID del usuario.
            example: 11111111-1111-1111-1111-111111111111
          - in: query
            name: week_start
            type: string
            required: false
            description: Fecha inicio semana (YYYY-MM-DD).
            example: "2026-03-23"
          - in: query
            name: timezone
            type: string
            required: false
            description: Zona horaria IANA.
            example: America/Bogota
        responses:
          200:
            description: Archivo PDF del reporte semanal.
            schema:
              type: string
              format: binary
          400:
            description: Parametros invalidos.
            schema:
              type: object
              properties:
                error:
                  type: string
          500:
            description: Error interno al generar PDF.
            schema:
              type: object
              properties:
                error:
                  type: string
        """
        user_id = request.args.get("user_id")
        if not user_id:
            return jsonify({"error": "query param 'user_id' es obligatorio"}), 400

        week_start = request.args.get("week_start")
        timezone_name = request.args.get("timezone")

        try:
            pdf_bytes, filename = weekly_report_pdf_use_case.execute(
                user_id=user_id,
                week_start_str=week_start,
                timezone_name=timezone_name,
            )
            return send_file(
                BytesIO(pdf_bytes),
                mimetype="application/pdf",
                as_attachment=True,
                download_name=filename,
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception:
            current_app.logger.exception("Error generando PDF semanal")
            return jsonify({"error": "Error interno generando PDF"}), 500

    @blueprint.post("/api/reports/weekly/email")
    def weekly_report_email_removed() -> tuple:
        """Endpoint de email removido del backend actual.
        ---
        tags:
          - Reports
        responses:
          410:
            description: Endpoint removido y delegado a servicio externo.
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: Endpoint deshabilitado
                message:
                  type: string
                  example: El envio de reportes por correo fue removido de este backend.
                reports_service_url:
                  type: string
                  example: https://reports.fintu.app
        """
        payload, status_code = report_email_policy_use_case.execute()
        return jsonify(payload), status_code

    return blueprint
