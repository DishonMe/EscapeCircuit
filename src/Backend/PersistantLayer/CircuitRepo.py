import sqlite3
from typing import Optional, List

from Backend.DomainLayer.Circuit import Circuit


class CircuitRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS circuits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            cost INTEGER NOT NULL,
            structure_json TEXT NOT NULL,
            UNIQUE(user_id, name)
        );
        """)

    def create(self, circuit: Circuit) -> Circuit:
        cur = self.conn.execute("""
            INSERT INTO circuits(user_id, name, cost, structure_json)
            VALUES(?,?,?,?)
        """, (circuit.user_id, circuit.name, circuit.cost, circuit.structure_json))
        circuit.id = int(cur.lastrowid)
        return circuit

    def get_by_id(self, circuit_id: int) -> Optional[Circuit]:
        row = self.conn.execute("SELECT * FROM circuits WHERE id=?", (circuit_id,)).fetchone()
        if not row:
            return None
        return Circuit(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            name=row["name"],
            cost=int(row["cost"]),
            structure_json=row["structure_json"],
        )

    def list_by_user(self, user_id: int) -> List[Circuit]:
        rows = self.conn.execute("""
            SELECT * FROM circuits WHERE user_id=? ORDER BY id DESC
        """, (user_id,)).fetchall()
        return [
            Circuit(
                id=int(r["id"]),
                user_id=int(r["user_id"]),
                name=r["name"],
                cost=int(r["cost"]),
                structure_json=r["structure_json"],
            )
            for r in rows
        ]

    def delete(self, circuit_id: int, user_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM circuits WHERE id=? AND user_id=?", (circuit_id, user_id))
        return cur.rowcount > 0
