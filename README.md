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
| http://localhost:8002/health | `{"status":"ok"}` 나오면 정상 |
| `localhost:3307` | DB (DB 툴 접속용, 사용자 `root`, 비밀번호는 `.env`의 `DB_PASSWORD`) |

> api-server는 현재 **목업**(고정 응답)입니다. API 형식은 노션 API 명세서 참고.

## 끄기 · 초기화

```bash
docker compose down       # 끄기 (DB 데이터 유지)
docker compose down -v    # 끄기 + DB 데이터 삭제 (init.sql 다시 적용)
docker compose logs -f auth-server   # 로그 보기 (서비스 이름: db, auth-server, api-server)
```
