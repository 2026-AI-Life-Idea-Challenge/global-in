import psycopg2

conn = psycopg2.connect("postgresql://global_in_app:outsiders4@localhost:5432/global_in")
cur = conn.cursor()

cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
print("pgvector:", cur.fetchone())

cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
print("tables:", [r[0] for r in cur.fetchall()])

cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='knowledge_chunks'")
print("knowledge_chunks exists:", bool(cur.fetchone()[0]))

cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='knowledge_chunk_embeddings'")
print("knowledge_chunk_embeddings exists:", bool(cur.fetchone()[0]))

conn.close()
print("done")
