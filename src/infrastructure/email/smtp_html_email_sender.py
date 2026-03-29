from __future__ import annotations

import smtplib
from email.mime.text import MIMEText


class SmtpHtmlEmailSender:
    def __init__(
        self,
        *,
        host: str | None,
        port: int,
        username: str | None,
        password: str | None,
        timeout_seconds: int,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._timeout_seconds = timeout_seconds

    def send_html_email(
        self,
        *,
        to_email: str,
        subject: str,
        html_body: str,
        from_email: str,
    ) -> None:
        if not self._host:
            raise ValueError("SMTP_HOST es obligatorio para enviar correos")
        if not self._username:
            raise ValueError("SMTP_USER es obligatorio para enviar correos")
        if not self._password:
            raise ValueError("SMTP_PASS/SMTP_PASSWORD es obligatorio para enviar correos")

        message = MIMEText(html_body, "html", "utf-8")
        message["Subject"] = subject
        message["From"] = from_email
        message["To"] = to_email

        with smtplib.SMTP(self._host, self._port, timeout=self._timeout_seconds) as client:
            client.ehlo()
            client.starttls()
            client.ehlo()
            client.login(self._username, self._password)
            client.sendmail(from_email, [to_email], message.as_string())
