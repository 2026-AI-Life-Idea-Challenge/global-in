"""Local SQLite consultation state and token-bound cross-worker leases.

This is separate from the policy PostgreSQL DB. Workers must share the same
file; multi-host deployments require an external shared store instead.
"""
from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from threading import Lock
import time
import uuid


class MissingSession(Exception):
    pass


class BusySession(Exception):
    pass


class MemorySessions:
    def __init__(self):
        self.sessions = {}
        self.tokens = {}
        self.owners = {}
        self.lock = Lock()

    def create(self, owner=''):
        sid = uuid.uuid4().hex
        with self.lock:
            self.sessions[sid] = {}
            self.owners[sid] = owner
        return sid

    def acquire(self, sid, owner=''):
        with self.lock:
            if sid not in self.sessions or self.owners[sid] != owner:
                raise MissingSession()
            if sid in self.tokens:
                raise BusySession()
            token = self.tokens[sid] = uuid.uuid4().hex
            return deepcopy(self.sessions[sid]), token

    def commit(self, sid, token, state):
        with self.lock:
            if self.tokens.get(sid) != token:
                raise BusySession()
            self.sessions[sid] = deepcopy(state)

    def release(self, sid, token):
        with self.lock:
            if self.tokens.get(sid) == token:
                self.tokens.pop(sid)


class SQLiteSessions:
    def __init__(self, path, ttl=86400, lease_seconds=600):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl, self.lease_seconds = ttl, lease_seconds
        with closing(sqlite3.connect(self.path, timeout=10)) as conn, conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('''CREATE TABLE IF NOT EXISTS consult_sessions(
                session_id TEXT PRIMARY KEY, payload TEXT NOT NULL, expires REAL NOT NULL,
                token TEXT, lease_until REAL NOT NULL DEFAULT 0)''')
            columns = {row[1] for row in conn.execute('PRAGMA table_info(consult_sessions)')}
            if 'owner' not in columns:
                conn.execute("ALTER TABLE consult_sessions ADD COLUMN owner TEXT NOT NULL DEFAULT ''")

    def create(self, owner=''):
        sid = uuid.uuid4().hex
        now = time.time()
        with closing(sqlite3.connect(self.path, timeout=10)) as conn, conn:
            conn.execute('DELETE FROM consult_sessions WHERE expires < ? AND lease_until < ?', (now, now))
            conn.execute('INSERT INTO consult_sessions(session_id,payload,expires,owner) VALUES(?,?,?,?)', (sid, '{}', now+self.ttl, owner))
        return sid

    def acquire(self, sid, owner=''):
        now, token = time.time(), uuid.uuid4().hex
        with closing(sqlite3.connect(self.path, timeout=10)) as conn, conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT payload,expires,lease_until FROM consult_sessions WHERE session_id=? AND owner=?', (sid,owner)).fetchone()
            if row is None or row[1] < now:
                raise MissingSession()
            if row[2] > now:
                raise BusySession()
            conn.execute('UPDATE consult_sessions SET token=?,lease_until=?,expires=? WHERE session_id=?', (token, now+self.lease_seconds, now+self.ttl, sid))
            return json.loads(row[0]), token

    def commit(self, sid, token, state):
        raw = json.dumps(state, ensure_ascii=False, default=str, allow_nan=False)
        with closing(sqlite3.connect(self.path, timeout=10)) as conn, conn:
            result = conn.execute('UPDATE consult_sessions SET payload=?,expires=? WHERE session_id=? AND token=? AND lease_until>=?',
                                  (raw, time.time()+self.ttl, sid, token, time.time()))
            if result.rowcount != 1:
                raise BusySession()

    def release(self, sid, token):
        with closing(sqlite3.connect(self.path, timeout=10)) as conn, conn:
            conn.execute('UPDATE consult_sessions SET token=NULL,lease_until=0 WHERE session_id=? AND token=?', (sid, token))
