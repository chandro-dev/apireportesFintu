from __future__ import annotations

from typing import Protocol


class HtmlEmailSender(Protocol):
    def send_html_email(
        self,
        *,
        to_email: str,
        subject: str,
        html_body: str,
        from_email: str,
        inline_images: dict[str, bytes] | None = None,
    ) -> None:
        ...
