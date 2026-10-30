import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import psycopg
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    """프로젝트 환경설정으로 DB에 연결하고 사용 후 연결을 닫는다."""
    load_dotenv(dotenv_path=ENV_PATH, override=False)

    database_url = os.getenv("DATABASE_URL")
    if database_url is None or not database_url.strip():
        raise RuntimeError(
            "DATABASE_URL이 설정되어 있지 않습니다. "
            "프로젝트 루트의 .env 또는 환경변수를 확인해주세요."
        )

    with psycopg.connect(database_url) as connection:
        yield connection
