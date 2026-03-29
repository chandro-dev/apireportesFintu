from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

import psycopg
from psycopg.rows import dict_row


def _normalize_postgres_uri(uri: str) -> str:
    parts = urlsplit(uri)
    if parts.scheme not in {"postgres", "postgresql"}:
        return uri

    hostname = parts.hostname or ""
    netloc = hostname

    if parts.username is not None:
        user = quote(parts.username, safe="")
        if parts.password is not None:
            password = quote(parts.password, safe="")
            netloc = f"{user}:{password}@{hostname}"
        else:
            netloc = f"{user}@{hostname}"

    if parts.port is not None:
        netloc = f"{netloc}:{parts.port}"

    query_params = dict(parse_qsl(parts.query, keep_blank_values=True))
    query_params.pop("pgbouncer", None)
    query_params.setdefault("sslmode", "require")

    return urlunsplit(
        (parts.scheme, netloc, parts.path, urlencode(query_params), parts.fragment)
    )


class PostgresConnectionFactory:
    def __init__(self, connection_uri: str) -> None:
        self._connection_uri = _normalize_postgres_uri(connection_uri)

    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection]:
        with psycopg.connect(self._connection_uri, row_factory=dict_row) as conn:
            yield conn
