-- 차근 DB 초기 스키마 (MariaDB 컨테이너 최초 실행 시 자동 적용)
-- 다시 적용하려면: docker compose down -v -> docker compose up -d

-- 회원 
CREATE TABLE IF NOT EXISTS users (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  username    VARCHAR(100)    NOT NULL,
  password    VARCHAR(255)    NOT NULL,                -- BCrypt 해시
  created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 차량 
CREATE TABLE IF NOT EXISTS vehicles (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id       BIGINT UNSIGNED NOT NULL,              -- 소유자 (JWT sub)
  nickname      VARCHAR(50)     NULL,                  -- 예: 내 K5
  manufacturer  VARCHAR(20)     NOT NULL,              -- 기아 · 현대
  model         VARCHAR(50)     NOT NULL,              -- K5 · 더 뉴 아반떼
  model_year    VARCHAR(10)     NOT NULL,              -- 예: 2026
  powertrain    VARCHAR(50)     NOT NULL,              -- 예: G2.0
  mileage_km    INT UNSIGNED    NULL,                  -- 현재 주행거리
  is_primary    BOOLEAN         NOT NULL DEFAULT FALSE,-- 기본 차량 여부
  created_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_vehicles_user (user_id),
  CONSTRAINT fk_vehicles_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 정비 기록
-- item_label(엔진오일 등)은 저장하지 않고 응답할 때 item 값으로 붙인다
CREATE TABLE IF NOT EXISTS maintenance_records (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  vehicle_id    BIGINT UNSIGNED NOT NULL,
  item          VARCHAR(30)     NOT NULL,              -- engine_oil · air_filter · tire · brake_pad · coolant · battery · wiper · other
  performed_at  DATE            NOT NULL,              -- 정비한 날짜
  mileage_km    INT UNSIGNED    NULL,                  -- 정비 당시 주행거리
  memo          VARCHAR(255)    NULL,
  created_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_maintenance_vehicle (vehicle_id, item, performed_at),
  CONSTRAINT fk_maintenance_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 대화 기록 (RAG에 이전 대화로 보낸다. rag 서버는 상태를 갖지 않는다)
-- conversation_id는 api-server가 첫 질문 때 만든다 (c_ + 32자리). 질문 1번 = user 1줄 + assistant 1줄
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
