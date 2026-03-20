from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from src.config import Settings
from src.db import get_connection


class WeeklyReportService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build_weekly_report(
        self,
        user_id: str,
        week_start_str: str | None,
        timezone_name: str | None,
    ) -> dict[str, Any]:
        tz_name = timezone_name or self.settings.default_timezone
        week_start_date, week_end_date, week_start_dt, week_end_exclusive_dt = self._build_week_window(
            week_start_str=week_start_str,
            timezone_name=tz_name,
        )

        with get_connection(self.settings.database_url) as conn:
            user_email = self._fetch_user_email(conn=conn, user_id=user_id)
            accounts = self._fetch_account_weekly_metrics(
                conn=conn,
                user_id=user_id,
                week_start=week_start_dt,
                week_end_exclusive=week_end_exclusive_dt,
            )
            account_daily = self._fetch_account_daily_metrics(
                conn=conn,
                user_id=user_id,
                week_start=week_start_dt,
                week_end_exclusive=week_end_exclusive_dt,
                timezone_name=tz_name,
            )
            daily_overview = self._fetch_daily_overview(
                conn=conn,
                user_id=user_id,
                week_start=week_start_dt,
                week_end_exclusive=week_end_exclusive_dt,
                timezone_name=tz_name,
            )
            categories = self._fetch_top_categories(
                conn=conn,
                user_id=user_id,
                week_start=week_start_dt,
                week_end_exclusive=week_end_exclusive_dt,
            )
            latest_categories = self._fetch_latest_categories(
                conn=conn,
                user_id=user_id,
                timezone_name=tz_name,
            )

        complete_days = self._list_days(week_start_date, week_end_date)
        accounts_payload = self._build_accounts_payload(accounts, account_daily, complete_days)
        overview_payload = self._build_daily_overview_payload(daily_overview, complete_days)

        summary = {
            "accounts_count": len(accounts_payload),
            "active_accounts": sum(1 for row in accounts_payload if row["is_active"]),
            "transactions_count": sum(int(row["transactions_count"]) for row in accounts_payload),
            "income": self._sum_field(accounts_payload, "income"),
            "expense": self._sum_field(accounts_payload, "expense"),
            "net": self._sum_field(accounts_payload, "net"),
            "estimated_opening_balance": self._sum_field(accounts_payload, "estimated_opening_balance"),
            "estimated_closing_balance": self._sum_field(accounts_payload, "estimated_closing_balance"),
        }

        categorized_expenses = [item for item in categories if item["flow"] == "EXPENSE"]
        categorized_income = [item for item in categories if item["flow"] == "INCOME"]

        return {
            "user_id": user_id,
            "user_email": user_email,
            "week": {
                "start_date": week_start_date.isoformat(),
                "end_date": week_end_date.isoformat(),
                "timezone": tz_name,
            },
            "summary": summary,
            "accounts": accounts_payload,
            "daily_overview": overview_payload,
            "top_categories": {
                "expense": categorized_expenses[:5],
                "income": categorized_income[:5],
            },
            "latest_categories": latest_categories,
            "generated_at": datetime.now(tz=ZoneInfo("UTC")).isoformat(),
        }

    def _build_week_window(
        self,
        week_start_str: str | None,
        timezone_name: str,
    ) -> tuple[date, date, datetime, datetime]:
        try:
            tz = ZoneInfo(timezone_name)
        except Exception as exc:
            raise ValueError(f"Timezone invalida: {timezone_name}") from exc

        if week_start_str:
            try:
                start_date = date.fromisoformat(week_start_str)
            except ValueError as exc:
                raise ValueError("week_start debe tener formato YYYY-MM-DD") from exc
        else:
            today = datetime.now(tz=tz).date()
            start_date = today - timedelta(days=today.weekday())

        end_date = start_date + timedelta(days=6)

        start_dt = datetime.combine(start_date, time.min, tzinfo=tz)
        end_exclusive = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=tz)

        return start_date, end_date, start_dt, end_exclusive

    def _fetch_account_weekly_metrics(
        self,
        conn,
        user_id: str,
        week_start: datetime,
        week_end_exclusive: datetime,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT
                a.id AS account_id,
                a.name AS account_name,
                a."currentAmount",
                a."isActive",
                a."bankName",
                at.name AS account_type,
                COALESCE(
                    SUM(CASE
                        WHEN t."occurredAt" >= %(week_start)s
                         AND t."occurredAt" < %(week_end)s
                         AND t.flow = 'INCOME' THEN t.amount
                        ELSE 0
                    END),
                    0
                ) AS weekly_income,
                COALESCE(
                    SUM(CASE
                        WHEN t."occurredAt" >= %(week_start)s
                         AND t."occurredAt" < %(week_end)s
                         AND t.flow = 'EXPENSE' THEN t.amount
                        ELSE 0
                    END),
                    0
                ) AS weekly_expense,
                COALESCE(
                    SUM(CASE
                        WHEN t."occurredAt" >= %(week_start)s
                         AND t."occurredAt" < %(week_end)s THEN
                            CASE WHEN t.flow = 'INCOME' THEN t.amount ELSE -t.amount END
                        ELSE 0
                    END),
                    0
                ) AS weekly_net,
                COALESCE(
                    SUM(CASE
                        WHEN t."occurredAt" >= %(week_end)s THEN
                            CASE WHEN t.flow = 'INCOME' THEN t.amount ELSE -t.amount END
                        ELSE 0
                    END),
                    0
                ) AS post_week_net,
                COALESCE(
                    COUNT(*) FILTER (
                        WHERE t."occurredAt" >= %(week_start)s
                          AND t."occurredAt" < %(week_end)s
                    ),
                    0
                ) AS weekly_tx_count
            FROM accounts a
            INNER JOIN account_types at ON at.id = a."typeId"
            LEFT JOIN transactions t ON t."accountId" = a.id
            WHERE a."userId" = %(user_id)s
            GROUP BY
                a.id,
                a.name,
                a."currentAmount",
                a."isActive",
                a."bankName",
                at.name
            ORDER BY a.name ASC;
        """

        with conn.cursor() as cur:
            cur.execute(
                query,
                {
                    "user_id": user_id,
                    "week_start": week_start,
                    "week_end": week_end_exclusive,
                },
            )
            return cur.fetchall()

    def _fetch_user_email(self, conn, user_id: str) -> str | None:
        query = """
            SELECT email
            FROM auth.users
            WHERE id = %(user_id)s::uuid
            LIMIT 1;
        """

        try:
            with conn.cursor() as cur:
                cur.execute(query, {"user_id": user_id})
                row = cur.fetchone()
        except Exception:
            return None

        if not row:
            return None
        return row.get("email")

    def _fetch_account_daily_metrics(
        self,
        conn,
        user_id: str,
        week_start: datetime,
        week_end_exclusive: datetime,
        timezone_name: str,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT
                t."accountId" AS account_id,
                (t."occurredAt" AT TIME ZONE %(timezone)s)::date AS day,
                COALESCE(SUM(CASE WHEN t.flow = 'INCOME' THEN t.amount ELSE 0 END), 0) AS income,
                COALESCE(SUM(CASE WHEN t.flow = 'EXPENSE' THEN t.amount ELSE 0 END), 0) AS expense,
                COALESCE(SUM(CASE WHEN t.flow = 'INCOME' THEN t.amount ELSE -t.amount END), 0) AS net,
                COUNT(*) AS transactions_count
            FROM transactions t
            INNER JOIN accounts a ON a.id = t."accountId"
            WHERE a."userId" = %(user_id)s
              AND t."occurredAt" >= %(week_start)s
              AND t."occurredAt" < %(week_end)s
            GROUP BY t."accountId", day
            ORDER BY day ASC;
        """

        with conn.cursor() as cur:
            cur.execute(
                query,
                {
                    "user_id": user_id,
                    "week_start": week_start,
                    "week_end": week_end_exclusive,
                    "timezone": timezone_name,
                },
            )
            return cur.fetchall()

    def _fetch_daily_overview(
        self,
        conn,
        user_id: str,
        week_start: datetime,
        week_end_exclusive: datetime,
        timezone_name: str,
    ) -> list[dict[str, Any]]:
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
              AND t."occurredAt" >= %(week_start)s
              AND t."occurredAt" < %(week_end)s
            GROUP BY day
            ORDER BY day ASC;
        """

        with conn.cursor() as cur:
            cur.execute(
                query,
                {
                    "user_id": user_id,
                    "week_start": week_start,
                    "week_end": week_end_exclusive,
                    "timezone": timezone_name,
                },
            )
            return cur.fetchall()

    def _fetch_top_categories(
        self,
        conn,
        user_id: str,
        week_start: datetime,
        week_end_exclusive: datetime,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT
                c.id AS category_id,
                c.name AS category_name,
                c.flow,
                COALESCE(SUM(t.amount), 0) AS total_amount,
                COUNT(*) AS transactions_count
            FROM transaction_categories tc
            INNER JOIN transactions t ON t.id = tc."transactionId"
            INNER JOIN categories c ON c.id = tc."categoryId"
            INNER JOIN accounts a ON a.id = t."accountId"
            WHERE a."userId" = %(user_id)s
              AND t."occurredAt" >= %(week_start)s
              AND t."occurredAt" < %(week_end)s
            GROUP BY c.id, c.name, c.flow
            ORDER BY total_amount DESC;
        """

        with conn.cursor() as cur:
            cur.execute(
                query,
                {
                    "user_id": user_id,
                    "week_start": week_start,
                    "week_end": week_end_exclusive,
                },
            )
            rows = cur.fetchall()

        return [
            {
                "category_id": row["category_id"],
                "category_name": row["category_name"],
                "flow": row["flow"],
                "amount": self._num(row["total_amount"]),
                "transactions_count": int(row["transactions_count"]),
            }
            for row in rows
        ]

    def _fetch_latest_categories(
        self,
        conn,
        user_id: str,
        timezone_name: str,
    ) -> list[dict[str, Any]]:
        query = """
            WITH ranked_categories AS (
                SELECT
                    c.id AS category_id,
                    c.name AS category_name,
                    c.flow,
                    (t."occurredAt" AT TIME ZONE %(timezone)s) AS occurred_local,
                    t.amount AS tx_amount,
                    ROW_NUMBER() OVER (
                        PARTITION BY c.id
                        ORDER BY t."occurredAt" DESC
                    ) AS rn
                FROM transaction_categories tc
                INNER JOIN transactions t ON t.id = tc."transactionId"
                INNER JOIN categories c ON c.id = tc."categoryId"
                INNER JOIN accounts a ON a.id = t."accountId"
                WHERE a."userId" = %(user_id)s
            )
            SELECT
                category_id,
                category_name,
                flow,
                occurred_local AS last_occurred_at,
                tx_amount AS last_amount
            FROM ranked_categories
            WHERE rn = 1
            ORDER BY occurred_local DESC
            LIMIT 8;
        """

        with conn.cursor() as cur:
            cur.execute(
                query,
                {
                    "user_id": user_id,
                    "timezone": timezone_name,
                },
            )
            rows = cur.fetchall()

        result: list[dict[str, Any]] = []
        for row in rows:
            last_occurred_at = row["last_occurred_at"]
            result.append(
                {
                    "category_id": row["category_id"],
                    "category_name": row["category_name"],
                    "flow": row["flow"],
                    "last_occurred_at": (
                        last_occurred_at.isoformat(sep=" ") if last_occurred_at else None
                    ),
                    "last_amount": self._num(row["last_amount"]),
                }
            )

        return result

    def _build_accounts_payload(
        self,
        account_rows: list[dict[str, Any]],
        account_daily_rows: list[dict[str, Any]],
        week_days: list[date],
    ) -> list[dict[str, Any]]:
        daily_map: dict[str, dict[date, dict[str, Any]]] = {}
        for row in account_daily_rows:
            account_id = row["account_id"]
            day = row["day"]
            daily_map.setdefault(account_id, {})[day] = {
                "date": day.isoformat(),
                "income": self._num(row["income"]),
                "expense": self._num(row["expense"]),
                "net": self._num(row["net"]),
                "transactions_count": int(row["transactions_count"]),
            }

        payload: list[dict[str, Any]] = []
        for row in account_rows:
            current_amount = Decimal(row["currentAmount"] or 0)
            post_week_net = Decimal(row["post_week_net"] or 0)
            weekly_net = Decimal(row["weekly_net"] or 0)

            opening = current_amount - post_week_net
            closing = opening + weekly_net

            account_id = row["account_id"]
            account_days = daily_map.get(account_id, {})
            daily_payload = []

            for day in week_days:
                day_metrics = account_days.get(day)
                if day_metrics:
                    daily_payload.append(day_metrics)
                    continue
                daily_payload.append(
                    {
                        "date": day.isoformat(),
                        "income": 0.0,
                        "expense": 0.0,
                        "net": 0.0,
                        "transactions_count": 0,
                    }
                )

            payload.append(
                {
                    "account_id": account_id,
                    "account_name": row["account_name"],
                    "account_type": row["account_type"],
                    "bank_name": row["bankName"],
                    "is_active": bool(row["isActive"]),
                    "current_amount": self._num(current_amount),
                    "estimated_opening_balance": self._num(opening),
                    "estimated_closing_balance": self._num(closing),
                    "income": self._num(row["weekly_income"]),
                    "expense": self._num(row["weekly_expense"]),
                    "net": self._num(row["weekly_net"]),
                    "transactions_count": int(row["weekly_tx_count"]),
                    "daily": daily_payload,
                }
            )

        return payload

    def _build_daily_overview_payload(
        self,
        daily_rows: list[dict[str, Any]],
        week_days: list[date],
    ) -> list[dict[str, Any]]:
        daily_map = {
            row["day"]: {
                "date": row["day"].isoformat(),
                "income": self._num(row["income"]),
                "expense": self._num(row["expense"]),
                "net": self._num(row["net"]),
                "transactions_count": int(row["transactions_count"]),
            }
            for row in daily_rows
        }

        payload = []
        for day in week_days:
            payload.append(
                daily_map.get(
                    day,
                    {
                        "date": day.isoformat(),
                        "income": 0.0,
                        "expense": 0.0,
                        "net": 0.0,
                        "transactions_count": 0,
                    },
                )
            )

        return payload

    @staticmethod
    def _list_days(start_date: date, end_date: date) -> list[date]:
        days: list[date] = []
        current = start_date
        while current <= end_date:
            days.append(current)
            current += timedelta(days=1)
        return days

    @staticmethod
    def _num(value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, Decimal):
            return round(float(value), 2)
        if isinstance(value, int):
            return float(value)
        if isinstance(value, float):
            return round(value, 2)
        return round(float(value), 2)

    @staticmethod
    def _sum_field(rows: list[dict[str, Any]], field: str) -> float:
        return round(sum(float(row[field]) for row in rows), 2)




