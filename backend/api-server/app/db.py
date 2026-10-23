"""MariaDB 연결 — 요청마다 연결을 하나 열고, 끝나면 커밋(오류 시 롤백) 후 닫는다.

접속 정보는 docker compose(infra/docker-compose.yml)가 환경변수로 넣어 준다. 없으면 서버가 뜨지 않는다
"""
import os

import pymysql
from pymysql.cursors import DictCursor

DB_CONFIG = {
    "host": os.environ["DB_HOST"],
    "port": int(os.environ["DB_PORT"]),
    "database": os.environ["DB_NAME"],
    "user": os.environ["DB_USER"],
    "password": os.environ["DB_PASSWORD"],
    "charset": "utf8mb4",
    "cursorclass": DictCursor,   # 조회 결과를 dict로 받아 그대로 JSON 응답에 쓴다
    "connect_timeout": 5,
}


def connect() -> pymysql.connections.Connection:
    return pymysql.connect(**DB_CONFIG)


def get_db():
    """FastAPI 의존성: `db = Depends(get_db)`로 받아 쓴다."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
