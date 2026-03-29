from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from src.domain.analytics_entities import AccountTypeMetric, TransactionTypeMetric
from src.domain.ports.report_repository import ReportRepository
from src.domain.report_entities import CategoryPoint, DailyPoint
from src.infrastructure.postgres.connection_factory import PostgresConnectionFactory


class SupabaseReportRepository(ReportRepository):
    def __init__(self, connection_factory: PostgresConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def fetch_daily_overview(
        self,
        *,
        user_id: str,
        week_start: datetime,
        week_end_exclusive: datetime,
        timezone_name: str,
    ) -> list[DailyPoint]:
        return self.fetch_daily_history(
            user_id=user_id,
            start_inclusive=week_start,
            end_exclusive=week_end_exclusive,
            timezone_name=timezone_name,
        )

    def fetch_expense_categories(
        self,
        *,
        user_id: str,
        week_start: datetime,
        week_end_exclusive: datetime,
    ) -> list[CategoryPoint]:
        return self.fetch_expense_category_breakdown(
            user_id=user_id,
            start_inclusive=week_start,
            end_exclusive=week_end_exclusive,
            limit=8,
        )

    def fetch_daily_history(
        self,
        *,
        user_id: str,
        start_inclusive: datetime,
        end_exclusive: datetime,
        timezone_name: str,
    ) -> list[DailyPoint]:
        query = """
            SELECT
                (t."occurredAt" AT TIME ZONE %(timezone)s)::date AS day,
                COALESCE(SUM(CASE WHEN t.flow = 'INCOME' THEN t.amount ELSE 0 END), 0) AS income,
                COALESCE(SUM(CASE WHEN t.flow = 'EXPENSE' THEN t.amount ELSE 0 END), 0) AS expense,
                COALESCE(SUM(CASE WHEN t.flow = 'INCOME' THEN t.amount ELSE -t.amount END), 0) AS net,
                COUNT(*) AS transactions_count
            FROM transactions t
            INNER JOIN accounts a ON a.id = t."accountId"
            WHERE a."userId" = %(user_id)s
              AND t."occurredAt" >= %(start)s
              AND t."occurredAt" < %(end)s
            GROUP BY day
            ORDER BY day ASC;
        """

        with self._connection_factory.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    {
                        "user_id": user_id,
                        "start": start_inclusive,
                        "end": end_exclusive,
                        "timezone": timezone_name,
                    },
                )
                rows = cur.fetchall()

        return [
            DailyPoint(
                date=row["day"].isoformat(),
                income=self._num(row["income"]),
                expense=self._num(row["expense"]),
                net=self._num(row["net"]),
                transactions_count=int(row["transactions_count"]),
            )
            for row in rows
        ]

    def fetch_account_type_breakdown(
        self,
        *,
        user_id: str,
        start_inclusive: datetime,
        end_exclusive: datetime,
    ) -> list[AccountTypeMetric]:
        query = """
            WITH tx AS (
                SELECT
                    a."typeId" AS type_id,
                    COALESCE(SUM(CASE WHEN t.flow = 'INCOME' THEN t.amount ELSE 0 END), 0) AS income,
                    COALESCE(SUM(CASE WHEN t.flow = 'EXPENSE' THEN t.amount ELSE 0 END), 0) AS expense,
                    COALESCE(SUM(CASE WHEN t.flow = 'INCOME' THEN t.amount ELSE -t.amount END), 0) AS net,
                    COUNT(t.id) AS transactions_count
                FROM accounts a
                LEFT JOIN transactions t ON t."accountId" = a.id
                    AND t."occurredAt" >= %(start)s
                    AND t."occurredAt" < %(end)s
                WHERE a."userId" = %(user_id)s
                GROUP BY a."typeId"
            ),
            bal AS (
                SELECT
                    a."typeId" AS type_id,
                    COALESCE(SUM(a."currentAmount"), 0) AS current_balance,
                    COUNT(*) FILTER (WHERE a."isActive" = TRUE) AS active_accounts
                FROM accounts a
                WHERE a."userId" = %(user_id)s
                GROUP BY a."typeId"
            )
            SELECT
                at.name AS account_type,
                COALESCE(bal.active_accounts, 0) AS active_accounts,
                COALESCE(bal.current_balance, 0) AS current_balance,
                COALESCE(tx.income, 0) AS income,
                COALESCE(tx.expense, 0) AS expense,
                COALESCE(tx.net, 0) AS net,
                COALESCE(tx.transactions_count, 0) AS transactions_count
            FROM account_types at
            LEFT JOIN bal ON bal.type_id = at.id
            LEFT JOIN tx ON tx.type_id = at.id
            WHERE bal.type_id IS NOT NULL OR tx.type_id IS NOT NULL
            ORDER BY current_balance DESC, account_type ASC;
        """

        with self._connection_factory.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    {
                        "user_id": user_id,
                        "start": start_inclusive,
                        "end": end_exclusive,
                    },
                )
                rows = cur.fetchall()

        return [
            AccountTypeMetric(
                account_type=row["account_type"],
                active_accounts=int(row["active_accounts"]),
                current_balance=self._num(row["current_balance"]),
                income=self._num(row["income"]),
                expense=self._num(row["expense"]),
                net=self._num(row["net"]),
                transactions_count=int(row["transactions_count"]),
            )
            for row in rows
        ]

    def fetch_transaction_type_breakdown(
        self,
        *,
        user_id: str,
        start_inclusive: datetime,
        end_exclusive: datetime,
    ) -> list[TransactionTypeMetric]:
        query = """
            SELECT
                tt.code AS type_code,
                tt.name AS type_name,
                COALESCE(SUM(CASE WHEN t.flow = 'INCOME' THEN t.amount ELSE 0 END), 0) AS income,
                COALESCE(SUM(CASE WHEN t.flow = 'EXPENSE' THEN t.amount ELSE 0 END), 0) AS expense,
                COALESCE(SUM(CASE WHEN t.flow = 'INCOME' THEN t.amount ELSE -t.amount END), 0) AS net,
                COUNT(*) AS transactions_count
            FROM transactions t
            INNER JOIN transaction_types tt ON tt.id = t."typeId"
            INNER JOIN accounts a ON a.id = t."accountId"
            WHERE a."userId" = %(user_id)s
              AND t."occurredAt" >= %(start)s
              AND t."occurredAt" < %(end)s
            GROUP BY tt.id, tt.code, tt.name
            ORDER BY transactions_count DESC, expense DESC;
        """

        with self._connection_factory.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    {
                        "user_id": user_id,
                        "start": start_inclusive,
                        "end": end_exclusive,
                    },
                )
                rows = cur.fetchall()

        return [
            TransactionTypeMetric(
                transaction_type_code=row["type_code"],
                transaction_type_name=row["type_name"],
                income=self._num(row["income"]),
                expense=self._num(row["expense"]),
                net=self._num(row["net"]),
                transactions_count=int(row["transactions_count"]),
            )
            for row in rows
        ]

    def fetch_expense_category_breakdown(
        self,
        *,
        user_id: str,
        start_inclusive: datetime,
        end_exclusive: datetime,
        limit: int,
    ) -> list[CategoryPoint]:
        query = """
            WITH expense_tx AS (
                SELECT
                    t.id,
                    t.amount
                FROM transactions t
                INNER JOIN accounts a ON a.id = t."accountId"
                WHERE a."userId" = %(user_id)s
                  AND t."occurredAt" >= %(start)s
                  AND t."occurredAt" < %(end)s
                  AND t.flow = 'EXPENSE'
            )
            SELECT
                COALESCE(cat.category_name, 'Sin categoria') AS category_name,
                COALESCE(SUM(et.amount), 0) AS total_amount,
                COUNT(*) AS transactions_count
            FROM expense_tx et
            LEFT JOIN LATERAL (
                SELECT c.name AS category_name
                FROM transaction_categories tc
                INNER JOIN categories c ON c.id = tc."categoryId"
                WHERE tc."transactionId" = et.id
                ORDER BY c.name ASC
                LIMIT 1
            ) cat ON TRUE
            GROUP BY COALESCE(cat.category_name, 'Sin categoria')
            ORDER BY total_amount DESC
            LIMIT %(limit)s;
        """

        with self._connection_factory.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    {
                        "user_id": user_id,
                        "start": start_inclusive,
                        "end": end_exclusive,
                        "limit": limit,
                    },
                )
                rows = cur.fetchall()

        return [
            CategoryPoint(
                category_name=row["category_name"],
                amount=self._num(row["total_amount"]),
                transactions_count=int(row["transactions_count"]),
            )
            for row in rows
        ]

    def fetch_total_current_balance(self, *, user_id: str) -> float | None:
        query = """
            SELECT COALESCE(SUM(a."currentAmount"), 0) AS total_balance
            FROM accounts a
            WHERE a."userId" = %(user_id)s
              AND a."isActive" = TRUE;
        """

        with self._connection_factory.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, {"user_id": user_id})
                row = cur.fetchone()

        if row is None:
            return None
        return self._num(row["total_balance"])

    @staticmethod
    def _num(value) -> float:
        if value is None:
            return 0.0
        if isinstance(value, Decimal):
            return round(float(value), 2)
        return round(float(value), 2)
