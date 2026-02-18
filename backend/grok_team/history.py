from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import asyncio
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class StoredMessage:
    role: str
    content: str
    created_at: str = field(default_factory=utc_now_iso)
    thoughts: Optional[List[Dict[str, Any]]] = None
    duration: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at,
        }
        if self.thoughts:
            payload["thoughts"] = self.thoughts
        if self.duration is not None:
            payload["duration"] = self.duration
        return payload


@dataclass
class Conversation:
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[StoredMessage]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [message.to_dict() for message in self.messages],
        }


class SQLiteHistoryStore:
    def __init__(self, db_path: Path):
        self._db_path = db_path

    async def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        def _init() -> None:
            conn = sqlite3.connect(self._db_path)
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA foreign_keys=ON;")
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        thoughts_json TEXT,
                        duration REAL,
                        FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                    )
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at DESC)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id, id)")
                conn.commit()
            finally:
                conn.close()

        await asyncio.to_thread(_init)

    async def create(self, title: str = "Новый диалог") -> Conversation:
        conversation_id = str(uuid4())
        now = utc_now_iso()

        def _create() -> None:
            conn = sqlite3.connect(self._db_path)
            try:
                conn.execute(
                    "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (conversation_id, title, now, now),
                )
                conn.commit()
            finally:
                conn.close()

        await asyncio.to_thread(_create)
        return Conversation(id=conversation_id, title=title, created_at=now, updated_at=now, messages=[])

    async def get_or_create(self, conversation_id: Optional[str]) -> Conversation:
        if conversation_id:
            existing = await self.get(conversation_id)
            if existing:
                return existing
        return await self.create()

    async def get(self, conversation_id: str) -> Optional[Conversation]:
        def _get() -> Optional[Conversation]:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            try:
                conv = conn.execute(
                    "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
                    (conversation_id,),
                ).fetchone()
                if conv is None:
                    return None

                rows = conn.execute(
                    """
                    SELECT role, content, created_at, thoughts_json, duration
                    FROM messages
                    WHERE conversation_id = ?
                    ORDER BY id ASC
                    """,
                    (conversation_id,),
                ).fetchall()

                messages: List[StoredMessage] = []
                for row in rows:
                    thoughts_payload: Optional[List[Dict[str, Any]]] = None
                    if row["thoughts_json"]:
                        try:
                            raw = json.loads(row["thoughts_json"])
                            if isinstance(raw, list):
                                thoughts_payload = raw
                        except json.JSONDecodeError:
                            thoughts_payload = None

                    messages.append(
                        StoredMessage(
                            role=row["role"],
                            content=row["content"],
                            created_at=row["created_at"],
                            thoughts=thoughts_payload,
                            duration=row["duration"],
                        )
                    )

                return Conversation(
                    id=conv["id"],
                    title=conv["title"],
                    created_at=conv["created_at"],
                    updated_at=conv["updated_at"],
                    messages=messages,
                )
            finally:
                conn.close()

        return await asyncio.to_thread(_get)

    async def list_summaries(self) -> List[Dict[str, Any]]:
        def _list() -> List[Dict[str, Any]]:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    SELECT
                        c.id,
                        c.title,
                        c.created_at,
                        c.updated_at,
                        COALESCE((
                            SELECT m.content
                            FROM messages m
                            WHERE m.conversation_id = c.id
                            ORDER BY m.id DESC
                            LIMIT 1
                        ), '') AS last_message,
                        (SELECT COUNT(*) FROM messages m2 WHERE m2.conversation_id = c.id) AS message_count
                    FROM conversations c
                    ORDER BY c.updated_at DESC
                    """
                ).fetchall()

                return [
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "last_message": str(row["last_message"] or "")[:160],
                        "message_count": int(row["message_count"] or 0),
                    }
                    for row in rows
                ]
            finally:
                conn.close()

        return await asyncio.to_thread(_list)

    async def search_summaries(self, query: str) -> List[Dict[str, Any]]:
        normalized = query.strip().lower()
        if not normalized:
            return await self.list_summaries()

        def _search() -> List[Dict[str, Any]]:
            like_query = f"%{normalized}%"
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    SELECT
                        c.id,
                        c.title,
                        c.created_at,
                        c.updated_at,
                        COALESCE((
                            SELECT m.content
                            FROM messages m
                            WHERE m.conversation_id = c.id
                            ORDER BY m.id DESC
                            LIMIT 1
                        ), '') AS last_message,
                        (SELECT COUNT(*) FROM messages m2 WHERE m2.conversation_id = c.id) AS message_count
                    FROM conversations c
                    WHERE lower(c.title) LIKE ?
                        OR EXISTS (
                            SELECT 1
                            FROM messages m
                            WHERE m.conversation_id = c.id
                              AND lower(m.content) LIKE ?
                        )
                    ORDER BY c.updated_at DESC
                    """,
                    (like_query, like_query),
                ).fetchall()

                return [
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "last_message": str(row["last_message"] or "")[:160],
                        "message_count": int(row["message_count"] or 0),
                    }
                    for row in rows
                ]
            finally:
                conn.close()

        return await asyncio.to_thread(_search)

    async def add_message(self, conversation_id: str, message: StoredMessage) -> bool:
        def _add() -> bool:
            conn = sqlite3.connect(self._db_path)
            try:
                conn.execute("PRAGMA foreign_keys=ON;")
                existing = conn.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
                if existing is None:
                    return False

                thoughts_json = json.dumps(message.thoughts, ensure_ascii=False) if message.thoughts else None
                conn.execute(
                    """
                    INSERT INTO messages (conversation_id, role, content, created_at, thoughts_json, duration)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (conversation_id, message.role, message.content, message.created_at, thoughts_json, message.duration),
                )

                conn.execute(
                    "UPDATE conversations SET updated_at = ? WHERE id = ?",
                    (utc_now_iso(), conversation_id),
                )

                if message.role == "user":
                    inferred_title = (message.content.strip().split("\n", 1)[0][:80] or "Новый диалог")
                    conn.execute(
                        "UPDATE conversations SET title = ? WHERE id = ? AND title = 'Новый диалог'",
                        (inferred_title, conversation_id),
                    )

                conn.commit()
                return True
            finally:
                conn.close()

        return await asyncio.to_thread(_add)

    async def update_title(self, conversation_id: str, title: str) -> bool:
        safe_title = title[:120].strip()
        if not safe_title:
            return False

        def _update() -> bool:
            conn = sqlite3.connect(self._db_path)
            try:
                cursor = conn.execute(
                    "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                    (safe_title, utc_now_iso(), conversation_id),
                )
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

        return await asyncio.to_thread(_update)

    async def delete(self, conversation_id: str) -> bool:
        def _delete() -> bool:
            conn = sqlite3.connect(self._db_path)
            try:
                conn.execute("PRAGMA foreign_keys=ON;")
                cursor = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

        return await asyncio.to_thread(_delete)
