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

> 대화(`/rag-query`)는 rag 서버의 문서 인덱스가 있어야 답한다. `ai_data/data/indexes/v9-law-paragraphs` 폴더를 받아 넣지 않으면 503. API 형식은 노션 API 명세서 참고.

## 끄기 · 초기화

```bash
docker compose down       # 끄기 (DB 데이터 유지)
docker compose down -v    # 끄기 + DB 데이터 · Whisper 모델 모두 삭제
docker compose logs -f auth-server   # 로그 보기 (서비스 이름: db, auth-server, api-server, voice-ai)
```

### DB 다시 만들기 (init.sql · 차종 값이 바뀌었을 때)

`docker compose down` → `up`만 하면 DB 데이터는 그대로 남는다. `infra/db/init.sql`이 바뀌었거나 차량 카탈로그 값이 바뀌었으면 DB를 지우고 다시 만든다.

```bash
docker compose down
docker volume rm chageun_db-data   # DB만 삭제 (Whisper 모델은 유지)
docker compose up -d --build
```

> 회원 · 차량 · 정비 기록이 모두 지워지므로 회원가입부터 다시 한다.
