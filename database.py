import os
import sqlite3
from typing import Iterable, Tuple


DB_FILENAME = "camptrack.db"


def _project_root() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _db_path() -> str:
    return os.path.join(_project_root(), "data", DB_FILENAME)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    # Enforce foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _executescript(conn: sqlite3.Connection, script: str) -> None:
    conn.executescript(script)


def _executemany(conn: sqlite3.Connection, sql: str, rows: Iterable[Tuple]) -> None:
    conn.executemany(sql, list(rows))


def init_db() -> None:
    """Create tables and indexes if they do not exist."""
    os.makedirs(os.path.join(_project_root(), "data"), exist_ok=True)
    with _connect() as conn:
        _executescript(
            conn,
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL CHECK (role IN ('admin','coordinator','leader','parent')),
                enabled INTEGER NOT NULL DEFAULT 1,
                password TEXT NOT NULL DEFAULT ''
            );

            -- Exactly one active coordinator and one active admin via partial unique indexes
            CREATE UNIQUE INDEX IF NOT EXISTS one_coordinator ON users(role) WHERE role='coordinator' AND enabled=1;
            CREATE UNIQUE INDEX IF NOT EXISTS one_admin ON users(role) WHERE role='admin' AND enabled=1;

            -- Parent-camper table: allows parent to be associated with multiple campers
            CREATE TABLE IF NOT EXISTS parent_campers (
                id INTEGER PRIMARY KEY,
                parent_user_id INTEGER NOT NULL,
                camper_id INTEGER NOT NULL,
                UNIQUE(parent_user_id, camper_id),
                FOREIGN KEY (parent_user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (camper_id) REFERENCES campers(id) ON DELETE CASCADE
            );

            -- Consent forms table: stores yes/no consent and optional notes
            CREATE TABLE IF NOT EXISTS consent_forms (
                id INTEGER PRIMARY KEY,
                parent_user_id INTEGER NOT NULL,
                camper_id INTEGER NOT NULL,
                camp_id INTEGER NOT NULL,
                consent INTEGER NOT NULL,                -- 0 = no, 1 = yes
                notes TEXT NOT NULL DEFAULT '',
                submitted_at TEXT NOT NULL,
                FOREIGN KEY (parent_user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (camper_id) REFERENCES campers(id) ON DELETE CASCADE,
                FOREIGN KEY (camp_id) REFERENCES camps(id) ON DELETE CASCADE
            );

            -- Camper feedback table: stores free‑text feedback per camper per camp
            CREATE TABLE IF NOT EXISTS camper_feedback (
                id INTEGER PRIMARY KEY,
                parent_user_id INTEGER NOT NULL,
                camper_id INTEGER NOT NULL,
                camp_id INTEGER NOT NULL,
                feedback TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                FOREIGN KEY (parent_user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (camper_id) REFERENCES campers(id) ON DELETE CASCADE,
                FOREIGN KEY (camp_id) REFERENCES camps(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS camps (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                area TEXT,
                start_date TEXT NOT NULL, -- YYYY-MM-DD
                end_date TEXT NOT NULL,   -- YYYY-MM-DD
                type TEXT NOT NULL CHECK (type IN ('day','overnight','expedition')),
                daily_food_units_planned INTEGER NOT NULL DEFAULT 0,
                default_food_units_per_camper_per_day INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS leader_assignments (
                id INTEGER PRIMARY KEY,
                leader_user_id INTEGER NOT NULL,
                camp_id INTEGER NOT NULL,
                UNIQUE(leader_user_id, camp_id),
                FOREIGN KEY (leader_user_id) REFERENCES users(id) ON DELETE RESTRICT,
                FOREIGN KEY (camp_id) REFERENCES camps(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS campers (
                id INTEGER PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                dob TEXT NOT NULL, -- YYYY-MM-DD
                emergency_contact TEXT NOT NULL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS camper_identity
            ON campers(lower(first_name), lower(last_name), dob);

            CREATE TABLE IF NOT EXISTS camp_campers (
                id INTEGER PRIMARY KEY,
                camp_id INTEGER NOT NULL,
                camper_id INTEGER NOT NULL,
                food_units_per_day INTEGER NOT NULL DEFAULT 0,
                UNIQUE(camp_id, camper_id),
                FOREIGN KEY (camp_id) REFERENCES camps(id) ON DELETE CASCADE,
                FOREIGN KEY (camper_id) REFERENCES campers(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY,
                camp_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                date TEXT NOT NULL, -- YYYY-MM-DD
                FOREIGN KEY (camp_id) REFERENCES camps(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS camper_activity (
                id INTEGER PRIMARY KEY,
                activity_id INTEGER NOT NULL,
                camper_id INTEGER NOT NULL,
                UNIQUE(activity_id, camper_id),
                FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
                FOREIGN KEY (camper_id) REFERENCES campers(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS daily_reports (
                id INTEGER PRIMARY KEY,
                date TEXT NOT NULL, -- YYYY-MM-DD
                camp_id INTEGER NOT NULL,
                leader_user_id INTEGER NOT NULL,
                notes TEXT,
                FOREIGN KEY (camp_id) REFERENCES camps(id) ON DELETE CASCADE,
                FOREIGN KEY (leader_user_id) REFERENCES users(id) ON DELETE RESTRICT
            );

            CREATE UNIQUE INDEX IF NOT EXISTS unique_daily_report
            ON daily_reports(date, camp_id, leader_user_id);

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS stock_topups (
                id INTEGER PRIMARY KEY,
                camp_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                delta_daily_units INTEGER NOT NULL,
                FOREIGN KEY (camp_id) REFERENCES camps(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                sender_user_id INTEGER,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_user_id) REFERENCES users(id) ON DELETE SET NULL
            );
            """,
        )


def seed_initial_data() -> None:
    """Seed baseline settings and users per Note 1.

    - Users: admin, coordinator, leader1..leader3 with empty passwords and enabled=1
    - Settings: daily_pay_rate default to '0'
    """
    with _connect() as conn:
        # Default settings
        conn.execute(
            "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?);",
            ("daily_pay_rate", "0"),
        )

        # Baseline users (insert if missing)
        baseline_users = [
            ("admin", "admin"),
            ("coordinator", "coordinator"),
            ("leader1", "leader"),
            ("leader2", "leader"),
            ("leader3", "leader"),
        ]

        for username, role in baseline_users:
            conn.execute(
                """
                INSERT OR IGNORE INTO users(username, role, enabled, password)
                VALUES (?, ?, 1, '')
                """,
                (username, role),
            )


