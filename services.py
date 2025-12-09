import csv
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re

import numpy as np
import pandas as pd

from database import _connect


def _dict_cursor(conn: sqlite3.Connection) -> sqlite3.Connection:
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# Parent/Consent table init
# =========================
def _ensure_parent_tables() -> None:
    """Create parent-related tables if they don't exist. Safe to call multiple times."""
    with _connect() as conn:
        # Parent ↔ Camper linking
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS parent_campers (
                parent_id INTEGER NOT NULL,
                camper_id INTEGER NOT NULL,
                UNIQUE(parent_id, camper_id)
            );
            """
        )
        # Parent consent per camper per camp
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS parent_consents (
                parent_id INTEGER NOT NULL,
                camper_id INTEGER NOT NULL,
                camp_id   INTEGER NOT NULL,
                consent   INTEGER NOT NULL DEFAULT 0,
                notes     TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(parent_id, camper_id, camp_id)
            );
            """
        )
        # Parent feedback per camper per camp (free text, many entries allowed)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS parent_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER NOT NULL,
                camper_id INTEGER NOT NULL,
                camp_id   INTEGER NOT NULL,
                feedback  TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


def _ensure_parent_role_allowed() -> None:
    """Rebuild users table role CHECK to include 'parent' if missing."""
    with _dict_cursor(_connect()) as conn_ro:
        row = conn_ro.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='users';"
        ).fetchone()
        sql = row["sql"] if row else ""
    if "CHECK (role IN ('admin','coordinator','leader'))" in (sql or "") and "parent" not in sql:
        with _connect() as conn:
            conn.execute("PRAGMA foreign_keys=OFF;")
            conn.execute("BEGIN;")
            try:
                conn.execute("ALTER TABLE users RENAME TO users_old;")
                conn.execute(
                    """
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY,
                        username TEXT NOT NULL UNIQUE,
                        role TEXT NOT NULL CHECK (role IN ('admin','coordinator','leader','parent')),
                        enabled INTEGER NOT NULL DEFAULT 1,
                        password TEXT NOT NULL DEFAULT ''
                    );
                    """
                )
                conn.execute(
                    "INSERT INTO users(id, username, role, enabled, password) SELECT id, username, role, enabled, password FROM users_old;"
                )
                conn.execute("DROP TABLE users_old;")
                conn.execute("COMMIT;")
            except Exception:
                conn.execute("ROLLBACK;")
                raise
            finally:
                conn.execute("PRAGMA foreign_keys=ON;")


# =========================
# UK phone (+44) utilities
# =========================
_UK_FORMATTED_RE = re.compile(r"^\+44\s\d{4}\s\d{6}$")  # +44 XXXX XXXXXX (10 digits after +44, grouped 4+6)
_UK_COMPACT_RE = re.compile(r"^\+44\d{10}$")  # +44XXXXXXXXXX (10 digits after +44)


def normalize_uk_phone_to_formatted(value: str) -> Optional[str]:
    """Normalize a UK phone to '+44 XXXX XXXXXX' or return None if invalid.
    
    Accepts either '+44XXXXXXXXXX' (compact, 10 digits) or '+44 XXXX XXXXXX' (formatted).
    Any other shape returns None.
    """
    s = (value or "").strip()
    if not s:
        return None
    if _UK_FORMATTED_RE.fullmatch(s):
        return s
    # Strip spaces/dashes for compact check
    compact = s.replace(" ", "").replace("-", "")
    if _UK_COMPACT_RE.fullmatch(compact):
        digits = compact[3:]  # 10 digits
        return f"+44 {digits[:4]} {digits[4:]}"  # 4 + 6 grouping
    return None


def normalize_uk_phone_to_compact(value: str) -> Optional[str]:
    """Normalize a UK phone to '+44XXXXXXXXXX' (no spaces) or None if invalid."""
    s = (value or "").strip()
    if not s:
        return None
    if _UK_COMPACT_RE.fullmatch(s.replace(" ", "").replace("-", "")):
        return s.replace(" ", "").replace("-", "")
    if _UK_FORMATTED_RE.fullmatch(s):
        # Convert formatted to compact
        return s.replace(" ", "")
    return None


def is_valid_uk_phone(value: str) -> bool:
    """True if value is a valid UK number in '+44XXXXXXXXXX' or '+44 XXXX XXXXXX' form."""
    return normalize_uk_phone_to_formatted(value) is not None


