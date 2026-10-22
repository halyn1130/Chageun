# 실습 예제 구성

기존 project 폴더에서 빈칸을 완성한 예제 코드를 복사했습니다. 원본은 보존했습니다.

- workplace/: Java 회원가입·로그인·JWT, MariaDB 예제
- voice-ai_code/: FastAPI STT·TTS·음성 통번역 예제
- rag-code-template_ext/: PDF·웹 자료 기반 RAG 예제
- intro_main.html, internal_index.html, external_index.html: 강의 예제 화면
- run_examples.py: 예제 서버 실행 도우미

## 로컬 실행 준비

Python 가상환경과 패키지를 새로 설치합니다. Java 예제에는 JDK 17 이상과 MariaDB가 필요합니다. Gradle Wrapper는 포함했습니다.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-examples.txt
cp .env.example .env
```

.env에 실제 API 키, DB 비밀번호, Java/Python 공통 JWT 비밀키를 설정하세요. 실제 비밀키는 복사하지 않았습니다. MariaDB는 기존 예제 설정인 localhost:53301/sql_db를 사용합니다. 새 DB에서는 Java 예제의 테이블 정의를 참고해 users 테이블을 준비하세요. DB 내용은 이번 복사에 포함되지 않습니다.

```sh
.venv/bin/python run_examples.py auth voice rag
```

- 인증: http://localhost:8080/login
- 음성: http://localhost:8008
- RAG: http://localhost:8001

기존 폴더의 서버가 같은 포트에서 실행 중이면 먼저 종료해야 새 폴더의 코드가 실행됩니다. 실행 도우미는 사용 중인 포트를 건너뜁니다.

FAISS 인덱스는 제외했으므로 PDF 업로드 또는 자료 수집 후 다시 생성해야 합니다. internal_index.html은 화면 예제만 있으며, 대응하는 Internal RAG 백엔드는 원본 폴더에도 없습니다.

## 제외한 항목

강의 PDF·강의록, 기획서·로고·목업, 임시 작업 파일, 가상환경, 빌드 결과·캐시, 녹음·합성 음성, 생성된 검색 인덱스, 실제 .env.

현재 코드는 교육용 예제입니다. 차근의 지도·차량 관리·음성 명령 통합 기능은 아직 구현되지 않았습니다. 복사 후 파일 동일성과 Python 구문만 확인했으며 새 폴더에서 서버 실행은 검증하지 않았습니다.
