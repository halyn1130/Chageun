# 차근 CHAGEUN

## 실행 방법

준비물: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (실행 중이어야 함). 프론트를 개발 모드로 띄울 때만 Node.js 20.19 이상이 필요합니다.

### 1. 처음 한 번

```bash
git clone https://github.com/halyn1130/Chageun.git
cd Chageun
cp .env.example .env          # 값 채우기 (OPENAI_API_KEY, DB_PASSWORD, JWT_SECRET 등)
```

RAG 검색 인덱스와 PDF 원본은 Git에 없습니다. 팀이 공유한 인덱스를 `ai_data/data/indexes/` 아래에, PDF를 `ai_data/data/raw/` 아래에 둡니다. 현재 쓰는 버전은 `infra/docker-compose.yml`의 `RAG_INDEX`(`v14-figures`)입니다. 자세한 내용은 [ai_data README](ai_data/README.md)를 봅니다.

### 2. 전체 실행

```bash
docker compose up -d --build  # 처음엔 빌드 때문에 몇 분 걸림
```

DB · 서버 · 프론트가 모두 뜹니다. 브라우저에서 **http://localhost:5174** 를 엽니다.

코드를 받은 뒤에는 같은 명령을 다시 실행하면 바뀐 서비스만 새로 빌드됩니다. 모든 `docker compose` 명령은 **저장소 루트**에서 실행합니다. `infra` 폴더에서 실행하면 별도 프로젝트로 컨테이너가 하나 더 생깁니다.

### 확인할 주소

| 주소 | 내용 |
|---|---|
| http://localhost:5174 | **차근 화면** (Vue 빌드본 + nginx, `frontend/`) |
| http://localhost:5500 | 팀 확인용 테스트 페이지 — 로그인 · 내 차 등록 · 텍스트/음성 질문 · 답변 출처 · 음성 재생 (`tools/test-page`) |
| http://localhost:8080/login | 로그인 화면 (auth-server) |
| http://localhost:8002/docs | API 목록·실행 (api-server, Swagger) |
| http://localhost:8002/health | `{"status":"ok","db":"ok"}` 나오면 정상 |
| http://localhost:8008/docs | 음성 API (voice-ai, Swagger) |
| http://localhost:8008/health | `{"status":"ok","whisper":"small"}` 나오면 정상. 처음 실행 때는 Whisper 모델(약 460MB)을 받느라 몇 분 걸림 |
| `localhost:3307` | DB (DB 툴 접속용, 사용자 `root`, 비밀번호는 `.env`의 `DB_PASSWORD`) |

5174 화면은 `/auth` · `/api` · `/voice` 요청을 nginx가 각각 auth-server(8080) · api-server(8002) · voice-ai(8008)로 넘깁니다 (`frontend/nginx.conf`).

## 프론트 개발 모드 (코드 수정하면서 볼 때)

Docker 서비스가 떠 있는 상태에서 별도 터미널로 실행합니다. 저장하면 화면이 바로 바뀝니다.

```bash
cd frontend
npm ci
npm run dev
```

화면: http://localhost:5173 — 프록시 규칙은 5174와 같습니다 (`frontend/vite.config.js`).

**음성 읽기 방식이 5174와 다를 수 있습니다.**

| | 5174 (Docker) | 5173 (개발 모드) |
|---|---|---|
| `VITE_TTS_PROVIDER` | `typecast` (빌드 기본값) | `frontend/.env.local`에 적은 값. 파일이 없으면 비어 있음 |
| 답변 읽기 | 서버 TTS (`/voice/tts`) | 비어 있으면 브라우저 내장 음성 |

개발 모드에서도 서버 TTS를 쓰려면 `cp frontend/.env.example frontend/.env.local` 후 Vite를 다시 시작합니다.

서버 TTS가 어떤 음성으로 만들지는 루트 `.env`의 `TTS_PROVIDER`가 정합니다. 비어 있으면 OpenAI TTS를 쓰고, `typecast`로 하면 `TYPECAST_API_KEY`가 필요합니다 ([Typecast 설정](docs/typecast-tts.md)).

화면별 동작은 [프론트 README](frontend/README.md), API 연결 범위는 [연결 메모](docs/frontend-api-gaps.md)에 정리했습니다.

## 기존 DB 업데이트

`infra/db/init.sql`은 **DB 볼륨을 처음 만들 때만** 실행됩니다. 예전부터 쓰던 DB에는 나중에 추가된 테이블(`conversation_messages`, `user_voice_settings` 등)이 없을 수 있습니다. 이때 API가 `Table ... doesn't exist` 500 에러를 냅니다.

아래 명령은 빠진 테이블만 만들고 기존 회원 · 차량 · 정비 기록은 그대로 둡니다 (`CREATE TABLE IF NOT EXISTS`만 있음).

```bash
docker compose exec -T db sh -c 'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb -uroot chageun' < infra/db/init.sql
```

## 끄기 · 로그 · 초기화

```bash
docker compose down                  # 끄기 (DB 데이터 유지)
docker compose down -v               # 끄기 + DB 데이터 · Whisper 모델 모두 삭제
docker compose logs -f api-server    # 로그 보기
docker compose up -d --build frontend   # 한 서비스만 다시 빌드
```

서비스 이름: `db`, `auth-server`, `api-server`, `voice-ai`, `rag`, `frontend`, `test-page`

## 데이터 관리

RAG는 `infra/docker-compose.yml`의 `RAG_INDEX` 경로에 있는 인덱스를 읽습니다. 팀이 공유한 인덱스를 해당 경로에 배치합니다.

- 설명서 원본(`ai_data/data/raw`), 검색 인덱스(`ai_data/data/indexes`), 다운로드한 `indexes.zip`, `.env`, 실제 DB 덤프는 Git에 올리지 않습니다.
- 문서 목록·경고등 사전·테스트용 예시 JSON과 화면용 이미지는 코드와 함께 관리합니다.
- `infra/db/demo-account-1.json`은 붕붕이 1대의 합성 시연 이력 정의이며 실제 DB 덤프나 자동 데이터 변경 스크립트가 아닙니다.
