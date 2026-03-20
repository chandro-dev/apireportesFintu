from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, request
from flasgger import Swagger

from src.config import get_settings
from src.email_report import send_weekly_report_email
from src.report_service import WeeklyReportService


def _build_swagger_template() -> dict:
    return {
        "swagger": "2.0",
        "info": {
            "title": "API Reportes Semanales",
            "description": "API Flask para reportes semanales de cuentas y transacciones en Supabase",
            "version": "1.1.0",
        },
        "basePath": "/",
        "schemes": ["http", "https"],
    }


def create_app() -> Flask:
    settings = get_settings()
    report_service = WeeklyReportService(settings=settings)

    app = Flask(__name__)

    app.config["SWAGGER"] = {
        "title": "API Reportes Semanales",
        "uiversion": 3,
    }
    Swagger(app, template=_build_swagger_template())

    @app.get("/health")
    def health():
        """
        Estado de la API
        ---
        tags:
          - Health
        responses:
          200:
            description: API disponible
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: ok
        """
        return jsonify({"status": "ok"})

    @app.get("/api/reports/weekly")
    def weekly_report():
        """
        Reporte semanal por usuario
        ---
        tags:
          - Reports
        parameters:
          - in: query
            name: user_id
            type: string
            required: true
            description: UUID del usuario (profiles.id)
          - in: query
            name: week_start
            type: string
            required: false
            description: Fecha de inicio en formato YYYY-MM-DD
          - in: query
            name: timezone
            type: string
            required: false
            description: Timezone IANA, por ejemplo America/Bogota
        responses:
          200:
            description: Reporte semanal generado
          400:
            description: Error de validacion de parametros
          500:
            description: Error interno
        """
        user_id = request.args.get("user_id")
        if not user_id:
            return jsonify({"error": "query param 'user_id' es obligatorio"}), 400

        week_start = request.args.get("week_start")
        timezone_name = request.args.get("timezone")

        try:
            result = report_service.build_weekly_report(
                user_id=user_id,
                week_start_str=week_start,
                timezone_name=timezone_name,
            )
            return jsonify(result)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception:
            app.logger.exception("Error generando reporte semanal")
            return jsonify({"error": "Error interno generando el reporte"}), 500

    @app.post("/api/reports/weekly/email")
    def weekly_report_email():
        """
        Enviar reporte semanal por correo HTML
        ---
        tags:
          - Reports
        consumes:
          - application/json
        parameters:
          - in: body
            name: body
            required: true
            schema:
              type: object
              required:
                - user_id
              properties:
                user_id:
                  type: string
                  description: UUID del usuario (profiles.id)
                to_email:
                  type: string
                  description: Correo destino opcional (si no viene, se usa el correo del user_id)
                week_start:
                  type: string
                  description: Fecha inicio de semana YYYY-MM-DD (opcional)
                subject:
                  type: string
                  description: Asunto personalizado del correo (opcional)
        responses:
          200:
            description: Correo enviado
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
          400:
            description: Error de validacion
          500:
            description: Error interno
        """
        body = request.get_json(silent=True) or {}

        user_id = body.get("user_id")
        to_email = body.get("to_email")
        week_start = body.get("week_start")
        subject = body.get("subject")
        timezone_name = settings.default_timezone

        if not user_id:
            return jsonify({"error": "Campo 'user_id' es obligatorio"}), 400

        try:
            report = report_service.build_weekly_report(
                user_id=user_id,
                week_start_str=week_start,
                timezone_name=timezone_name,
            )
            recipient_email = to_email or report.get("user_email")
            if not recipient_email:
                return (
                    jsonify(
                        {
                            "error": (
                                "No se encontro correo para el user_id. "
                                "Puedes enviarlo manualmente en 'to_email'."
                            )
                        }
                    ),
                    400,
                )

            report_date = datetime.now(ZoneInfo(timezone_name)).strftime("%d/%m/%Y")
            email_subject = subject or (
                "Fintu - Reporte generado el "
                f"{report_date} | Semana {report['week']['start_date']} a {report['week']['end_date']}"
            )
            send_weekly_report_email(
                report=report,
                to_email=recipient_email,
                subject=email_subject,
                smtp_settings=settings.smtp,
            )
            return jsonify(
                {
                    "status": "sent",
                    "to_email": recipient_email,
                    "subject": email_subject,
                    "timezone": timezone_name,
                    "sent_at": datetime.utcnow().isoformat() + "Z",
                }
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception:
            app.logger.exception("Error enviando reporte semanal por correo")
            return jsonify({"error": "Error interno enviando el correo"}), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
