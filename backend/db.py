from __future__ import annotations

import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Any, Dict, List, Optional

from config.settings import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASSWORD
from backend.security import hash_password


def get_conn():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=RealDictCursor
    )
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            display_name VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            must_change_password BOOLEAN NOT NULL DEFAULT TRUE
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS patients (
            id SERIAL PRIMARY KEY,
            patient_id VARCHAR(255) UNIQUE NOT NULL,
            tracking_token VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP,
            source VARCHAR(50) NOT NULL,
            name VARCHAR(255) NOT NULL,
            age INTEGER,
            sex VARCHAR(50),
            pregnancy BOOLEAN NOT NULL DEFAULT FALSE,
            chief_complaint TEXT,
            symptoms_json TEXT,
            risk_factors_json TEXT,
            vitals_json TEXT,
            photo_meta_json TEXT,
            image_path TEXT,
            location_text TEXT,
            gps_lat REAL,
            gps_lon REAL,
            gps_accuracy REAL,
            emergency_phone VARCHAR(50),
            triage_json TEXT,
            status VARCHAR(50) NOT NULL DEFAULT 'NEW',
            reviewed_by VARCHAR(255),
            reviewed_at TIMESTAMP,
            notes TEXT DEFAULT '',
            video_recommended BOOLEAN NOT NULL DEFAULT FALSE,
            video_requested BOOLEAN NOT NULL DEFAULT FALSE,
            video_room_id VARCHAR(255) NOT NULL DEFAULT '',
            video_status VARCHAR(50) NOT NULL DEFAULT 'NONE',
            video_requested_at TIMESTAMP,
            video_joined_at TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS gps_updates (
            id SERIAL PRIMARY KEY,
            patient_id VARCHAR(255) NOT NULL,
            tracking_token VARCHAR(255) NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            accuracy REAL,
            updated_at TIMESTAMP NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS status_history (
            id SERIAL PRIMARY KEY,
            patient_id VARCHAR(255) NOT NULL,
            status VARCHAR(50) NOT NULL,
            note TEXT,
            changed_by VARCHAR(255),
            changed_at TIMESTAMP NOT NULL
        )
        """
    )
    # Backward-compatible migrations for an existing SQLite database.
    def ensure_column(table: str, column: str, ddl: str) -> None:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

    ensure_column("patients", "video_recommended", "INTEGER NOT NULL DEFAULT 0")
    ensure_column("patients", "video_requested", "INTEGER NOT NULL DEFAULT 0")
    ensure_column("patients", "video_room_id", "TEXT NOT NULL DEFAULT ''")
    ensure_column("patients", "video_status", "TEXT NOT NULL DEFAULT 'NONE'")
    ensure_column("patients", "video_requested_at", "TEXT")
    ensure_column("patients", "video_joined_at", "TEXT")

    conn.commit()
    conn.close()
    ensure_default_admin()


def ensure_default_admin() -> None:
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
    if row and row["c"] == 0:
        conn.execute(
            """
            INSERT INTO users (username, display_name, role, password_hash, created_at, must_change_password)
            VALUES (%s, %s, %s, %s, NOW(), TRUE)
            """,
            (DEFAULT_ADMIN_USER, "System Administrator", "admin", hash_password(DEFAULT_ADMIN_PASSWORD)),
        )
        conn.commit()
    conn.close()


def row_to_dict(row) -> Dict[str, Any]:
    return dict(row)


def list_users() -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY id ASC").fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


def get_user(username: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username = %s", (username,)).fetchone()
    conn.close()
    return row_to_dict(row) if row else None


def create_user(username: str, display_name: str, role: str, password_hash: str, must_change_password: bool = False) -> Dict[str, Any]:
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO users (username, display_name, role, password_hash, created_at, must_change_password)
        VALUES (%s, %s, %s, %s, NOW(), %s)
        """,
        (username, display_name, role, password_hash, must_change_password),
    )
    conn.commit()
    conn.close()
    return get_user(username)


def serialize_patient(row: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(row)
    for key, target in [
        ("symptoms_json", "symptoms"),
        ("risk_factors_json", "risk_factors"),
        ("vitals_json", "vitals"),
        ("photo_meta_json", "photo_meta"),
        ("triage_json", "triage"),
    ]:
        raw = data.pop(key, None)
        if raw:
            try:
                data[target] = json.loads(raw)
            except Exception:
                data[target] = [] if target in ("symptoms", "risk_factors") else {}
        else:
            data[target] = [] if target in ("symptoms", "risk_factors") else {}
    data["pregnancy"] = bool(data.get("pregnancy"))
    data["video_recommended"] = bool(data.get("video_recommended"))
    data["video_requested"] = bool(data.get("video_requested"))
    return data


def list_patients(status: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_conn()
    query = "SELECT * FROM patients"
    params: List[Any] = []
    clauses = []
    if status and status != "ALL":
        if status == "REVIEWED":
            clauses.append("status IN ('REVIEWED','REFERRED','ARRIVED','CLOSED')")
        elif status == "NEW":
            clauses.append("status = 'NEW'")
        elif status == "IN_REVIEW":
            clauses.append("status = 'IN_REVIEW'")
        else:
            clauses.append("status = %s")
            params.append(status)
    if search:
        clauses.append("(patient_id LIKE %s OR name LIKE %s OR chief_complaint LIKE %s)")
        s = f"%{search}%"
        params.extend([s, s, s])
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC, id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [serialize_patient(r) for r in rows]


def get_patient(patient_id: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM patients WHERE patient_id = %s", (patient_id,)).fetchone()
    conn.close()
    return serialize_patient(row) if row else None


def create_patient(record: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO patients (
            patient_id, tracking_token, created_at, updated_at, source, name, age, sex, pregnancy,
            chief_complaint, symptoms_json, risk_factors_json, vitals_json, photo_meta_json, image_path,
            location_text, gps_lat, gps_lon, gps_accuracy, emergency_phone, triage_json, status,
            reviewed_by, reviewed_at, notes, video_recommended, video_requested, video_room_id, video_status,
            video_requested_at, video_joined_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            record["patient_id"], record["tracking_token"], record["created_at"], record.get("updated_at"), record["source"],
            record["name"], record.get("age"), record.get("sex"), record.get("pregnancy", False),
            record.get("chief_complaint", ""),
            json.dumps(record.get("symptoms", []), ensure_ascii=False),
            json.dumps(record.get("risk_factors", []), ensure_ascii=False),
            json.dumps(record.get("vitals", {}), ensure_ascii=False),
            json.dumps(record.get("photo_meta", {}), ensure_ascii=False),
            record.get("image_path"),
            record.get("location_text", ""),
            record.get("gps_lat"),
            record.get("gps_lon"),
            record.get("gps_accuracy"),
            record.get("emergency_phone", ""),
            json.dumps(record.get("triage", {}), ensure_ascii=False),
            record.get("status", "NEW"),
            record.get("reviewed_by"),
            record.get("reviewed_at"),
            record.get("notes", ""),
            record.get("video_recommended", False),
            record.get("video_requested", False),
            record.get("video_room_id", ""),
            record.get("video_status", "NONE"),
            record.get("video_requested_at"),
            record.get("video_joined_at"),
        ),
    )
    conn.commit()
    conn.close()
    return get_patient(record["patient_id"])


def update_patient_fields(patient_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    allowed = {"status", "reviewed_by", "reviewed_at", "notes", "updated_at", "gps_lat", "gps_lon", "gps_accuracy", "location_text", "emergency_phone", "video_recommended", "video_requested", "video_room_id", "video_status", "video_requested_at", "video_joined_at"}
    fields, values = [], []
    for k, v in updates.items():
        if k in allowed:
            fields.append(f"{k} = %s")
            values.append(v)
    if not fields:
        return get_patient(patient_id)
    values.append(patient_id)
    conn = get_conn()
    conn.execute(f"UPDATE patients SET {', '.join(fields)} WHERE patient_id = %s", values)
    conn.commit()
    conn.close()
    return get_patient(patient_id)


def record_status_history(patient_id: str, status: str, note: str = "", changed_by: str = "") -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO status_history (patient_id, status, note, changed_by, changed_at) VALUES (%s, %s, %s, %s, NOW())",
        (patient_id, status, note, changed_by),
    )
    conn.commit()
    conn.close()


def update_gps(patient_id: str, tracking_token: str, lat: float, lon: float, accuracy: Optional[float] = None) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    row = conn.execute("SELECT patient_id FROM patients WHERE patient_id = %s AND tracking_token = %s", (patient_id, tracking_token)).fetchone()
    if not row:
        conn.close()
        return None
    conn.execute(
        "INSERT INTO gps_updates (patient_id, tracking_token, lat, lon, accuracy, updated_at) VALUES (%s, %s, %s, %s, %s, NOW())",
        (patient_id, tracking_token, lat, lon, accuracy),
    )
    conn.execute(
        "UPDATE patients SET gps_lat = %s, gps_lon = %s, gps_accuracy = %s, updated_at = NOW() WHERE patient_id = %s",
        (lat, lon, accuracy, patient_id),
    )
    conn.commit()
    conn.close()
    return get_patient(patient_id)


def dashboard_summary() -> Dict[str, Any]:
    patients = list_patients()
    return {
        "total": len(patients),
        "new": sum(1 for p in patients if p.get("status") == "NEW"),
        "in_review": sum(1 for p in patients if p.get("status") == "IN_REVIEW"),
        "reviewed": sum(1 for p in patients if p.get("status") in {"REVIEWED", "REFERRED", "ARRIVED", "CLOSED"}),
        "urgent": sum(1 for p in patients if int(p.get("triage", {}).get("level", 5)) in (1, 2)),
        "gps": sum(1 for p in patients if p.get("gps_lat") is not None and p.get("gps_lon") is not None),
    }
