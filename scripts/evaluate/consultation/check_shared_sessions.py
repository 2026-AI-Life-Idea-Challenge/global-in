"""Explicit runtime-schema initialization and bounded, synthetic concurrency probe."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--initialize',action='store_true');parser.add_argument('--requests',type=int,default=64)
    args=parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env')
    from app.services.postgres_sessions import PostgresSessions
    from app.services.consultation_sessions import MissingSession,BusySession
    dsn=os.environ.get('CONSULT_SESSION_DATABASE_URL') or os.environ['DATABASE_URL']
    store=PostgresSessions(dsn)
    if args.initialize: store.initialize()
    owner='synthetic-probe-'+__import__('uuid').uuid4().hex
    created=[]
    started=time.monotonic()
    try:
        def worker(index):
            # Each instance uses independent network connections, as remote workers do.
            first,second=PostgresSessions(dsn),PostgresSessions(dsn)
            sid=first.create(owner);created.append(sid)
            _,token=first.acquire(sid,owner)
            try: second.acquire(sid,owner)
            except BusySession: pass
            else: raise AssertionError('Concurrent lease admitted')
            try: second.acquire(sid,'different-owner')
            except MissingSession: pass
            else: raise AssertionError('Owner isolation failed')
            first.commit(sid,token,{'index':index});first.release(sid,token)
            state,new=second.acquire(sid,owner)
            assert state=={'index':index}
            try: first.commit(sid,token,{'stale':True})
            except BusySession: pass
            else: raise AssertionError('Stale token accepted')
            first.release(sid,token)
            try: first.acquire(sid,owner)
            except BusySession: pass
            else: raise AssertionError('Stale release cleared new lease')
            second.release(sid,new)
            return True
        with ThreadPoolExecutor(max_workers=8) as pool: results=list(pool.map(worker,range(args.requests)))
        report=dict(backend='postgresql',workers=8,synthetic_sessions=len(results),checks_per_session=5,
                    passed=all(results),seconds=round(time.monotonic()-started,2),scope='shared_store_local_network_connections_not_production_load')
        target=ROOT/'data/processed/quality/consultation/shared_sessions.json';target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
    finally:
        with store.connect() as conn:
            conn.execute('DELETE FROM consult_runtime.sessions WHERE owner=%s',(owner,))

if __name__=='__main__':main()
