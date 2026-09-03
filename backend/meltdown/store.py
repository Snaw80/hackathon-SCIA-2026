import hashlib
import json
import sqlite3
from pathlib import Path


def fingerprint(request):
    return hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False, timeout=30)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS games (id TEXT PRIMARY KEY, version INTEGER NOT NULL, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS requests (
          game_id TEXT NOT NULL, request_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
          response TEXT NOT NULL, PRIMARY KEY (game_id, request_id));
        """)

    def create(self, game):
        with self.conn:
            self.conn.execute(
                "INSERT INTO games VALUES (?, ?, ?)", (game["id"], game["version"], json.dumps(game))
            )

    def load(self, game_id):
        row = self.conn.execute("SELECT data FROM games WHERE id = ?", (game_id,)).fetchone()
        if not row:
            raise KeyError(game_id)
        return json.loads(row[0])

    def receipt(self, game_id, request):
        row = self.conn.execute(
            "SELECT fingerprint,response FROM requests WHERE game_id=? AND request_id=?",
            (game_id, request["request_id"]),
        ).fetchone()
        if not row:
            return None
        if row[0] != fingerprint(request):
            raise ValueError("This request ID has already been used for another decision.")
        return json.loads(row[1])

    def commit(self, game, request):
        from .projection import public_view

        existing = self.receipt(game["id"], request)
        if existing is not None:
            return self.load(game["id"])
        response = public_view(game)
        with self.conn:
            updated = self.conn.execute(
                "UPDATE games SET version=?, data=? WHERE id=? AND version=?",
                (game["version"], json.dumps(game), game["id"], request["expected_version"]),
            )
            if updated.rowcount != 1:
                raise ValueError("The saved version has changed. Reload the game.")
            self.conn.execute(
                "INSERT INTO requests VALUES (?, ?, ?, ?)",
                (game["id"], request["request_id"], fingerprint(request), json.dumps(response)),
            )
        return game

    def close(self):
        self.conn.close()
