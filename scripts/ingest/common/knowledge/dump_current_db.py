"""Export the currently connected PostgreSQL database without changing its data."""
import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.conninfo import conninfo_to_dict
from psycopg import sql

ROOT = Path(__file__).resolve().parents[4]


def main():
    load_dotenv(ROOT / '.env')
    params = conninfo_to_dict(os.environ['DATABASE_URL'])
    binary = Path(r'C:\Program Files\PostgreSQL\17\bin')
    env = os.environ.copy()
    for key, variable in [('host', 'PGHOST'), ('port', 'PGPORT'),
                          ('user', 'PGUSER'), ('password', 'PGPASSWORD'),
                          ('dbname', 'PGDATABASE'), ('sslmode', 'PGSSLMODE')]:
        if key in params:
            env[variable] = params[key]
    env['PGCONNECT_TIMEOUT'] = '10'
    folder = ROOT / 'data/exports'
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime('%Y%m%d_%H%M%S')
    target = folder / f'global_in_current_{stamp}.dump'
    temporary = target.with_suffix('.dump.partial')
    with psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=10) as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        version = conn.execute('SHOW server_version').fetchone()[0]
        snapshot = conn.execute('SELECT pg_export_snapshot()').fetchone()[0]
        tables = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
        counts = {name: conn.execute(sql.SQL('SELECT count(*) FROM public.{}').format(sql.Identifier(name))).fetchone()[0]
                  for (name,) in tables}
        result = subprocess.run([str(binary / 'pg_dump.exe'), '--format=custom', '--no-owner',
                                 '--no-privileges', '--snapshot', snapshot, '--file', str(temporary)],
                                env=env, capture_output=True)
        if result.returncode:
            temporary.unlink(missing_ok=True)
            raise RuntimeError('pg_dump failed; connection details suppressed.')
    check = subprocess.run([str(binary / 'pg_restore.exe'), '--list', str(temporary)], capture_output=True)
    if check.returncode or b'TABLE DATA' not in check.stdout:
        raise RuntimeError('Archive directory verification failed.')
    # Read and decompress the complete archive without connecting to a database.
    check = subprocess.run([str(binary / 'pg_restore.exe'), '--file', os.devnull, str(temporary)], capture_output=True)
    if check.returncode:
        raise RuntimeError('Full archive read verification failed.')
    temporary.replace(target)
    receipt = dict(file=str(target), created_at=datetime.now().astimezone().isoformat(),
                   server_version=version, bytes=target.stat().st_size,
                   sha256=hashlib.file_digest(target.open('rb'), 'sha256').hexdigest(),
                   public_table_counts=counts, consistent_snapshot=True,
                   archive_directory_verified=True, full_archive_read_verified=True,
                   restore_into_database_tested=False, database_modified=False)
    target.with_suffix('.manifest.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
