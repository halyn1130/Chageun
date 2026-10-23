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
  model         VARCHAR(50)     NOT NULL,              -- K5 · 디 올 뉴 아반떼
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
