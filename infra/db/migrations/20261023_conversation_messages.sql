-- 기존 회원, 차량, 정비 데이터를 유지하며 대화 테이블만 추가합니다.
CREATE TABLE IF NOT EXISTS conversation_messages (
  id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  conversation_id  VARCHAR(40)     NOT NULL,
  user_id          BIGINT UNSIGNED NOT NULL,              -- 대화 주인 (JWT sub). 남의 대화는 이어 쓸 수 없다
  role             VARCHAR(10)     NOT NULL,              -- user · assistant
  content          TEXT            NOT NULL,              -- user: 질문 / assistant: 화면용 answer
  created_at       TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_conversation (conversation_id, id),
  CONSTRAINT fk_conversation_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
