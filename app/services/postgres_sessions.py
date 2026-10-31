"""Shared PostgreSQL session store, separate from the immutable policy tables.

Schema creation is explicit. All clocks and leases use PostgreSQL server time.
No connection/row lock is held while a model is running.
"""
import json
import uuid
import psycopg
from psycopg.types.json import Jsonb
from app.services.consultation_sessions import BusySession, MissingSession


class PostgresSessions:
    def __init__(self, dsn, ttl=86400, lease_seconds=600):
        self.dsn, self.ttl, self.lease_seconds = dsn, ttl, lease_seconds

    def connect(self):
        return psycopg.connect(self.dsn, connect_timeout=5, options='-c statement_timeout=10000 -c lock_timeout=5000')

    def initialize(self):
        with self.connect() as conn:
            conn.execute('CREATE SCHEMA IF NOT EXISTS consult_runtime')
            conn.execute('''CREATE TABLE IF NOT EXISTS consult_runtime.sessions (
                session_id text PRIMARY KEY, owner text NOT NULL, payload jsonb NOT NULL,
                expires timestamptz NOT NULL, token text, lease_until timestamptz)''')
            conn.execute('CREATE INDEX IF NOT EXISTS consult_sessions_expiry ON consult_runtime.sessions(expires)')

    def create(self, owner=''):
        sid=uuid.uuid4().hex
        with self.connect() as conn:
            conn.execute('''DELETE FROM consult_runtime.sessions WHERE expires < clock_timestamp()
                AND (lease_until IS NULL OR lease_until < clock_timestamp())''')
            conn.execute('''INSERT INTO consult_runtime.sessions(session_id,owner,payload,expires)
                VALUES (%s,%s,'{}',clock_timestamp()+%s*interval '1 second')''',(sid,owner,self.ttl))
        return sid

    def acquire(self,sid,owner=''):
        token=uuid.uuid4().hex
        with self.connect() as conn:
            row=conn.execute('''SELECT payload,expires>=clock_timestamp(),
                lease_until>clock_timestamp() FROM consult_runtime.sessions
                WHERE session_id=%s AND owner=%s FOR UPDATE''',(sid,owner)).fetchone()
            if row is None or not row[1]: raise MissingSession()
            if row[2]: raise BusySession()
            conn.execute('''UPDATE consult_runtime.sessions SET token=%s,
                lease_until=clock_timestamp()+%s*interval '1 second',
                expires=clock_timestamp()+%s*interval '1 second' WHERE session_id=%s''',
                (token,self.lease_seconds,self.ttl,sid))
            return row[0],token

    def commit(self,sid,token,state):
        # Reject NaN and unserializable state before opening a transaction.
        clean=json.loads(json.dumps(state,ensure_ascii=False,allow_nan=False,default=str))
        with self.connect() as conn:
            result=conn.execute('''UPDATE consult_runtime.sessions SET payload=%s,
                expires=clock_timestamp()+%s*interval '1 second'
                WHERE session_id=%s AND token=%s AND lease_until>=clock_timestamp()''',
                (Jsonb(clean),self.ttl,sid,token))
            if result.rowcount!=1: raise BusySession()

    def release(self,sid,token):
        with self.connect() as conn:
            conn.execute('''UPDATE consult_runtime.sessions SET token=NULL,lease_until=NULL
                WHERE session_id=%s AND token=%s''',(sid,token))