def normalize_all_camper_phones() -> Dict[str, int]:
    """Normalize all campers.emergency_contact to '+44 XXXX XXXXXX' when possible.
    
    Rules:
    - If value contains local UK '0' + 10 digits, convert to +44 + last 10 digits.
    - If value contains '44' + 10 digits, prefix '+' and format.
    - If value contains '+44' + 10 digits (any formatting), normalize grouping to 4+6.
    - Otherwise leave unchanged and count as invalid.
    
    Returns counters: {'updated': n, 'unchanged': n, 'invalid': n}
    """
    counters: Dict[str, int] = {"updated": 0, "unchanged": 0, "invalid": 0}
    with _dict_cursor(_connect()) as conn:
        rows = conn.execute("SELECT id, emergency_contact FROM campers;").fetchall()
    with _connect() as conn_w:
        for r in rows:
            camper_id = int(r["id"])
            raw = (r["emergency_contact"] or "").strip()
            if not raw:
                counters["unchanged"] += 1
                continue
            # Clean variants
            digits_only = re.sub(r"\D", "", raw)
            compact = raw.replace(" ", "").replace("-", "")
            candidate_compact = None
            # +44XXXXXXXXXX (keep as-is compact)
            if _UK_COMPACT_RE.fullmatch(compact):
                candidate_compact = compact
            # 44XXXXXXXXXX (missing '+')
            elif re.fullmatch(r"44\d{10}", digits_only):
                candidate_compact = "+" + digits_only
            # 0XXXXXXXXXX local UK → +44XXXXXXXXXX
            elif re.fullmatch(r"0\d{10}", digits_only):
                candidate_compact = "+44" + digits_only[1:]
            # Already formatted but wrong grouping or spaces
            else:
                # Attempt to extract +44 and exactly 10 digits after anywhere
                m = re.search(r"\+?44\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)", raw)
                if m:
                    ten = "".join(m.groups())
                    candidate_compact = "+44" + ten
            normalized = normalize_uk_phone_to_formatted(candidate_compact or raw)
            if not normalized:
                counters["invalid"] += 1
                continue
            if normalized != raw:
                conn_w.execute(
                    "UPDATE campers SET emergency_contact = ? WHERE id = ?;",
                    (normalized, camper_id),
                )
                counters["updated"] += 1
            else:
                counters["unchanged"] += 1
    return counters


def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Return user dict if credentials are valid and user is enabled, else None.

    Note 1: passwords are empty strings for all users in this coursework.
    """
    with _dict_cursor(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?;",
            (username,),
        ).fetchone()
        if row is None:
            return None
        if row["enabled"] != 1:
            return None
        if (row["password"] or "") != (password or ""):
            return None
        return dict(row)


def list_messages(limit: int = 100) -> List[Dict[str, Any]]:
    with _dict_cursor(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT m.id, m.content, m.created_at,
                   u.username AS sender_username, m.sender_user_id
            FROM messages m
            LEFT JOIN users u ON u.id = m.sender_user_id
            ORDER BY m.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def post_message(sender_user_id: Optional[int], content: str) -> None:
    cleaned = (content or "").strip()
    if not cleaned:
        return
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages(sender_user_id, content) VALUES (?, ?);",
            (sender_user_id, cleaned),
        )


def list_messages_lines(limit: int = 100) -> List[str]:
    lines = []
    for row in list_messages(limit):
        sender = row.get("sender_username") or "(system)"
        created = row.get("created_at") or ""
        content = row.get("content") or ""
        lines.append(f"[{created}] {sender}: {content}")
    return list(reversed(lines))


def effective_daily_stock_for_camp(camp_id: int) -> int:
    """Compute base + sum(top-ups) for a camp."""
    with _dict_cursor(_connect()) as conn:
        base_row = conn.execute(
            "SELECT daily_food_units_planned FROM camps WHERE id = ?;",
            (camp_id,),
        ).fetchone()
        if base_row is None:
            return 0
        base = int(base_row["daily_food_units_planned"]) or 0
        delta = conn.execute(
            "SELECT COALESCE(SUM(delta_daily_units),0) AS s FROM stock_topups WHERE camp_id = ?;",
            (camp_id,),
        ).fetchone()["s"]
        return base + int(delta or 0)


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    with _dict_cursor(_connect()) as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?;", (user_id,)).fetchone()
        return dict(row) if row else None


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    with _dict_cursor(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?;",
            (username,),
        ).fetchone()
        return dict(row) if row else None


def list_users() -> List[Dict[str, Any]]:
    with _dict_cursor(_connect()) as conn:
        rows = conn.execute(
            "SELECT id, username, role, enabled FROM users ORDER BY role, username;"
        ).fetchall()
        return [dict(r) for r in rows]


def list_campers() -> List[Dict[str, Any]]:
    """List all campers with core fields."""
    with _dict_cursor(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT id, first_name, last_name, dob, emergency_contact
            FROM campers
            ORDER BY LOWER(last_name), LOWER(first_name);
            """
        ).fetchall()
        return [dict(r) for r in rows]

def count_roles_total() -> Dict[str, int]:
    """Return total counts per role across all users (enabled and disabled). Includes 'parent' if present."""
    with _dict_cursor(_connect()) as conn:
        rows = conn.execute(
            "SELECT role, COUNT(*) as c FROM users GROUP BY role;"
        ).fetchall()
    counts: Dict[str, int] = {}
    for r in rows:
        counts[str(r["role"])] = int(r["c"])
    # Ensure standard roles present
    for role in ("admin", "coordinator", "leader", "parent"):
        counts.setdefault(role, 0)
    return counts

def count_roles_enabled() -> Dict[str, int]:
    """Return counts per role for enabled users only. Includes 'parent' if present."""
    with _dict_cursor(_connect()) as conn:
        rows = conn.execute(
            "SELECT role, COUNT(*) as c FROM users WHERE enabled = 1 GROUP BY role;"
        ).fetchall()
    counts: Dict[str, int] = {}
    for r in rows:
        counts[str(r["role"])] = int(r["c"])
    for role in ("admin", "coordinator", "leader", "parent"):
        counts.setdefault(role, 0)
    return counts

