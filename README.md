# API de reportes semanales (Supabase + Flask)

API en Python para generar reportes semanales de cuentas y transacciones (por usuario) sobre tu base de datos de Supabase/PostgreSQL.

## 1) Requisitos

- Python 3.11+
- Acceso a la base de datos de Supabase

## 2) Configuracion

Crea un archivo `.env` en la raiz del proyecto (puedes basarte en `.env.example`):

```env
DATABASE_URL="postgresql://USER:PASSWORD@HOST:6543/postgres?pgbouncer=true"
DIRECT_URL="postgresql://USER:PASSWORD@HOST:5432/postgres"
DEFAULT_TIMEZONE="America/Bogota"

SMTP_HOST="smtp.gmail.com"
SMTP_PORT="587"
SMTP_USER="tu-correo@gmail.com"
SMTP_PASS="tu-password-o-app-password"
MAIL_FROM="tu-correo@gmail.com"
SMTP_TIMEOUT_SECONDS="10"
```

Notas:
- La API prioriza `DATABASE_URL` y si no existe usa `DIRECT_URL`.
- Se agrega `sslmode=require` automaticamente cuando no existe en la URL.
- Si usas Gmail, normalmente necesitas App Password.

## 3) Instalacion

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
```

## 4) Ejecutar

```bash
python app.py
```

Servidor en `http://localhost:5000`.

## 4.1) Ejecutar con Docker

```bash
docker compose up -d --build
docker compose ps
```

La API quedara disponible en `http://localhost:5000`.

## 5) Swagger

- UI: `http://localhost:5000/apidocs`
- JSON spec: `http://localhost:5000/apispec_1.json`

## 6) Endpoints

### Salud

`GET /health`

### Reporte semanal JSON

`GET /api/reports/weekly?user_id=<UUID>&week_start=YYYY-MM-DD&timezone=America/Bogota`

### Enviar reporte semanal por correo (HTML)

`POST /api/reports/weekly/email`

Body ejemplo:

```json
{
  "user_id": "c9d21d7e-869b-4f3c-92dc-92d8538ca54e",
  "week_start": "2026-03-16",
  "subject": "Reporte completo de mi semana"
}
```

Notas del endpoint de correo:
- Si no envias `to_email`, toma el correo del `user_id` desde `auth.users.email`.
- El timezone del reporte se toma de `DEFAULT_TIMEZONE` en `.env`.
- Si quieres, puedes enviar `to_email` para forzar un destinatario especifico.

## 7) Seguridad (importante)

Las credenciales compartidas en texto plano deben considerarse comprometidas. Te recomiendo:
- Rotar inmediatamente `SUPABASE_SERVICE_ROLE_KEY`.
- Rotar usuario/password de `DATABASE_URL` y `DIRECT_URL`.
- Rotar `SMTP_PASS`.
- No commitear `.env` al repositorio.
