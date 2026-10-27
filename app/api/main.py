
import os
from contextlib import asynccontextmanager

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from psycopg.rows import dict_row

from app.models.program import Program, PolicyCandidate, Evidence, SupportProgram


load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")

    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("SELECT 1")

    yield


app = FastAPI(
    title="Global-In API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
def root():
    return {"message": "Global-In API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/programs", response_model=list[Program])
def list_programs(
    country: str | None = Query(default=None),
    category: str | None = Query(default=None),
):
    query = """
        SELECT program_id, country, name, category, route_id,
               visa_subclass, stream, source_program_id,
               source_file, review_status, metadata
        FROM programs
        WHERE TRUE
    """
    params = []

    if country is not None:
        query += " AND country = %s"
        params.append(country)

    if category is not None:
        query += " AND category = %s"
        params.append(category)

    query += " ORDER BY country, program_id"

    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            rows = conn.execute(query, params).fetchall()
    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Database query failed",
        )

    return rows


@app.get("/programs/{program_id}", response_model=Program)
def get_program(program_id: str):
    query = """
        SELECT program_id, country, name, category, route_id,
               visa_subclass, stream, source_program_id,
               source_file, review_status, metadata
        FROM programs
        WHERE program_id = %s
    """

    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            row = conn.execute(query, (program_id,)).fetchone()
    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Database query failed",
        ) from None

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Program not found",
        )

    return row


@app.get(
    "/programs/{program_id}/policies",
    response_model=list[PolicyCandidate],
)
def get_program_policies(program_id: str):
    query = """
        SELECT policy_id, program_id, country, topic,
               source_evidence_ids, policy_text, review_status,
               legal_validation_approved,
               approved_for_eligibility_decision,
               approved_for_embedding,
               approved_for_user_answers,
               metadata
        FROM policy_candidates
        WHERE program_id = %s
        ORDER BY policy_id
    """

    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:

            exists = conn.execute(
                "SELECT 1 FROM programs WHERE program_id = %s",
                (program_id,),
            ).fetchone()

            if exists is None:
                raise HTTPException(
                    status_code=404,
                    detail="Program not found",
                )

            rows = conn.execute(query, (program_id,)).fetchall()
    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Database query failed",
        ) from None

    return rows


@app.get(
    "/programs/{program_id}/evidence",
    response_model=list[Evidence],
)
def get_program_evidence(program_id: str):
    query = """
        SELECT evidence_id, program_id, country,
               source_evidence_id, source_id, source_url,
               source_file, source_sha256, exact_quote,
               source_location, review_status, metadata
        FROM evidence
        WHERE program_id = %s
        ORDER BY evidence_id
    """

    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:

            exists = conn.execute(
                "SELECT 1 FROM programs WHERE program_id = %s",
                (program_id,),
            ).fetchone()

            if exists is None:
                raise HTTPException(
                    status_code=404,
                    detail="Program not found",
                )

            rows = conn.execute(query, (program_id,)).fetchall()
    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Database query failed",
        ) from None

    return rows


@app.get("/support-programs", response_model=list[SupportProgram])
def list_support_programs(
    country: str | None = Query(default=None),
):
    query = """
        SELECT support_program_id, country, name, provider,
               source_file, review_status, metadata
        FROM support_programs
        WHERE TRUE
    """
    params = []

    if country is not None:
        query += " AND country = %s"
        params.append(country)

    query += " ORDER BY country, support_program_id"

    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            rows = conn.execute(query, params).fetchall()
    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Database query failed",
        ) from None

    return rows