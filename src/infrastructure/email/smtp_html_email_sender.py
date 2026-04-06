from __future__ import annotations

import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
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
        inline_images: dict[str, bytes] | None = None,
    ) -> None:
        if not self._host:
            raise ValueError("SMTP_HOST es obligatorio para enviar correos")
        if not self._username:
            raise ValueError("SMTP_USER es obligatorio para enviar correos")
        if not self._password:
            raise ValueError("SMTP_PASS/SMTP_PASSWORD es obligatorio para enviar correos")

        if inline_images:
            message = MIMEMultipart("related")
            message["Subject"] = subject
            message["From"] = from_email
            message["To"] = to_email

            body_container = MIMEMultipart("alternative")
            body_container.attach(MIMEText(html_body, "html", "utf-8"))
            message.attach(body_container)

            for cid, image_bytes in inline_images.items():
                image_part = MIMEImage(image_bytes, _subtype="png")
                image_part.add_header("Content-ID", f"<{cid}>")
                image_part.add_header("Content-Disposition", "inline", filename=f"{cid}.png")
                message.attach(image_part)
        else:
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
