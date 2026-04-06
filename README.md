# Fintu Backend Core

Backend de Fintu con arquitectura por capas (presentation, application, domain, infrastructure, core).

## Arquitectura y patrones aplicados

- App Factory: `src/bootstrap.py`
- Dependency Injection (contenedor): `src/infrastructure/container.py`
- Use Case por API: `src/application/use_cases/*`
- Puertos y adaptadores: `src/domain/ports/*` + implementaciones en `src/infrastructure/*`
- Catalogo de contratos de API: `GET /api/catalog`

## Como determinamos cada API

Cada endpoint se registra como contrato (`ApiContract`) con:

- `capability`: capacidad de negocio que resuelve
- `owner_service`: servicio responsable
- `lifecycle`: estado (`active`, `removed`)
- `description`: comportamiento esperado

## Variables de entorno

```env
APP_NAME=fintu-backend-core
APP_ENV=development
API_VERSION=v1

DATABASE_URL="postgresql://USER:PASSWORD@HOST:6543/postgres?pgbouncer=true"
DIRECT_URL="postgresql://USER:PASSWORD@HOST:5432/postgres"
DEFAULT_TIMEZONE="America/Bogota"

GEMINI_API_KEY=""
GEMINI_MODEL="gemini-3-flash"
GEMINI_MODELS="gemini-3-flash,gemini-2.5-flash,gemini-2.5-flash-lite"
GEMINI_MAX_OUTPUT_TOKENS=220

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-correo@gmail.com
SMTP_PASS="tu-app-password"
MAIL_FROM=tu-correo@gmail.com
SMTP_TIMEOUT_SECONDS=10

REPORTS_SERVICE_URL=
```

Notas:

- Se usa `DATABASE_URL` o `DIRECT_URL` para leer datos del reporte.
- Los reportes operativos diarios/semanales aplican filtros de negocio:
  - `accounts.include_in_reports = true`
  - `accounts.is_active = true`
  - `transaction_types.code = 'NORMAL'`
- Si `GEMINI_API_KEY` no existe, los consejos usan fallback local.
- La analitica usa contexto vectorizado para bajar tokens enviados a Gemini.
- Para envio de analitica por correo HTML se requiere SMTP configurado.

## Instalacion

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecutar

```bash
python app.py
```

Servicio: `http://localhost:5000`

Swagger UI: `http://localhost:5000/apidocs`

Spec JSON: `http://localhost:5000/apispec.json`

## Docker

```bash
docker compose up -d --build
docker compose ps
```

## Endpoints

- `GET /health`
  - Estado del backend.

- `GET /api/catalog`
  - Catalogo de APIs y criterios de diseño.

- `GET /api/reports/daily?user_id=<UUID>&report_day=YYYY-MM-DD&timezone=America/Bogota`
  - Reporte diario operativo en JSON.
  - Si `report_day` no se envia, usa el dia anterior en la zona horaria indicada.
  - Incluye:
    - valor actual de cuentas normales
    - deuda total estimada en tarjetas de credito (`credit_limit - cupo_disponible`)
    - ultimas 10 salidas de cuentas normales
    - categorias de gasto semanal para visualizacion tipo torta

- `GET /api/reports/daily/html?user_id=<UUID>&report_day=YYYY-MM-DD&timezone=America/Bogota`
  - Dashboard diario en HTML con enfoque ejecutivo y visual.

- `GET /api/reports/weekly?user_id=<UUID>&week_start=YYYY-MM-DD&timezone=America/Bogota`
  - Reporte semanal en JSON con consejo diario.

- `GET /api/reports/weekly/pdf?user_id=<UUID>&week_start=YYYY-MM-DD&timezone=America/Bogota`
  - Reporte semanal en PDF con graficas simples.

- `GET /api/analytics/finance/forecast?user_id=<UUID>&mode=daily|weekly|custom&history_days=90&forecast_days=7&timezone=America/Bogota`
  - Analitica predictiva con KPIs, proyeccion, `spending_focus` (categoria con mayor gasto y categorias a reducir) y `ai_advice`.
  - `mode=daily`: usa el dia inmediatamente anterior.
  - `mode=weekly`: usa los ultimos 7 dias cerrados.
  - `mode=custom`: usa `history_days` como antes.

- `POST /api/analytics/finance/forecast/email`
  - Envia reporte por correo en formato HTML (sin adjuntos).
  - Comportamiento por `mode`:
    - `daily`: envia el snapshot diario visual (cuentas normales, deuda tarjetas, ultimas 10 salidas y torta semanal embebida como imagen inline).
    - `weekly` y `custom`: envia analitica predictiva.
  - Body JSON:

```json
{
  "user_id": "11111111-1111-1111-1111-111111111111",
  "to_email": "usuario@correo.com",
  "mode": "weekly",
  "history_days": 90,
  "forecast_days": 7,
  "timezone": "America/Bogota",
  "subject": "Fintu | Reporte semanal generado 2026-03-29"
}
```

- `POST /api/reports/weekly/email`
  - `410` (removido, lo gestiona servicio externo).

## Automatizacion n8n (recomendado)

1. Flujo diario:
- Cron diario.
- HTTP Request `POST /api/analytics/finance/forecast/email` con `"mode":"daily"`.

2. Flujo semanal:
- Cron semanal.
- HTTP Request `POST /api/analytics/finance/forecast/email` con `"mode":"weekly"`.

3. Visual diario:
- HTTP Request `GET /api/reports/daily/html?user_id=<UUID>` y usarlo como vista/preview del dia.
