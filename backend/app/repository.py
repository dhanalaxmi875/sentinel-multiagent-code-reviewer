from __future__ import annotations

import json
import hashlib
import hmac
import secrets
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.config import Settings

AGENTS = (
    "orchestrator",
    "bug_detector",
    "security",
    "code_quality",
    "test_coverage",
    "semgrep",
    "verifier",
    "summarizer",
)
SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime | None = None) -> str:
    return (value or utc_now()).isoformat()


class Repository:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.path = settings.database_path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            self.path,
            timeout=30,
            isolation_level="DEFERRED",
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def migrate(self) -> None:
        migrations = Path(__file__).parent / "migrations"
        with closing(self.connect()) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            for version, filename in ((1, "001_initial.sql"), (2, "002_auth.sql")):
                exists = connection.execute(
                    "SELECT 1 FROM schema_migrations WHERE version = ?",
                    (version,),
                ).fetchone()
                if exists:
                    continue
                connection.executescript(
                    (migrations / filename).read_text(encoding="utf-8")
                )
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES(?, ?)",
                    (version, iso()),
                )
                connection.commit()

    @staticmethod
    def _password_digest(password: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)

    def create_user(self, email: str, password: str) -> dict[str, str] | None:
        user_id = str(uuid.uuid4())
        salt = secrets.token_bytes(16)
        digest = self._password_digest(password, salt)
        created_at = iso()
        try:
            with closing(self.connect()) as connection:
                connection.execute(
                    "INSERT INTO users(id,email,password_salt,password_hash,created_at) "
                    "VALUES(?,?,?,?,?)",
                    (user_id, email, salt.hex(), digest.hex(), created_at),
                )
                connection.commit()
        except sqlite3.IntegrityError:
            return None
        return {"id": user_id, "email": email, "created_at": created_at}

    def verify_user(self, email: str, password: str) -> dict[str, str] | None:
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT id,email,password_salt,password_hash,created_at "
                "FROM users WHERE email=? COLLATE NOCASE",
                (email,),
            ).fetchone()
        if row is None:
            # Keep unknown-account attempts close to the cost of a password check.
            self._password_digest(password, b"sentinel-demo-salt")
            return None
        matches = hmac.compare_digest(
            self._password_digest(password, bytes.fromhex(row["password_salt"])),
            bytes.fromhex(row["password_hash"]),
        )
        if not matches:
            return None
        return {"id": row["id"], "email": row["email"], "created_at": row["created_at"]}

    def create_session(self, user_id: str) -> tuple[str, datetime]:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = utc_now()
        expires_at = now + timedelta(days=14)
        with closing(self.connect()) as connection:
            connection.execute(
                "DELETE FROM auth_sessions WHERE expires_at <= ?", (iso(now),)
            )
            connection.execute(
                "INSERT INTO auth_sessions(token_hash,user_id,created_at,expires_at) "
                "VALUES(?,?,?,?)",
                (token_hash, user_id, iso(now), iso(expires_at)),
            )
            connection.commit()
        return token, expires_at

    def get_session_user(self, token: str) -> dict[str, str] | None:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT u.id,u.email,u.created_at FROM auth_sessions s "
                "JOIN users u ON u.id=s.user_id "
                "WHERE s.token_hash=? AND s.expires_at>?",
                (token_hash, iso()),
            ).fetchone()
        if row is None:
            return None
        return {"id": row["id"], "email": row["email"], "created_at": row["created_at"]}

    def revoke_session(self, token: str) -> None:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with closing(self.connect()) as connection:
            connection.execute(
                "DELETE FROM auth_sessions WHERE token_hash=?", (token_hash,)
            )
            connection.commit()

    def claim_legacy_reviews(self, legacy_token: str | None, user_id: str) -> None:
        """Attach this browser's pre-auth reviews to the account that signs in."""
        if not legacy_token or len(legacy_token) > 128:
            return
        with closing(self.connect()) as connection:
            connection.execute(
                "UPDATE reviews SET client_token=? WHERE client_token=?",
                (f"user:{user_id}", legacy_token),
            )
            connection.commit()

    def recover_and_purge(self) -> None:
        with closing(self.connect()) as connection:
            connection.execute(
                "UPDATE reviews SET status='failed', error=?, finished_at=? "
                "WHERE status='running'",
                ("interrupted by server restart", iso()),
            )
            connection.commit()
        self.purge_expired()

    def purge_expired(self) -> None:
        if self.settings.retention_days <= 0:
            return
        cutoff = iso(utc_now() - timedelta(days=self.settings.retention_days))
        with closing(self.connect()) as connection:
            connection.execute("DELETE FROM reviews WHERE created_at < ?", (cutoff,))
            connection.commit()

    def enqueue_review(
        self,
        *,
        client_token: str,
        diff_hash: str,
        diff_text: str,
        file_paths: list[str],
        source: str,
        review_id: str,
        force: bool = False,
        is_demo: bool = False,
    ) -> tuple[str, str | None, int]:
        with closing(self.connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                if not force:
                    cached = connection.execute(
                        "SELECT id FROM reviews WHERE client_token=? AND diff_hash=? "
                        "AND status='done' ORDER BY finished_at DESC LIMIT 1",
                        (client_token, diff_hash),
                    ).fetchone()
                    if cached:
                        connection.commit()
                        return "cached", cached["id"], 0

                active = connection.execute(
                    "SELECT COUNT(*) FROM reviews WHERE client_token=? "
                    "AND status IN ('queued','running')",
                    (client_token,),
                ).fetchone()[0]
                if int(active) >= self.settings.max_active_reviews_per_token:
                    connection.rollback()
                    return "active_limit", None, 60

                window_start = iso(
                    utc_now() - timedelta(hours=1)
                )
                recent = connection.execute(
                    "SELECT COUNT(*) FROM reviews WHERE client_token=? AND created_at>=?",
                    (client_token, window_start),
                ).fetchone()[0]
                if int(recent) >= self.settings.reviews_per_hour:
                    oldest = connection.execute(
                        "SELECT MIN(created_at) FROM reviews "
                        "WHERE client_token=? AND created_at>=?",
                        (client_token, window_start),
                    ).fetchone()[0]
                    retry = 60
                    if oldest:
                        elapsed = (
                            utc_now() - datetime.fromisoformat(oldest)
                        ).total_seconds()
                        retry = max(1, int(3600 - elapsed))
                    connection.rollback()
                    return "rate_limit", None, retry

                connection.execute(
                    "INSERT INTO reviews("
                    "id,client_token,diff_hash,diff_text,file_paths,source,"
                    "status,is_demo,created_at"
                    ") VALUES(?,?,?,?,?,?,'queued',?,?)",
                    (
                        review_id,
                        client_token,
                        diff_hash,
                        diff_text,
                        json.dumps(file_paths),
                        source,
                        int(is_demo),
                        iso(),
                    ),
                )
                connection.executemany(
                    "INSERT INTO agent_runs(id,review_id,agent,status) "
                    "VALUES(?,?,?,'idle')",
                    [
                        (str(uuid.uuid4()), review_id, agent)
                        for agent in AGENTS
                    ],
                )
                connection.commit()
                return "created", review_id, 0
            except Exception:
                connection.rollback()
                raise

    def claim_next(self) -> dict[str, Any] | None:
        with closing(self.connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM reviews WHERE status='queued' "
                "ORDER BY created_at ASC LIMIT 1"
            ).fetchone()
            if not row:
                connection.commit()
                return None
            started_at = iso()
            connection.execute(
                "UPDATE reviews SET status='running', started_at=?, error=NULL "
                "WHERE id=? AND status='queued'",
                (started_at, row["id"]),
            )
            connection.commit()
            result = dict(row)
            result["status"] = "running"
            result["started_at"] = started_at
            return result

    def get_review(self, review_id: str, token: str) -> dict[str, Any] | None:
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT * FROM reviews WHERE id=? AND client_token=?",
                (review_id, token),
            ).fetchone()
            if not row:
                return None
            review = dict(row)
            review["file_paths"] = json.loads(review["file_paths"] or "[]")
            review["is_demo"] = bool(review.get("is_demo"))
            review["is_replay"] = bool(review.get("is_replay"))
            review["agents"] = [
                dict(item)
                for item in connection.execute(
                    "SELECT agent,status,duration_s,finding_count FROM agent_runs "
                    "WHERE review_id=? ORDER BY CASE agent "
                    "WHEN 'orchestrator' THEN 0 WHEN 'bug_detector' THEN 1 "
                    "WHEN 'security' THEN 2 WHEN 'code_quality' THEN 3 "
                    "WHEN 'test_coverage' THEN 4 WHEN 'semgrep' THEN 5 "
                    "WHEN 'verifier' THEN 6 ELSE 7 END",
                    (review_id,),
                ).fetchall()
            ]
            findings = []
            for finding in connection.execute(
                "SELECT id,title,severity,confidence,cwe,file,line,evidence,fix,"
                "sources,status,rejection_reason FROM findings "
                "WHERE review_id=? ORDER BY status, severity, title",
                (review_id,),
            ).fetchall():
                item = dict(finding)
                item["sources"] = json.loads(item["sources"] or "[]")
                findings.append(item)
            review["findings"] = findings
            review["logs"] = [
                dict(item)
                for item in connection.execute(
                    "SELECT ts,level,message FROM review_logs "
                    "WHERE review_id=? ORDER BY ts,id",
                    (review_id,),
                ).fetchall()
            ]
            return review

    def get_reviews(
        self, token: str, limit: int, offset: int
    ) -> list[dict[str, Any]]:
        with closing(self.connect()) as connection:
            rows = connection.execute(
                "SELECT id,status,verdict,created_at,duration_s FROM reviews "
                "WHERE client_token=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (token, limit, offset),
            ).fetchall()
            summaries = []
            for row in rows:
                counts = self._finding_counts(connection, row["id"])
                item = dict(row)
                item["finding_counts"] = counts
                summaries.append(item)
            return summaries

    def get_stats(self, token: str) -> dict[str, Any]:
        with closing(self.connect()) as connection:
            total = int(
                connection.execute(
                    "SELECT COUNT(*) FROM reviews WHERE client_token=?",
                    (token,),
                ).fetchone()[0]
            )
            verdict_counts = {
                "approve": 0,
                "request_changes": 0,
            }
            for row in connection.execute(
                "SELECT verdict,COUNT(*) AS count FROM reviews "
                "WHERE client_token=? AND status='done' GROUP BY verdict",
                (token,),
            ).fetchall():
                if row["verdict"] == "APPROVE":
                    verdict_counts["approve"] = int(row["count"])
                elif row["verdict"] == "REQUEST_CHANGES":
                    verdict_counts["request_changes"] = int(row["count"])

            duration = connection.execute(
                "SELECT AVG(duration_s) FROM reviews "
                "WHERE client_token=? AND status='done' AND duration_s IS NOT NULL",
                (token,),
            ).fetchone()[0]

            finding_counts = {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
            }
            for row in connection.execute(
                "SELECT LOWER(f.severity) AS severity,COUNT(*) AS count "
                "FROM findings f JOIN reviews r ON r.id=f.review_id "
                "WHERE r.client_token=? AND r.status='done' AND f.status='kept' "
                "GROUP BY f.severity",
                (token,),
            ).fetchall():
                key = str(row["severity"] or "").lower()
                if key in finding_counts:
                    finding_counts[key] = int(row["count"])

            return {
                "total_reviews": total,
                "finding_counts": finding_counts,
                "verdict_split": verdict_counts,
                "avg_review_time_s": float(duration or 0.0),
            }

    @staticmethod
    def _finding_counts(
        connection: sqlite3.Connection, review_id: str
    ) -> dict[str, int]:
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for row in connection.execute(
            "SELECT LOWER(severity) AS severity,COUNT(*) AS count "
            "FROM findings WHERE review_id=? AND status='kept' GROUP BY severity",
            (review_id,),
        ).fetchall():
            key = str(row["severity"] or "").lower()
            if key in counts:
                counts[key] = int(row["count"])
        return counts

    def delete_review(self, review_id: str, token: str) -> bool:
        with closing(self.connect()) as connection:
            cursor = connection.execute(
                "DELETE FROM reviews WHERE id=? AND client_token=?",
                (review_id, token),
            )
            connection.commit()
            return cursor.rowcount > 0

    def set_review_error(self, review_id: str, message: str) -> None:
        with closing(self.connect()) as connection:
            connection.execute(
                "UPDATE reviews SET status='failed',error=?,finished_at=? WHERE id=?",
                (message, iso(), review_id),
            )
            connection.execute(
                "UPDATE agent_runs SET status='failed' "
                "WHERE review_id=? AND status='running'",
                (review_id,),
            )
            connection.commit()

    def queue_depth(self) -> int:
        with closing(self.connect()) as connection:
            return int(
                connection.execute(
                    "SELECT COUNT(*) FROM reviews WHERE status='queued'"
                ).fetchone()[0]
            )

    def set_agent(
        self,
        review_id: str,
        agent: str,
        status: str,
        duration_s: float | None = None,
        finding_count: int | None = None,
    ) -> None:
        with closing(self.connect()) as connection:
            connection.execute(
                "UPDATE agent_runs SET status=?,"
                "duration_s=COALESCE(?,duration_s), "
                "finding_count=COALESCE(?,finding_count) "
                "WHERE review_id=? AND agent=?",
                (status, duration_s, finding_count, review_id, agent),
            )
            connection.commit()

    def add_log(self, review_id: str, ts: str, level: str, message: str) -> None:
        with closing(self.connect()) as connection:
            connection.execute(
                "INSERT INTO review_logs(id,review_id,ts,level,message) "
                "VALUES(?,?,?,?,?)",
                (str(uuid.uuid4()), review_id, ts, level, message),
            )
            connection.commit()

    def complete_review(
        self,
        review_id: str,
        report_md: str,
        verdict: str | None,
        duration_s: float,
        findings: list[dict[str, Any]],
        is_demo: bool = False,
        is_replay: bool = False,
    ) -> None:
        with closing(self.connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "DELETE FROM findings WHERE review_id=?", (review_id,)
            )
            connection.executemany(
                "INSERT INTO findings("
                "id,review_id,title,severity,confidence,cwe,file,line,"
                "evidence,fix,sources,status,rejection_reason"
                ") VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [
                    (
                        str(item.get("id") or uuid.uuid4()),
                        review_id,
                        item.get("title") or "Untitled finding",
                        item.get("severity") or "LOW",
                        item.get("confidence") or "LOW",
                        item.get("cwe"),
                        item.get("file"),
                        item.get("line"),
                        item.get("evidence"),
                        item.get("fix"),
                        json.dumps(item.get("sources") or []),
                        item.get("status") or "kept",
                        item.get("rejection_reason"),
                    )
                    for item in findings
                ],
            )
            connection.execute(
                "UPDATE reviews SET status='done',verdict=?,report_md=?,"
                "error=NULL,finished_at=?,duration_s=?,is_demo=?,is_replay=? "
                "WHERE id=?",
                (
                    verdict,
                    report_md,
                    iso(),
                    duration_s,
                    int(is_demo),
                    int(is_replay),
                    review_id,
                ),
            )
            connection.commit()