def create_user(username: str, role: str) -> bool:
    try:
        if role == "parent":
            _ensure_parent_role_allowed()
        with _connect() as conn:
            conn.execute(
                "INSERT INTO users(username, role, enabled, password) VALUES (?, ?, 1, '');",
                (username.strip(), role),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def update_user_enabled(user_id: int, enabled: bool) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET enabled = ? WHERE id = ?;",
            (1 if enabled else 0, user_id),
        )


def update_user_username(user_id: int, new_username: str) -> bool:
    try:
        with _connect() as conn:
            conn.execute(
                "UPDATE users SET username = ? WHERE id = ?;",
                (new_username.strip(), user_id),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def delete_user(user_id: int) -> bool:
    try:
        # Defense-in-depth: prevent deleting the sole remaining leader
        with _dict_cursor(_connect()) as conn_ro:
            row = conn_ro.execute("SELECT role FROM users WHERE id = ?;", (user_id,)).fetchone()
            if row is None:
                return False
            role = str(row["role"])
            if role == "leader":
                count_row = conn_ro.execute(
                    "SELECT COUNT(*) AS c FROM users WHERE role = 'leader';"
                ).fetchone()
                if int(count_row["c"] or 0) <= 1:
                    # Block deletion if this is the last leader account
                    return False
        with _connect() as conn:
            conn.execute("DELETE FROM users WHERE id = ?;", (user_id,))
        return True
    except sqlite3.IntegrityError:
        return False


def get_setting(key: str, default: str = "") -> str:
    with _dict_cursor(_connect()) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?;", (key,)).fetchone()
        if row is None:
            return default
        return row["value"]


def set_setting(key: str, value: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value;",
            (key, value),
        )


# -------------------------
# Camper update operations
# -------------------------
def update_camper(camper_id: int, first_name: str, last_name: str, dob: str, emergency_contact: str) -> bool:
    """Update core camper fields. UI should validate formats prior to calling this.
    
    Returns True if a row was updated.
    """
    try:
        with _connect() as conn:
            res = conn.execute(
                """
                UPDATE campers
                SET first_name = ?, last_name = ?, dob = ?, emergency_contact = ?
                WHERE id = ?;
                """,
                (first_name.strip(), last_name.strip(), dob.strip(), emergency_contact.strip(), camper_id),
            )
        return res.rowcount > 0
    except sqlite3.IntegrityError:
        return False


def get_daily_pay_rate() -> str:
    return get_setting("daily_pay_rate", "0")


def set_daily_pay_rate(value: str) -> None:
    set_setting("daily_pay_rate", value)


def get_camp_summary_df() -> pd.DataFrame:
    with _connect() as conn:
        df = pd.read_sql_query(
            """
            WITH camp_totals AS (
                SELECT camp_id, COUNT(*) AS campers_count, SUM(food_units_per_day) AS campers_food_units
                FROM camp_campers
                GROUP BY camp_id
            ),
            assignment_totals AS (
                SELECT camp_id, COUNT(DISTINCT leader_user_id) AS leaders_count
                FROM leader_assignments
                GROUP BY camp_id
            ),
            leader_names AS (
                SELECT la.camp_id, GROUP_CONCAT(u.username, ', ') AS leader_list
                FROM leader_assignments la
                JOIN users u ON u.id = la.leader_user_id
                GROUP BY la.camp_id
            ),
            activity_totals AS (
                SELECT camp_id, COUNT(*) AS activities_count
                FROM activities
                GROUP BY camp_id
            ),
            topups AS (
                SELECT camp_id, SUM(delta_daily_units) AS topup_delta
                FROM stock_topups
                GROUP BY camp_id
            ),
            activity_dates AS (
                SELECT DISTINCT camp_id, date
                FROM activities
            )
            SELECT
                c.id,
                c.name,
                c.location,
                c.area,
                c.type,
                c.start_date,
                c.end_date,
                c.daily_food_units_planned,
                c.default_food_units_per_camper_per_day,
                COALESCE(ct.campers_count, 0) AS campers_count,
                COALESCE(ct.campers_food_units, 0) AS campers_food_units,
                COALESCE(at.activities_count, 0) AS activities_count,
                COALESCE(lt.leaders_count, 0) AS leaders_count,
                COALESCE(tp.topup_delta, 0) AS topup_delta,
                MIN(ad.date) AS first_activity_date,
                MAX(ad.date) AS last_activity_date,
                COALESCE(ln.leader_list, '') AS leader_names
            FROM camps c
            LEFT JOIN camp_totals ct ON c.id = ct.camp_id
            LEFT JOIN activity_totals at ON c.id = at.camp_id
            LEFT JOIN assignment_totals lt ON c.id = lt.camp_id
            LEFT JOIN topups tp ON c.id = tp.camp_id
            LEFT JOIN activity_dates ad ON c.id = ad.camp_id
            LEFT JOIN leader_names ln ON c.id = ln.camp_id
            GROUP BY c.id
            ORDER BY c.start_date, c.name;
            """,
            conn,
        )

    if df.empty:
        return pd.DataFrame(
            columns=[
                "id",
                "name",
                "location",
                "area",
                "type",
                "start_date",
                "end_date",
                "daily_food_units_planned",
                "default_food_units_per_camper_per_day",
                "campers_count",
                "campers_food_units",
                "activities_count",
                "leaders_count",
                "topup_delta",
                "effective_daily_food",
                "required_daily_food",
                "food_gap",
            ]
        )

    df = df.infer_objects(copy=False)
    for col in ["campers_count", "campers_food_units", "activities_count", "leaders_count", "topup_delta"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    for col in ["daily_food_units_planned", "default_food_units_per_camper_per_day"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    df["effective_daily_food"] = df["daily_food_units_planned"] + df["topup_delta"]

    df["required_daily_food"] = np.where(
        df["campers_food_units"] > 0,
        df["campers_food_units"],
        df["default_food_units_per_camper_per_day"] * df["campers_count"],
    ).astype(int)

    df["food_gap"] = (df["effective_daily_food"] - df["required_daily_food"]).astype(int)
    df["area"] = df["area"].fillna("")

    return df


def compute_day_by_day_food_usage(camp_id: int) -> List[Dict[str, Any]]:
    camp = get_camp(camp_id)
    if not camp:
        return []

    start = pd.to_datetime(camp["start_date"])
    end = pd.to_datetime(camp["end_date"])
    dates = pd.date_range(start, end, freq="D")

    # Cache top-up sum once instead of querying per day
    topup_sum = sum(row["delta_daily_units"] for row in list_stock_topups(camp_id))
    planned_daily = int(camp["daily_food_units_planned"]) + int(topup_sum)

    with _connect() as conn:
        campers_df = pd.read_sql_query(
            """
            SELECT camp_id, camper_id, food_units_per_day
            FROM camp_campers
            WHERE camp_id = ?
            """,
            conn,
            params=(camp_id,),
        )

        activity_df = pd.read_sql_query(
            """
            SELECT a.date, ca.camper_id, cc.food_units_per_day
            FROM activities a
            JOIN camper_activity ca ON ca.activity_id = a.id
            JOIN camp_campers cc ON cc.camper_id = ca.camper_id AND cc.camp_id = a.camp_id
            WHERE a.camp_id = ?
            """,
            conn,
            params=(camp_id,),
        )

    records = []
    for date in dates:
        date_str = date.strftime("%Y-%m-%d")
        day_activities = activity_df[activity_df["date"] == date_str]
        if not day_activities.empty:
            required = int(day_activities["food_units_per_day"].sum())
        else:
            required = int(campers_df["food_units_per_day"].sum())

        records.append(
            {
                "date": date_str,
                "required": required,
                "planned": planned_daily,
                "gap": planned_daily - required,
            }
        )

    return records


def get_food_shortage_alerts() -> List[Dict[str, Any]]:
    alerts = []
    for camp in list_camps():
        per_day = compute_day_by_day_food_usage(camp["id"])
        shortages = [day for day in per_day if day["gap"] < 0]
        if shortages:
            alerts.append(
                {
                    "camp_id": camp["id"],
                    "camp_name": camp["name"],
                    "shortages": shortages,
                }
            )
    return alerts


def compute_leader_pay_report() -> List[Dict[str, Any]]:
    df = get_camp_summary_df()
    if df.empty:
        return []

    with _connect() as conn:
        assignments = pd.read_sql_query(
            """
            SELECT la.leader_user_id, la.camp_id, c.start_date, c.end_date
            FROM leader_assignments la
            JOIN camps c ON c.id = la.camp_id;
            """,
            conn,
        )

    if assignments.empty:
        return []

    # Parse dates robustly: support both DD-MM-YYYY and YYYY-MM-DD inputs
    assignments["start_date"] = pd.to_datetime(assignments["start_date"], dayfirst=True, errors="coerce")
    assignments["end_date"] = pd.to_datetime(assignments["end_date"], dayfirst=True, errors="coerce")
    # Drop any rows with invalid dates to avoid downstream crashes
    assignments = assignments.dropna(subset=["start_date", "end_date"])
    # Compute assignment days; ensure strictly non-negative for pay purposes
    days_delta = (assignments["end_date"] - assignments["start_date"]).dt.days + 1
    # If end < start, treat as absolute duration; clamp minimum at 0
    assignments["days"] = days_delta.abs().clip(lower=0)

    daily_rate = float(get_daily_pay_rate() or "0")

    results = []
    for leader_id, group in assignments.groupby("leader_user_id"):
        per_camp = []
        total = 0.0
        for _, row in group.iterrows():
            camp_record = df[df["id"] == row["camp_id"]].iloc[0]
            # Always compute non-negative pay
            pay = daily_rate * max(0, int(row["days"]))
            total += pay
            per_camp.append(
                {
                    "camp_id": int(row["camp_id"]),
                    "camp_name": camp_record["name"],
                    "days": max(0, int(row["days"])),
                    "pay": pay,
                }
            )

        results.append(
            {
                "leader_user_id": int(leader_id),
                "total_pay": total,
                "per_camp": per_camp,
            }
        )

    return results


def get_leader_pay_summary(leader_user_id: int) -> Dict[str, Any]:
    summaries = compute_leader_pay_report()
    for summary in summaries:
        if summary["leader_user_id"] == leader_user_id:
            return summary
    return {"leader_user_id": leader_user_id, "total_pay": 0.0, "per_camp": []}


def get_leader_statistics(leader_user_id: int) -> List[Dict[str, Any]]:
    """Get participation, food usage, and report stats for all camps led by this leader."""
    assignments = list_leader_assignments(leader_user_id)
    
    stats = []
    for assignment in assignments:
        camp_id = assignment["camp_id"]
        
        # Get campers count
        campers = list_camp_campers(camp_id)
        total_campers = len(campers)
        
        # Get activities and participation
        activities = list_camp_activities(camp_id)
        total_activities = len(activities)
        
        # Count unique campers who attended at least one activity
        attending_campers = set()
        for activity in activities:
            participants = list_activity_campers(activity["id"])
            attending_campers.update(p["id"] for p in participants)
        
        campers_attending = len(attending_campers)
        participation_rate = (campers_attending / total_campers * 100) if total_campers > 0 else 0
        
        # Calculate total food allocated
        total_food_allocated = sum(c["food_units_per_day"] for c in campers)
        
        # Get camp details for duration
        camp = get_camp(camp_id)
        if camp:
            # Parse camp dates robustly; handle invalid values
            start = pd.to_datetime(camp["start_date"], dayfirst=True, errors="coerce")
            end = pd.to_datetime(camp["end_date"], dayfirst=True, errors="coerce")
            if pd.isna(start) or pd.isna(end):
                camp_days = 0
                total_food_used = 0
            else:
                camp_days = (end - start).days + 1
                total_food_used = total_food_allocated * camp_days
        else:
            camp_days = 0
            total_food_used = 0
        
        # Count daily reports (incident reports)
        reports = list_daily_reports(leader_user_id, camp_id)
        incident_report_count = len(reports)
        
        stats.append({
            "camp_id": camp_id,
            "camp_name": assignment["name"],
            "camp_area": assignment.get("area", ""),
            "camp_days": camp_days,
            "total_campers": total_campers,
            "campers_attending": campers_attending,
            "participation_rate": round(participation_rate, 1),
            "total_activities": total_activities,
            "food_allocated_per_day": total_food_allocated,
            "total_food_used": total_food_used,
            "incident_report_count": incident_report_count,
        })
    
    return stats


def list_camps() -> List[Dict[str, Any]]:
    df = get_camp_summary_df()
    if df.empty:
        return []
    return df.to_dict("records")


def create_camp(
    name: str,
    location: str,
    area: str,
    camp_type: str,
    start_date: str,
    end_date: str,
    daily_food_units_planned: int,
    default_food_units_per_camper_per_day: int,
) -> bool:
    try:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO camps(
                    name, location, area, type, start_date, end_date,
                    daily_food_units_planned, default_food_units_per_camper_per_day
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    name.strip(),
                    location.strip(),
                    area.strip(),
                    camp_type,
                    start_date,
                    end_date,
                    daily_food_units_planned,
                    default_food_units_per_camper_per_day,
                ),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def update_camp(
    camp_id: int,
    name: str,
    location: str,
    area: str,
    camp_type: str,
    start_date: str,
    end_date: str,
    daily_food_units_planned: int,
    default_food_units_per_camper_per_day: int,
) -> bool:
    try:
        with _connect() as conn:
            conn.execute(
                """
                UPDATE camps
                SET name = ?, location = ?, area = ?, type = ?, start_date = ?, end_date = ?,
                    daily_food_units_planned = ?, default_food_units_per_camper_per_day = ?
                WHERE id = ?;
                """,
                (
                    name.strip(),
                    location.strip(),
                    area.strip(),
                    camp_type,
                    start_date,
                    end_date,
                    daily_food_units_planned,
                    default_food_units_per_camper_per_day,
                    camp_id,
                ),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def delete_camp(camp_id: int) -> bool:
    try:
        with _connect() as conn:
            conn.execute("DELETE FROM camps WHERE id = ?;", (camp_id,))
        return True
    except sqlite3.IntegrityError:
        return False


def add_stock_topup(camp_id: int, delta_daily_units: int) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO stock_topups(camp_id, delta_daily_units) VALUES (?, ?);",
            (camp_id, delta_daily_units),
        )


def list_stock_topups(camp_id: int) -> List[Dict[str, Any]]:
    with _dict_cursor(_connect()) as conn:
        rows = conn.execute(
            "SELECT id, created_at, delta_daily_units FROM stock_topups WHERE camp_id = ? ORDER BY id DESC;",
            (camp_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_coordinator_dashboard_stats() -> Dict[str, Any]:
    df = get_camp_summary_df()
    if df.empty:
        return {
            "summary_records": [],
            "campers_per_camp": [],
            "leaders_per_camp": [],
            "activities_per_camp": [],
            "camps_by_area": [],
            "food_comparison": [],
        }

    summary_records = df.to_dict("records")

    campers_per_camp = list(
        zip(df["name"], df["campers_count"].astype(int))
    )
    leaders_per_camp = list(
        zip(df["name"], df["leaders_count"].astype(int))
    )
    activities_per_camp = list(
        zip(df["name"], df["activities_count"].astype(int))
    )

    area_labels = df["area"].fillna("").apply(lambda val: val.strip() if val and val.strip() else "Unspecified")
    area_counts = (
        df.assign(area_label=area_labels)
        .groupby("area_label")["id"]
        .count()
        .sort_values(ascending=False)
    )
    camps_by_area = list(area_counts.items())

    food_comparison = [
        {
            "label": row["name"],
            "effective": int(row["effective_daily_food"]),
            "required": int(row["required_daily_food"]),
        }
        for row in summary_records
    ]

    return {
        "summary_records": summary_records,
        "campers_per_camp": campers_per_camp,
        "leaders_per_camp": leaders_per_camp,
        "activities_per_camp": activities_per_camp,
        "camps_by_area": camps_by_area,
        "food_comparison": food_comparison,
    }


def list_leader_assignments(leader_user_id: int) -> List[Dict[str, Any]]:
    with _dict_cursor(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT la.id, la.camp_id, c.name, c.start_date, c.end_date, c.location, c.area
            FROM leader_assignments la
            JOIN camps c ON la.camp_id = c.id
            WHERE la.leader_user_id = ?
            ORDER BY c.start_date;
            """,
            (leader_user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def list_available_camps_for_leader(leader_user_id: int) -> List[Dict[str, Any]]:
    assignments = list_leader_assignments(leader_user_id)
    assigned_ranges = [(
        pd.to_datetime(rec["start_date"]),
        pd.to_datetime(rec["end_date"])
    ) for rec in assignments]

    df = get_camp_summary_df()
    if df.empty:
        return []

    available = []
    for _, camp in df.iterrows():
        if camp["id"] in {rec["camp_id"] for rec in assignments}:
            continue
        camp_start = pd.to_datetime(camp["start_date"])
        camp_end = pd.to_datetime(camp["end_date"])
        conflict = False
        for start, end in assigned_ranges:
            if not (camp_end < start or camp_start > end):
                conflict = True
                break
        if not conflict:
            available.append(camp.to_dict())

    return available


def assign_leader_to_camp(leader_user_id: int, camp_id: int) -> bool:
    available_camps = list_available_camps_for_leader(leader_user_id)
    if all(camp["id"] != camp_id for camp in available_camps):
        return False
    with _connect() as conn:
        conn.execute(
            "INSERT INTO leader_assignments(leader_user_id, camp_id) VALUES (?, ?);",
            (leader_user_id, camp_id),
        )
    return True


def remove_leader_assignment(assignment_id: int, leader_user_id: int) -> bool:
    with _connect() as conn:
        res = conn.execute(
            "DELETE FROM leader_assignments WHERE id = ? AND leader_user_id = ?;",
            (assignment_id, leader_user_id),
        )
    return res.rowcount > 0


def get_camp(camp_id: int) -> Optional[Dict[str, Any]]:
    with _dict_cursor(_connect()) as conn:
        row = conn.execute("SELECT * FROM camps WHERE id = ?;", (camp_id,)).fetchone()
        return dict(row) if row else None


def list_camp_campers(camp_id: int) -> List[Dict[str, Any]]:
    with _dict_cursor(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT
                cc.id,                       -- camp_campers row id (kept as 'id')
                cam.id AS camper_id,         -- underlying campers.id
                cc.food_units_per_day,
                cam.first_name,
                cam.last_name,
                cam.dob,
                cam.emergency_contact
            FROM camp_campers cc
            JOIN campers cam ON cam.id = cc.camper_id
            WHERE cc.camp_id = ?
            ORDER BY LOWER(cam.last_name), LOWER(cam.first_name);
            """,
            (camp_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# =========================
# Parent / Consent services
# =========================
def _migrate_parent_campers_fix_users_fk() -> None:
    """Fix legacy parent_campers referencing 'users_old' and unify parent column to 'parent_id'."""
    with _dict_cursor(_connect()) as conn_ro:
        # Check if table exists
        tbl = conn_ro.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='parent_campers';"
        ).fetchone()
        if not tbl:
            return
        # Gather columns and foreign keys
        cols = [r["name"] for r in conn_ro.execute("PRAGMA table_info(parent_campers);").fetchall()]
        fks = conn_ro.execute("PRAGMA foreign_key_list(parent_campers);").fetchall()
        fk_tables = [fk[2] if isinstance(fk, tuple) else fk["table"] for fk in fks] if fks else []
    needs_fk_fix = any(t == "users_old" for t in fk_tables)
    needs_col_fix = ("parent_user_id" in cols) and ("parent_id" not in cols)
    if not (needs_fk_fix or needs_col_fix):
        return
    with _connect() as conn:
        conn.execute("PRAGMA foreign_keys=OFF;")
        conn.execute("BEGIN;")
        try:
            conn.execute("ALTER TABLE parent_campers RENAME TO parent_campers_old;")
            conn.execute(
                """
                CREATE TABLE parent_campers (
                    id INTEGER PRIMARY KEY,
                    parent_id INTEGER NOT NULL,
                    camper_id INTEGER NOT NULL,
                    UNIQUE(parent_id, camper_id),
                    FOREIGN KEY (parent_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (camper_id) REFERENCES campers(id) ON DELETE CASCADE
                );
                """
            )
            # Copy data from legacy columns
            legacy_cols = [r[1] for r in conn.execute("PRAGMA table_info(parent_campers_old);").fetchall()]
            if "parent_id" in legacy_cols:
                conn.execute(
                    "INSERT OR IGNORE INTO parent_campers(parent_id, camper_id) SELECT parent_id, camper_id FROM parent_campers_old;"
                )
            elif "parent_user_id" in legacy_cols:
                conn.execute(
                    "INSERT OR IGNORE INTO parent_campers(parent_id, camper_id) SELECT parent_user_id, camper_id FROM parent_campers_old;"
                )
            conn.execute("DROP TABLE parent_campers_old;")
            conn.execute("COMMIT;")
        except Exception:
            conn.execute("ROLLBACK;")
            raise
        finally:
            conn.execute("PRAGMA foreign_keys=ON;")

def _parent_campers_parent_col() -> str:
    """Return the actual parent column name in parent_campers ('parent_id' or legacy 'parent_user_id')."""
    try:
        with _dict_cursor(_connect()) as conn:
            cols = [r["name"] for r in conn.execute("PRAGMA table_info(parent_campers);").fetchall()]
        if "parent_id" in cols:
            return "parent_id"
        if "parent_user_id" in cols:
            return "parent_user_id"
    except Exception:
        pass
    return "parent_id"

def add_parent_camper(parent_id: int, camper_id: int) -> bool:
    """Link a parent user to a camper (idempotent)."""
    _ensure_parent_tables()
    _migrate_parent_campers_fix_users_fk()
    try:
        col = _parent_campers_parent_col()
        with _connect() as conn:
            conn.execute(
                f"INSERT OR IGNORE INTO parent_campers({col}, camper_id) VALUES (?, ?);",
                (parent_id, camper_id),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def list_parent_campers(parent_id: int) -> List[Dict[str, Any]]:
    """Return campers linked to the given parent user."""
    _ensure_parent_tables()
    _migrate_parent_campers_fix_users_fk()
    col = _parent_campers_parent_col()
    with _dict_cursor(_connect()) as conn:
        rows = conn.execute(
            f"""
            SELECT c.id, c.first_name, c.last_name, c.dob, c.emergency_contact
            FROM parent_campers pc
            JOIN campers c ON c.id = pc.camper_id
            WHERE pc.{col} = ?
            ORDER BY LOWER(c.last_name), LOWER(c.first_name);
            """,
            (parent_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def list_camps_for_camper(camper_id: int) -> List[Dict[str, Any]]:
    """List camps a camper is enrolled in."""
    with _dict_cursor(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.name, c.location, c.start_date, c.end_date, c.type
            FROM camp_campers cc
            JOIN camps c ON c.id = cc.camp_id
            WHERE cc.camper_id = ?
            ORDER BY c.start_date, c.name;
            """,
            (camper_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def list_camps_for_parent(parent_id: int) -> List[Dict[str, Any]]:
    """List unique camps associated with any camper linked to a parent."""
    _ensure_parent_tables()
    _migrate_parent_campers_fix_users_fk()
    col = _parent_campers_parent_col()
    with _dict_cursor(_connect()) as conn:
        rows = conn.execute(
            f"""
            SELECT DISTINCT c.id, c.name, c.location, c.start_date, c.end_date, c.type
            FROM parent_campers pc
            JOIN camp_campers cc ON cc.camper_id = pc.camper_id
            JOIN camps c ON c.id = cc.camp_id
            WHERE pc.{col} = ?
            ORDER BY c.start_date, c.name;
            """,
            (parent_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_consent_form(parent_id: int, camper_id: int, camp_id: int) -> Optional[Dict[str, Any]]:
    """Get the stored consent row for parent/camper/camp, if any."""
    _ensure_parent_tables()
    with _dict_cursor(_connect()) as conn:
        row = conn.execute(
            """
            SELECT parent_id, camper_id, camp_id, consent, notes, updated_at
            FROM parent_consents
            WHERE parent_id = ? AND camper_id = ? AND camp_id = ?;
            """,
            (parent_id, camper_id, camp_id),
        ).fetchone()
        return dict(row) if row else None


def submit_consent_form(parent_user_id: int, camper_id: int, camp_id: int, consent: bool, notes: str) -> None:
    """Upsert a yes/no consent with optional notes."""
    _ensure_parent_tables()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO parent_consents(parent_id, camper_id, camp_id, consent, notes)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(parent_id, camper_id, camp_id)
            DO UPDATE SET consent = excluded.consent, notes = excluded.notes, updated_at = CURRENT_TIMESTAMP;
            """,
            (parent_user_id, camper_id, camp_id, 1 if consent else 0, (notes or "").strip()),
        )


def list_daily_reports_for_camper(camper_id: int) -> List[Dict[str, Any]]:
    """List daily reports for any camp the camper is in, showing leader username."""
    with _dict_cursor(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT dr.date, u.username AS leader, dr.notes
            FROM camp_campers cc
            JOIN daily_reports dr ON dr.camp_id = cc.camp_id
            LEFT JOIN users u ON u.id = dr.leader_user_id
            WHERE cc.camper_id = ?
            ORDER BY dr.date DESC;
            """,
            (camper_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def submit_feedback(parent_user_id: int, camper_id: int, camp_id: int, feedback: str) -> None:
    """Record free‑text feedback from a parent for a specific camper and camp."""
    _ensure_parent_tables()
    text = (feedback or "").strip()
    if not text:
        return
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO parent_feedback(parent_id, camper_id, camp_id, feedback)
            VALUES (?, ?, ?, ?);
            """,
            (parent_user_id, camper_id, camp_id, text),
        )


def update_camp_camper_food(camp_camper_id: int, food_units_per_day: int) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE camp_campers SET food_units_per_day = ? WHERE id = ?;",
            (food_units_per_day, camp_camper_id),
        )


def list_camp_activities(camp_id: int) -> List[Dict[str, Any]]:
    with _dict_cursor(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT id, name, date
            FROM activities
            WHERE camp_id = ?
            ORDER BY date, name;
            """,
            (camp_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def create_activity(camp_id: int, name: str, date: str) -> bool:
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO activities(camp_id, name, date) VALUES (?, ?, ?);",
                (camp_id, name.strip(), date),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def delete_activity(activity_id: int, camp_id: int) -> bool:
    with _connect() as conn:
        res = conn.execute(
            "DELETE FROM activities WHERE id = ? AND camp_id = ?;",
            (activity_id, camp_id),
        )
    return res.rowcount > 0


def update_activity(activity_id: int, camp_id: int, name: str, date: str) -> bool:
    """Update an activity's name and date; returns True if a row was changed."""
    try:
        with _connect() as conn:
            res = conn.execute(
                """
                UPDATE activities
                SET name = ?, date = ?
                WHERE id = ? AND camp_id = ?;
                """,
                (name.strip(), date, activity_id, camp_id),
            )
        return res.rowcount > 0
    except sqlite3.IntegrityError:
        return False


def assign_campers_to_activity(activity_id: int, camper_ids: List[int]) -> None:
    with _connect() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO camper_activity(activity_id, camper_id) VALUES (?, ?);",
            [(activity_id, camper_id) for camper_id in camper_ids],
        )


def list_activity_campers(activity_id: int) -> List[Dict[str, Any]]:
    with _dict_cursor(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT cam.id, cam.first_name, cam.last_name
            FROM camper_activity ca
            JOIN campers cam ON cam.id = ca.camper_id
            WHERE ca.activity_id = ?
            ORDER BY LOWER(cam.last_name), LOWER(cam.first_name);
            """,
            (activity_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def list_daily_reports(leader_user_id: int, camp_id: int) -> List[Dict[str, Any]]:
    with _dict_cursor(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT id, date, notes
            FROM daily_reports
            WHERE leader_user_id = ? AND camp_id = ?
            ORDER BY date DESC;
            """,
            (leader_user_id, camp_id),
        ).fetchall()
        return [dict(r) for r in rows]


def save_daily_report(leader_user_id: int, camp_id: int, date: str, notes: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO daily_reports(camp_id, leader_user_id, date, notes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(date, camp_id, leader_user_id) DO UPDATE SET notes = excluded.notes;
            """,
            (camp_id, leader_user_id, date, notes.strip()),
        )


def delete_daily_report(leader_user_id: int, camp_id: int, date: str) -> None:
    with _connect() as conn:
        conn.execute(
            "DELETE FROM daily_reports WHERE leader_user_id = ? AND camp_id = ? AND date = ?;",
            (leader_user_id, camp_id, date),
        )


def import_campers_from_csv(camp_id: int, file_path: str) -> Dict[str, Any]:
    camp = get_camp(camp_id)
    if camp is None:
        raise ValueError("Camp not found")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(file_path)

    with path.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        expected_header = {"first_name", "last_name", "dob", "emergency_contact"}
        if set(reader.fieldnames or []) != expected_header:
            raise ValueError("CSV header must be exactly first_name,last_name,dob,emergency_contact")

        rows = list(reader)

    unique_rows: Dict[Tuple[str, str, str], Dict[str, str]] = {}
    duplicates = 0
    for row in rows:
        key = (
            row["first_name"].strip(),
            row["last_name"].strip(),
            row["dob"].strip(),
        )
        if key in unique_rows:
            duplicates += 1
            continue
        unique_rows[key] = row

    created = 0
    linked = 0
    errors: List[str] = []

    def _find_camper(first_name: str, last_name: str, dob: str) -> Optional[int]:
        with _dict_cursor(_connect()) as conn:
            row = conn.execute(
                """
                SELECT id FROM campers
                WHERE LOWER(first_name) = LOWER(?) AND LOWER(last_name) = LOWER(?) AND dob = ?
                """,
                (first_name, last_name, dob),
            ).fetchone()
            return row["id"] if row else None

    default_food = int(camp.get("default_food_units_per_camper_per_day", 0) or 0)

    with _connect() as conn:
        for (first_name, last_name, dob), row in unique_rows.items():
            if not first_name or not last_name or not dob:
                errors.append(f"Invalid row missing data: {row}")
                continue

            camper_id = _find_camper(first_name, last_name, dob)
            if camper_id is None:
                cursor = conn.execute(
                    """
                    INSERT INTO campers(first_name, last_name, dob, emergency_contact)
                    VALUES (?, ?, ?, ?);
                    """,
                    (first_name, last_name, dob, row["emergency_contact"].strip()),
                )
                camper_id = cursor.lastrowid
                created += 1
            else:
                linked += 1

            conn.execute(
                """
                INSERT OR IGNORE INTO camp_campers(camp_id, camper_id, food_units_per_day)
                VALUES (?, ?, ?);
                """,
                (camp_id, camper_id, default_food),
            )

    preview_rows = list(unique_rows.values())[:10]
    return {
        "created": created,
        "linked": linked,
        "duplicates": duplicates,
        "errors": errors,
        "preview": preview_rows,
    }


