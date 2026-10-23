"""대화 기록 — /rag-query 프록시가 RAG에 보낼 history를 꺼내고, 답을 받은 뒤 질문·답변을 저장한다.

rag 서버는 상태를 갖지 않아서 이전 대화는 매번 여기서 꺼내 보낸다 (내부 API의 history).
"""
import uuid

from fastapi import HTTPException

from app.auth import CurrentUser

HISTORY_LIMIT = 6   # 최근 3턴 (질문 + 답변 = 2줄)


def new_conversation_id() -> str:
    return f"c_{uuid.uuid4().hex}"


def load_history(db, user: CurrentUser, conversation_id: str) -> list[dict]:
    """최근 대화를 오래된 것부터. 남의 대화면 404, 처음 보는 id면 빈 목록(새 대화로 시작)."""
    with db.cursor() as cur:
        cur.execute("SELECT user_id FROM conversation_messages WHERE conversation_id = %s LIMIT 1",
                    (conversation_id,))
        owner = cur.fetchone()
        if owner is None:
            return []
        if owner["user_id"] != user.id:
            raise HTTPException(404, "대화를 찾을 수 없어요. 새 대화로 다시 질문해 주세요.")
        cur.execute("SELECT role, content FROM conversation_messages WHERE conversation_id = %s"
                    " ORDER BY id DESC LIMIT %s", (conversation_id, HISTORY_LIMIT))
        return list(reversed(cur.fetchall()))


def save_turn(db, user: CurrentUser, conversation_id: str, question: str, answer: str) -> None:
    with db.cursor() as cur:
        cur.executemany(
            "INSERT INTO conversation_messages (conversation_id, user_id, role, content) VALUES (%s, %s, %s, %s)",
            [(conversation_id, user.id, "user", question), (conversation_id, user.id, "assistant", answer)],
        )
