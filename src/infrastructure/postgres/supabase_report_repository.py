from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from src.domain.analytics_entities import AccountTypeMetric, TransactionTypeMetric
from src.domain.ports.report_repository import ReportRepository
from src.domain.report_entities import (
    AccountBalancePoint,
    AccountMovementPoint,
    CategoryPoint,
    DailyPoint,
    OutgoingTransactionPoint,
)
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
        return self.fetch_category_breakdown(
            user_id=user_id,
            start_inclusive=week_start,
            end_exclusive=week_end_exclusive,
            flow="EXPENSE",
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
            INNER JOIN transaction_types tt ON tt.id = t."typeId"
            WHERE a."userId" = %(user_id)s
              AND COALESCE(a.include_in_reports, TRUE) = TRUE
              AND COALESCE(a."isActive", TRUE) = TRUE
              AND tt.code = 'NORMAL'
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
                LEFT JOIN transaction_types tt ON tt.id = t."typeId"
                WHERE a."userId" = %(user_id)s
                  AND COALESCE(a.include_in_reports, TRUE) = TRUE
                  AND COALESCE(a."isActive", TRUE) = TRUE
                  AND (tt.code = 'NORMAL' OR tt.code IS NULL)
                GROUP BY a."typeId"
            ),
            bal AS (
                SELECT
                    a."typeId" AS type_id,
                    COALESCE(SUM(a."currentAmount"), 0) AS current_balance,
                    COUNT(*) FILTER (WHERE a."isActive" = TRUE) AS active_accounts
                FROM accounts a
                WHERE a."userId" = %(user_id)s
                  AND COALESCE(a.include_in_reports, TRUE) = TRUE
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
              AND COALESCE(a.include_in_reports, TRUE) = TRUE
              AND COALESCE(a."isActive", TRUE) = TRUE
              AND tt.code = 'NORMAL'
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
        return self.fetch_category_breakdown(
            user_id=user_id,
            start_inclusive=start_inclusive,
            end_exclusive=end_exclusive,
            flow="EXPENSE",
            limit=limit,
        )

    def fetch_category_breakdown(
        self,
        *,
        user_id: str,
        start_inclusive: datetime,
        end_exclusive: datetime,
        flow: str,
        limit: int,
    ) -> list[CategoryPoint]:
        safe_flow = flow.upper().strip()
        if safe_flow not in {"INCOME", "EXPENSE"}:
            raise ValueError("flow debe ser INCOME o EXPENSE")

        query = """
            WITH filtered_tx AS (
                SELECT
                    t.id,
                    t.amount
                FROM transactions t
                INNER JOIN accounts a ON a.id = t."accountId"
                INNER JOIN transaction_types tt ON tt.id = t."typeId"
                WHERE a."userId" = %(user_id)s
                  AND COALESCE(a.include_in_reports, TRUE) = TRUE
                  AND COALESCE(a."isActive", TRUE) = TRUE
                  AND tt.code = 'NORMAL'
                  AND t.flow = %(flow)s
                  AND t."occurredAt" >= %(start)s
                  AND t."occurredAt" < %(end)s
            )
            SELECT
                COALESCE(cat.category_name, 'Sin categoria') AS category_name,
                COALESCE(SUM(ft.amount), 0) AS total_amount,
                COUNT(*) AS transactions_count
            FROM filtered_tx ft
            LEFT JOIN LATERAL (
                SELECT c.name AS category_name
                FROM transaction_categories tc
                INNER JOIN categories c ON c.id = tc."categoryId"
                WHERE tc."transactionId" = ft.id
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
                        "flow": safe_flow,
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

    def fetch_account_movement(
        self,
        *,
        user_id: str,
        start_inclusive: datetime,
        end_exclusive: datetime,
        limit: int,
    ) -> list[AccountMovementPoint]:
        query = """
            SELECT
                a.id AS account_id,
                a.name AS account_name,
                at.name AS account_type,
                COALESCE(SUM(CASE WHEN t.flow = 'INCOME' THEN t.amount ELSE 0 END), 0) AS income,
                COALESCE(SUM(CASE WHEN t.flow = 'EXPENSE' THEN t.amount ELSE 0 END), 0) AS expense,
                COALESCE(SUM(CASE WHEN t.flow = 'INCOME' THEN t.amount ELSE -t.amount END), 0) AS net,
                COALESCE(SUM(t.amount), 0) AS total_movement,
                COUNT(*) AS transactions_count
            FROM transactions t
            INNER JOIN accounts a ON a.id = t."accountId"
            INNER JOIN account_types at ON at.id = a."typeId"
            INNER JOIN transaction_types tt ON tt.id = t."typeId"
            WHERE a."userId" = %(user_id)s
              AND COALESCE(a.include_in_reports, TRUE) = TRUE
              AND COALESCE(a."isActive", TRUE) = TRUE
              AND tt.code = 'NORMAL'
              AND t."occurredAt" >= %(start)s
              AND t."occurredAt" < %(end)s
            GROUP BY a.id, a.name, at.name
            ORDER BY total_movement DESC, transactions_count DESC
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
            AccountMovementPoint(
                account_id=str(row["account_id"]),
                account_name=row["account_name"],
                account_type=row["account_type"],
                income=self._num(row["income"]),
                expense=self._num(row["expense"]),
                net=self._num(row["net"]),
                total_movement=self._num(row["total_movement"]),
                transactions_count=int(row["transactions_count"]),
            )
            for row in rows
        ]

    def fetch_normal_accounts_balances(self, *, user_id: str) -> list[AccountBalancePoint]:
        query = """
            SELECT
                a.id AS account_id,
                a.name AS account_name,
                a."bankName" AS bank_name,
                COALESCE(a."currentAmount", 0) AS current_amount
            FROM accounts a
            INNER JOIN account_types at ON at.id = a."typeId"
            WHERE a."userId" = %(user_id)s
              AND COALESCE(a.include_in_reports, TRUE) = TRUE
              AND COALESCE(a."isActive", TRUE) = TRUE
              AND LOWER(TRIM(at.name)) = 'cuenta normal'
            ORDER BY current_amount DESC, account_name ASC;
        """

        with self._connection_factory.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, {"user_id": user_id})
                rows = cur.fetchall()

        return [
            AccountBalancePoint(
                account_id=str(row["account_id"]),
                account_name=row["account_name"],
                bank_name=row["bank_name"],
                current_amount=self._num(row["current_amount"]),
            )
            for row in rows
        ]

    def fetch_credit_cards_total_debt(self, *, user_id: str) -> float:
        query = """
            WITH card_accounts AS (
                SELECT
                    a.id,
                    COALESCE(a."currentAmount", 0) AS current_amount,
                    COALESCE(cc."creditLimit", 0) AS credit_limit
                FROM accounts a
                INNER JOIN account_types at ON at.id = a."typeId"
                LEFT JOIN credit_cards cc ON cc."accountId" = a.id
                WHERE a."userId" = %(user_id)s
                  AND COALESCE(a.include_in_reports, TRUE) = TRUE
                  AND COALESCE(a."isActive", TRUE) = TRUE
                  AND LOWER(at.name) LIKE '%%tarjeta%%'
                  AND (
                    LOWER(at.name) LIKE '%%credito%%'
                  )
            ),
            account_debt AS (
                SELECT
                    COALESCE(
                        SUM(
                            CASE
                                WHEN credit_limit > 0 THEN GREATEST(credit_limit - current_amount, 0)
                                WHEN current_amount < 0 THEN -current_amount
                                ELSE 0
                            END
                        ),
                        0
                    ) AS debt_amount
                FROM card_accounts
            ),
            installment_debt AS (
                SELECT COALESCE(SUM(i."remainingPrincipal"), 0) AS debt_amount
                FROM credit_card_installments i
                INNER JOIN credit_cards cc ON cc.id = i."creditCardId"
                INNER JOIN accounts a ON a.id = cc."accountId"
                INNER JOIN account_types at ON at.id = a."typeId"
                WHERE a."userId" = %(user_id)s
                  AND COALESCE(a.include_in_reports, TRUE) = TRUE
                  AND COALESCE(a."isActive", TRUE) = TRUE
                  AND LOWER(at.name) LIKE '%%tarjeta%%'
                  AND (
                    LOWER(at.name) LIKE '%%credito%%'
                  )
                  AND i.status = 'ACTIVE'
            )
            SELECT
                (SELECT debt_amount FROM account_debt) AS account_debt,
                (SELECT debt_amount FROM installment_debt) AS installment_debt;
        """

        with self._connection_factory.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, {"user_id": user_id})
                row = cur.fetchone()

        if row is None:
            return 0.0

        account_debt = self._num(row["account_debt"])
        installment_debt = self._num(row["installment_debt"])

        # Avoids potential double counting between card balance and installment balance.
        return round(max(account_debt, installment_debt), 2)

    def fetch_recent_outgoing_normal_transactions(
        self,
        *,
        user_id: str,
        end_exclusive: datetime,
        timezone_name: str,
        limit: int,
    ) -> list[OutgoingTransactionPoint]:
        query = """
            SELECT
                t.id AS transaction_id,
                (t."occurredAt" AT TIME ZONE %(timezone)s)::date AS occurred_day,
                a.name AS account_name,
                COALESCE(NULLIF(t.title, ''), 'Sin titulo') AS title,
                COALESCE(t.amount, 0) AS amount,
                COALESCE(cat.category_name, 'Sin categoria') AS category_name
            FROM transactions t
            INNER JOIN accounts a ON a.id = t."accountId"
            INNER JOIN account_types at ON at.id = a."typeId"
            INNER JOIN transaction_types tt ON tt.id = t."typeId"
            LEFT JOIN LATERAL (
                SELECT c.name AS category_name
                FROM transaction_categories tc
                INNER JOIN categories c ON c.id = tc."categoryId"
                WHERE tc."transactionId" = t.id
                ORDER BY c.name ASC
                LIMIT 1
            ) cat ON TRUE
            WHERE a."userId" = %(user_id)s
              AND COALESCE(a.include_in_reports, TRUE) = TRUE
              AND COALESCE(a."isActive", TRUE) = TRUE
              AND LOWER(TRIM(at.name)) = 'cuenta normal'
              AND tt.code = 'NORMAL'
              AND t.flow = 'EXPENSE'
              AND t."occurredAt" < %(end)s
            ORDER BY t."occurredAt" DESC
            LIMIT %(limit)s;
        """

        with self._connection_factory.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    {
                        "user_id": user_id,
                        "end": end_exclusive,
                        "timezone": timezone_name,
                        "limit": limit,
                    },
                )
                rows = cur.fetchall()

        return [
            OutgoingTransactionPoint(
                transaction_id=str(row["transaction_id"]),
                occurred_at=row["occurred_day"].isoformat(),
                account_name=row["account_name"],
                title=row["title"],
                amount=self._num(row["amount"]),
                category_name=row["category_name"],
            )
            for row in rows
        ]

    def fetch_total_current_balance(self, *, user_id: str) -> float | None:
        query = """
            SELECT COALESCE(SUM(a."currentAmount"), 0) AS total_balance
            FROM accounts a
            WHERE a."userId" = %(user_id)s
              AND COALESCE(a.include_in_reports, TRUE) = TRUE
              AND COALESCE(a."isActive", TRUE) = TRUE;
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

