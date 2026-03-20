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
            # Re-escapa password para evitar errores por % incompleto en la URL original.
            password = quote(parts.password, safe="")
            netloc = f"{user}:{password}@{hostname}"
        else:
            netloc = f"{user}@{hostname}"

    if parts.port is not None:
        netloc = f"{netloc}:{parts.port}"

    query_params = dict(parse_qsl(parts.query, keep_blank_values=True))
    query_params.pop("pgbouncer", None)
    if "sslmode" not in query_params:
        query_params["sslmode"] = "require"

    return urlunsplit(
        (
            parts.scheme,
            netloc,
            parts.path,
            urlencode(query_params),
            parts.fragment,
        )
    )


@contextmanager
def get_connection(database_url: str) -> Iterator[psycopg.Connection]:
    normalized = _normalize_postgres_uri(database_url)
    with psycopg.connect(normalized, row_factory=dict_row) as conn:
        yield conn
