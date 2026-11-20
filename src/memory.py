import sqlite3
import json
import uuid
import os
from datetime import datetime
from src.config import Config
from src.utils import setup_logger

logger = setup_logger(__name__)

class MemoryManager:
    """
    Manages chat history and sessions using local SQLite.
    Zero external database required - 100% reliable across any environment/IP.
    """
    def __init__(self):
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        self.db_path = os.path.join(Config.DATA_DIR, "clarity_rx.db")
        self._init_db()
        logger.info(f"MemoryManager connected to local SQLite database at {self.db_path}")

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT,
                        prescription_id TEXT,
                        title TEXT,
                        filename TEXT,
                        details TEXT,
                        extracted_data TEXT,
                        summary TEXT,
                        otc_result TEXT,
                        created_at TEXT,
                        last_active TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT,
                        role TEXT,
                        content TEXT,
                        timestamp TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize SQLite database: {e}")

    def get_or_create_session(self, user_id, prescription_id, title=None, filename=None, details=None, extracted_data=None):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM sessions WHERE user_id = ? AND prescription_id = ?",
                    (user_id, prescription_id)
                )
                existing = cursor.fetchone()

                now = datetime.utcnow().isoformat()

                if existing:
                    session_id = existing["session_id"]
                    updates = []
                    params = []

                    if title and not existing["title"]:
                        updates.append("title = ?")
                        params.append(title)
                    if filename and not existing["filename"]:
                        updates.append("filename = ?")
                        params.append(filename)
                    if details and not existing["details"]:
                        updates.append("details = ?")
                        params.append(details)
                    if extracted_data and not existing["extracted_data"]:
                        updates.append("extracted_data = ?")
                        params.append(json.dumps(extracted_data) if isinstance(extracted_data, (dict, list)) else str(extracted_data))

                    if updates:
                        params.append(session_id)
                        cursor.execute(f"UPDATE sessions SET {', '.join(updates)} WHERE session_id = ?", params)
                        conn.commit()
                    return session_id

                session_id = str(uuid.uuid4())
                extracted_data_str = json.dumps(extracted_data) if isinstance(extracted_data, (dict, list)) else (str(extracted_data) if extracted_data else "")

                cursor.execute("""
                    INSERT INTO sessions (
                        session_id, user_id, prescription_id, title, filename, details,
                        extracted_data, summary, otc_result, created_at, last_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id, user_id, prescription_id,
                    title or f"Prescription {prescription_id[:8]}",
                    filename or "",
                    details or "",
                    extracted_data_str,
                    "",
                    "",
                    now,
                    now
                ))
                conn.commit()
                logger.info(f"Created new session {session_id} for user {user_id}")
                return session_id
        except Exception as e:
            logger.error(f"get_or_create_session failed: {e}")
            return str(uuid.uuid4())

    def get_session_info(self, session_id):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
                row = cursor.fetchone()
                if not row:
                    return {}
                res = dict(row)
                if res.get("extracted_data"):
                    try:
                        res["extracted_data"] = json.loads(res["extracted_data"])
                    except Exception:
                        pass
                return res
        except Exception as e:
            logger.error(f"get_session_info failed: {e}")
            return {}

    def get_session_details(self, session_id):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT details FROM sessions WHERE session_id = ?", (session_id,))
                row = cursor.fetchone()
                return row["details"] if row and row["details"] else ""
        except Exception as e:
            logger.error(f"get_session_details failed: {e}")
            return ""

    def get_prescription_by_filename(self, user_id, filename):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT prescription_id FROM sessions WHERE user_id = ? AND filename = ?",
                    (user_id, filename)
                )
                row = cursor.fetchone()
                return row["prescription_id"] if row else None
        except Exception as e:
            logger.error(f"get_prescription_by_filename failed: {e}")
            return None

    def add_message(self, session_id, role, content):
        try:
            now = datetime.utcnow().isoformat()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO messages (session_id, role, content, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (session_id, role, content, now))
                cursor.execute("UPDATE sessions SET last_active = ? WHERE session_id = ?", (now, session_id))
                conn.commit()
        except Exception as e:
            logger.error(f"add_message failed: {e}")

    def get_history(self, session_id, limit=20):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT role, content, timestamp FROM messages
                    WHERE session_id = ? ORDER BY id ASC LIMIT ?
                """, (session_id, limit))
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"get_history failed: {e}")
            return []

    def get_summary(self, session_id):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT summary FROM sessions WHERE session_id = ?", (session_id,))
                row = cursor.fetchone()
                return row["summary"] if row and row["summary"] else ""
        except Exception as e:
            logger.error(f"get_summary failed: {e}")
            return ""

    def update_summary(self, session_id, new_summary):
        try:
            now = datetime.utcnow().isoformat()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE sessions SET summary = ?, last_active = ? WHERE session_id = ?",
                    (new_summary, now, session_id)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"update_summary failed: {e}")

    def update_last_active(self, session_id):
        try:
            now = datetime.utcnow().isoformat()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE sessions SET last_active = ? WHERE session_id = ?", (now, session_id))
                conn.commit()
        except Exception as e:
            logger.error(f"update_last_active failed: {e}")

    def get_user_prescriptions(self, user_id):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT prescription_id, title, last_active FROM sessions
                    WHERE user_id = ? AND prescription_id != 'GLOBAL'
                    ORDER BY last_active DESC
                """, (user_id,))
                rows = cursor.fetchall()
                results = []
                seen_ids = set()
                for row in rows:
                    p_id = row["prescription_id"]
                    if p_id not in seen_ids:
                        results.append({
                            "id": p_id,
                            "title": row["title"] or f"Prescription {p_id[:8]}"
                        })
                        seen_ids.add(p_id)
                return results
        except Exception as e:
            logger.error(f"get_user_prescriptions failed: {e}")
            return []

    def get_all_sessions(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM sessions ORDER BY last_active DESC")
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"get_all_sessions failed: {e}")
            return []

    def save_otc_result(self, session_id, otc_result):
        try:
            data_str = json.dumps(otc_result) if isinstance(otc_result, (dict, list)) else str(otc_result)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE sessions SET otc_result = ? WHERE session_id = ?", (data_str, session_id))
                conn.commit()
        except Exception as e:
            logger.error(f"save_otc_result failed: {e}")

    def get_otc_result(self, session_id):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT otc_result FROM sessions WHERE session_id = ?", (session_id,))
                row = cursor.fetchone()
                if not row or not row["otc_result"]:
                    return None
                try:
                    return json.loads(row["otc_result"])
                except Exception:
                    return row["otc_result"]
        except Exception as e:
            logger.error(f"get_otc_result failed: {e}")
            return None
