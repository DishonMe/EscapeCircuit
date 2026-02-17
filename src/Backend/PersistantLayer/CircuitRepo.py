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
            is_arsenal INTEGER NOT NULL DEFAULT 0,
            basic_gates TEXT NOT NULL DEFAULT '[]',
            truth_table TEXT NOT NULL DEFAULT '{}',
            num_inputs INTEGER NOT NULL DEFAULT 0,
            num_outputs INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, name)
        );
        """)
        
        # Migrate existing DBs that lack the new columns
        try:
            cols = {r[1] for r in self.conn.execute("PRAGMA table_info(circuits);").fetchall()}
            if "is_arsenal" not in cols:
                self.conn.execute("ALTER TABLE circuits ADD COLUMN is_arsenal INTEGER NOT NULL DEFAULT 0;")
            if "basic_gates" not in cols:
                self.conn.execute("ALTER TABLE circuits ADD COLUMN basic_gates TEXT NOT NULL DEFAULT '[]';")
            if "truth_table" not in cols:
                self.conn.execute("ALTER TABLE circuits ADD COLUMN truth_table TEXT NOT NULL DEFAULT '{}';")
            if "num_inputs" not in cols:
                self.conn.execute("ALTER TABLE circuits ADD COLUMN num_inputs INTEGER NOT NULL DEFAULT 0;")
            if "num_outputs" not in cols:
                self.conn.execute("ALTER TABLE circuits ADD COLUMN num_outputs INTEGER NOT NULL DEFAULT 0;")
            self.conn.commit()
        except Exception:
            pass

    def create(self, circuit: Circuit) -> Circuit:
        cur = self.conn.execute("""
            INSERT INTO circuits(user_id, name, cost, structure_json, is_arsenal, basic_gates, truth_table, num_inputs, num_outputs)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (circuit.user_id, circuit.name, circuit.cost, circuit.structure_json, int(circuit.is_arsenal), circuit.basic_gates, circuit.truth_table, circuit.num_inputs, circuit.num_outputs))
        circuit.id = int(cur.lastrowid)
        self.conn.commit()
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
            is_arsenal=bool(row["is_arsenal"]),
            basic_gates=row["basic_gates"] or "",
            truth_table=row["truth_table"] or "",
            num_inputs=int(row["num_inputs"] or 0),
            num_outputs=int(row["num_outputs"] or 0),
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
                is_arsenal=bool(r["is_arsenal"]),
                basic_gates=r["basic_gates"] or "",
                truth_table=r["truth_table"] or "",
                num_inputs=int(r["num_inputs"] or 0),
                num_outputs=int(r["num_outputs"] or 0),
            )
            for r in rows
        ]

    def delete(self, circuit_id: int, user_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM circuits WHERE id=? AND user_id=?", (circuit_id, user_id))
        self.conn.commit()
        return cur.rowcount > 0

    def list_arsenal_by_user(self, user_id: int) -> List[Circuit]:
        """List only arsenal pieces for a user"""
        rows = self.conn.execute("""
            SELECT * FROM circuits WHERE user_id=? AND is_arsenal=1 ORDER BY id DESC
        """, (user_id,)).fetchall()
        return [
            Circuit(
                id=int(r["id"]),
                user_id=int(r["user_id"]),
                name=r["name"],
                cost=int(r["cost"]),
                structure_json=r["structure_json"],
                is_arsenal=bool(r["is_arsenal"]),
                basic_gates=r["basic_gates"] or "",
                truth_table=r["truth_table"] or "",
                num_inputs=int(r["num_inputs"] or 0),
                num_outputs=int(r["num_outputs"] or 0),
            )
            for r in rows
        ]

    def update(self, circuit: Circuit) -> bool:
        """Update an existing circuit"""
        cur = self.conn.execute("""
            UPDATE circuits 
            SET name=?, cost=?, structure_json=?, is_arsenal=?, basic_gates=?, truth_table=?, num_inputs=?, num_outputs=?
            WHERE id=? AND user_id=?
        """, (circuit.name, circuit.cost, circuit.structure_json, int(circuit.is_arsenal), 
              circuit.basic_gates, circuit.truth_table, circuit.num_inputs, circuit.num_outputs, circuit.id, circuit.user_id))
        self.conn.commit()
        return cur.rowcount > 0
