# 차근 CHAGEUN

## 실행 방법

준비물: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (실행 중이어야 함)

```bash
git clone https://github.com/halyn1130/Chageun.git
cd Chageun
cp .env.example .env          # env 채우기
docker compose up -d --build  # 처음엔 빌드 때문에 몇 분 걸림
```

## 확인할 주소

| 주소 | 내용 |
|---|---|
| http://localhost:8080/login | 로그인 화면 (auth-server) |
| http://localhost:8002/docs | API 목록·실행 (api-server, Swagger) |
| http://localhost:8002/health | `{"status":"ok","db":"ok"}` 나오면 정상 |
| http://localhost:8008/docs | 음성 API (voice-ai, Swagger) |
| http://localhost:8008/health | `{"status":"ok","whisper":"small"}` 나오면 정상. 처음 실행 때는 Whisper 모델(약 460MB)을 받느라 몇 분 걸림 |
| http://localhost:5500 | **팀 확인용 테스트 페이지** — 로그인 · 내 차 등록 · 텍스트/음성 질문 · 답변 출처 · 음성 재생을 한 화면에서 (`tools/test-page`, 프론트 화면 아님) |
| `localhost:3307` | DB (DB 툴 접속용, 사용자 `root`, 비밀번호는 `.env`의 `DB_PASSWORD`) |

## Vue 화면 실행

Docker 서비스가 실행 중인 상태에서 별도 터미널에서 실행합니다.

```bash
cd frontend
npm ci
npm run dev
```

화면: http://localhost:5173/ — 상단에서 **PC / 모바일**을 전환합니다. 홈은 음성 대화와 경고·이상 / 기능·조작 / 도로 규칙, 내 차 케어는 소모품 10종의 사용량과 정비 기록을 제공합니다. PC 1280×480은 와이드 시연 기준이며 실제 차량 패널 해상도를 의미하지 않습니다. 모바일은 390×844 기준으로 별도 배치합니다.

JWT 인증, 차량·정비 기록 저장, 내부 RAG를 실제 API에 연결했습니다. 웹 음성은 브라우저 음성 인식·읽기를 사용합니다. 실행 범위와 API 영향은 [연결 메모](docs/frontend-api-gaps.md), 화면별 동작은 [프론트 README](frontend/README.md)에 정리했습니다.

### 데이터 관리

RAG는 `infra/docker-compose.yml`의 `RAG_INDEX` 경로에 있는 인덱스를 읽습니다. 팀이 공유한 인덱스를 해당 경로에 배치합니다.

- 설명서 원본(`ai_data/data/raw`), 검색 인덱스(`ai_data/data/indexes`), 다운로드한 `indexes.zip`, `.env`, 실제 DB 덤프는 Git에 올리지 않습니다.
- 문서 목록·경고등 사전·테스트용 예시 JSON과 화면용 이미지는 코드와 함께 관리합니다.
- `infra/db/demo-account-1.json`은 붕붕이 1대의 합성 시연 이력 정의이며 실제 DB 덤프나 자동 데이터 변경 스크립트가 아닙니다.

## 끄기 · 초기화

```bash
docker compose down       # 끄기 (DB 데이터 유지)
docker compose down -v    # 끄기 + DB 데이터 · Whisper 모델 모두 삭제
docker compose logs -f auth-server   # 로그 보기 (서비스 이름: db, auth-server, api-server, voice-ai)
```

### 기존 DB에 최신 대화 테이블 추가

기존 회원·차량·정비 기록을 유지하면서 추가 마이그레이션을 적용합니다. 카탈로그 연식 변경은 과거 차량의 연식을 바꾸는 이유가 아닙니다.

```bash
docker compose exec -T db sh -c 'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb -uroot chageun' < infra/db/migrations/20261023_conversation_messages.sql
docker compose up -d --build api-server rag
```
