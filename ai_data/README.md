# 차근 AI · 데이터 (`ai_data/`)

차량 설명서와 도로교통법을 근거로 답하는 RAG 모듈과 rag 서버입니다. Docker Compose의 `rag` 서비스가 이 폴더를 빌드해 띄우고, api-server만 내부 주소(`http://rag:8001`)로 호출합니다.

## 한눈에 보기

```
질문 ─▶ 라우터(LLM 도구 선택 + 규칙 가드) ─▶ 검색(FAISS + BM25, 차량 필터) ─▶ LLM 재정렬(15→8)
     ─▶ 답변 LLM(근거 문장 ID 인용) ─▶ 검증 LLM(근거 밖 문장 거름) ─▶ 답변 + 출처 + 원문 문장
```

- **라우터** (`agent.py`): 도구 6개 중 하나를 고릅니다.
  - `search_manual`, `search_law`: 설명서·법령 검색
  - `maintenance_due`, `open_maintenance`: 정비 주기 계산, 내 차 화면 열기
  - `ask_missing_detail`: 되묻기
  - `decline`: 범위 밖 질문 거절
  - 규칙 가드가 라우터의 잘못된 선택을 바로잡습니다.
    - 경고등 질문이 `decline`으로 가면 설명서 검색으로 돌립니다.
    - 상황을 말로 설명한 도로 질문("점선인데 바꿔도 돼?")은 법령 검색으로 돌립니다.
    - 상황 설명이 없는 질문("지금 가도 돼?")은 상황을 되묻습니다.
- **검색** (`core.search`): FAISS(의미)와 BM25(글자 2-gram)를 RRF로 합칩니다. 설명서는 등록 차량의 제조사·모델·연식·파워트레인으로 먼저 거릅니다. `RAG_RERANK=1`이면 후보 15개를 LLM이 다시 정렬해 8개를 씁니다.
- **답변** (`core.answer_from_hits`):
  - 답변 LLM은 문장을 복사하지 않고 근거 문장 ID(`c1.3`)만 인용합니다. 그래서 출처를 지어낼 수 없습니다.
  - 검증 LLM이 답변과 음성 문장을 근거와 대조합니다. 떨어지면 피드백을 붙여 한 번 다시 시도하고, 그래도 떨어지면 `not_found`를 반환합니다.
- **대화 기록**: rag 서버는 상태를 갖지 않습니다. api-server가 `conversation_id`별 최근 6줄(3턴)을 DB에서 꺼내 `history`로 보내고, 라우터가 후속 질문인지 판단해 씁니다.

## 응답 형식 (`POST /rag-query`)

| 필드 | 내용 |
|---|---|
| `status` | `answered` · `need_clarification` · `need_vehicle` · `not_found` · `out_of_scope` 등 |
| `answer`, `speech_text` | 화면용 답변, 음성으로 읽을 답변 |
| `sources[]` | `title`, `page`(조문·인쇄 쪽·섹션), `url`(공식 원문), `quotes`(검증을 통과한 근거 문장, 최대 4개) |
| `needs_review`, `handoff` | 법령 근거 없음(검토 필요), 설명서 근거 없음(정비소·고객센터 안내) |
| `action`, `missing_fields` | 내 차 화면 열기 등 화면 동작, 되묻기에 필요한 항목 |

`quotes`는 표나 PDF 줄바꿈 때문에 잘린 줄을 그 줄이 속한 항목(`·` 글머리, `①` 항) 단위로 이어 붙인 문장입니다. 긴 설명서 문단은 인용한 문장만 남깁니다(`core.evidence_passage`).

## 데이터와 인덱스

등록 문서는 `data/registry.json`에 있습니다. PDF 원본(`data/raw/`)과 인덱스(`data/indexes/`)는 Git에 없으니 팀에서 따로 공유받아 같은 경로에 둡니다.

| 문서 | 청크 (`v14-figures`) | 청크 나누는 방식 |
|---|---|---|
| 기아 K5 (DL3) 2026 사용 설명서 | 763 | 섹션 머리말 기준, 최대 1,000자. 청크 끝에 홀로 남은 제목은 다음 청크로 옮김 |
| 현대 아반떼 (CN7) 2026 취급설명서 | 508 | 위와 같음 |
| K5 설명서 그림 설명 (보충) | 40 | 항목 1개 = 1쪽 = 청크 1개 |
| 아반떼 설명서 그림 설명 (보충) | 37 | 위와 같음 |
| 도로교통법 · 시행령 · 시행규칙 | 375 · 186 · 310 | 조문 단위 |
| 시행규칙 별표 2(신호) · 별표 6(안전표지) | 40 · 217 | 표의 행 단위 |
| 자동차 성능기준 규칙 별표 2 | 7 | 페이지 단위(`chunking: page`) |
| **합계** | **2,483** | |

- **그림 설명 PDF**: 설명서 그림(레버·버튼 위치 등)을 RAG가 읽지 못해서, 그림을 보고 글로 옮긴 비공식 보충 자료입니다. 위치는 운전석 기준이고, 그림으로 판단할 수 없는 내용은 "확인 불가"로 적었습니다.
- **경고등 사전** `data/warning_lights.json`(35개): 경고등 이름, 두 설명서의 다른 표기, 운전자가 아이콘을 묘사하는 말(주전자 모양 등)이 들어 있습니다. 청크 태깅과 라우터가 함께 씁니다.
- **청크 ID**는 문서 ID·버전·PDF 해시·페이지·내용으로 정해집니다. 내용이 바뀌면 ID도 바뀌니, 평가셋의 정답 ID를 다시 확인해야 합니다.

### 인덱스 버전

| 폴더 | 내용 | 상태 |
|---|---|---|
| `v13c-headings` | 설명서 2종 + 법령, 청크 끝 제목 이동 (2,406) | `v14-figures`의 기준본. 지우지 말 것 |
| `v14-figures` | `v13c-headings` + 그림 설명 77개 (2,483) | **rag 기본값** (`infra/docker-compose.yml`) |

인덱스 폴더는 덮어쓰지 않습니다. 이미 있으면 오류가 나니 새 버전 이름을 씁니다. `manifest.json`의 해시로 무결성을 검사합니다.

## 실행

Python 3.11, 저장소 루트의 `.env`(`OPENAI_API_KEY`, `JWT_SECRET`)가 필요합니다.

```sh
python -m venv .venv && source .venv/bin/activate
pip install -r ai_data/requirements.txt
cd ai_data
python -m unittest discover -s tests      # 키·네트워크 없이 72개
```

### rag 서버

서비스로는 **저장소 루트**에서 띄웁니다.

```sh
docker compose up -d --build rag
```

`infra` 폴더에서 실행하면 compose 프로젝트 이름이 달라져 rag가 하나 더 생기고, api-server는 예전 rag를 계속 부릅니다. rag 코드는 이미지에 복사되므로, 코드를 고친 뒤에는 `--build`가 필요합니다.

| 환경 변수 | 기본값 | 내용 |
|---|---|---|
| `RAG_INDEX` | `data/indexes/v14-figures` (compose) | 읽을 인덱스 폴더 |
| `RAG_LLM_MODEL` | `gpt-4o-mini` | 라우터·답변 기본 모델 |
| `RAG_ANSWER_MODEL` | (없음) | 답변만 다른 모델로 |
| `RAG_VERIFY_MODEL` | `gpt-4o` (compose) | 검증 모델. mini는 근거 있는 답변도 떨어뜨림 |
| `RAG_RETRY_MODEL` | `gpt-4o` (compose) | 검증에서 떨어진 답변의 재시도 모델 |
| `RAG_RERANK` | `1` (compose) | LLM 재정렬 사용 (질문당 약 +1초) |
| `RAG_TIMEOUT_S` | `30` | 서버 자체 시간 제한 (api-server는 35초 대기) |

로컬에서 직접 띄우려면: `RAG_INDEX=data/indexes/v14-figures uvicorn chageun_ai.server:app --port 8001`

### CLI (`python -m chageun_ai …`)

| 명령 | 용도 |
|---|---|
| `ingest` | registry의 모든 PDF를 청크로 (`data/processed/chunks.jsonl`) |
| `build --index <새 폴더>` | 청크를 임베딩해 인덱스 생성 (OpenAI 비용 발생) |
| `search` · `answer` | 필터를 직접 주고 검색·답변 확인 (`--filters '{"kind":"law"}'`) |
| `ask` | 서비스와 같은 경로(라우터 포함)로 질문. `--vehicle`로 차량 지정 |
| `evaluate` · `evaluate-answers` | 평가셋으로 검색(Hit·Recall·MRR)·답변 평가 |
| `respace <doc_id>` | 띄어쓰기가 빠진 별표 표를 한 번 복원 (공백만 바뀌는지 검사) |

### 문서를 추가할 때

전체를 다시 임베딩하지 않고 새 문서만 붙인 새 버전을 만듭니다. 기존 청크 ID와 벡터는 그대로입니다.

1. PDF를 `data/raw/`에 넣고 `data/registry.json`에 항목을 추가합니다. 필수값은 `doc_id`, `title`, `kind`, `source_url`(공식 HTTPS), `retrieved_at`, `revision`, `file`, `usage_note`입니다. 설명서는 `manufacturer`, `model`, `model_year`, `powertrain`도 필요합니다.
2. 설명서는 쪽마다 첫 줄이 `[PDF n] 대분류 > 소분류`(또는 `[p.x-y · PDF n] …`) 형식이어야 섹션으로 인식됩니다.
3. 먼저 확인용으로 돌린 뒤, 새 버전 폴더로 만듭니다.

```sh
python scripts/add_documents_index.py --base data/indexes/v14-figures --doc-ids <새 doc_id> --dry-run
python scripts/add_documents_index.py --base data/indexes/v14-figures --doc-ids <새 doc_id> --out data/indexes/<새 버전>
```

4. `infra/docker-compose.yml`의 `RAG_INDEX` 기본값을 바꾸고, 새 인덱스 폴더와 PDF를 팀에 공유합니다.

## 폴더

| 경로 | 내용 |
|---|---|
| `chageun_ai/core.py` | 문서 검증, PDF 추출, 청킹, 인덱스, 검색, 재정렬, 답변, 검증 |
| `chageun_ai/agent.py` | 라우터·가드, 경고등 확인 대화, 응답 형식 |
| `chageun_ai/server.py` | FastAPI 서버(`/health`, `/rag-query`), JWT 확인, 모델 설정, 사용량 로그 |
| `chageun_ai/maintenance.py`, `maintenance_rules.json` | 정비 주기 계산 (검토한 설명서 표 기준, LLM 없이) |
| `scripts/` | 인덱스 보정·문서 추가(`carry_headings_index.py`, `add_documents_index.py`), 사용량 요약(`usage_report.py`) |
| `evaluation/cases.json` | 평가 질문 44개 (RAG 23개 등, 모두 `draft`) |
| `evaluation/experiments/` | 검색 개선 실험 01~03 기록. 03(LLM 재정렬)만 서비스에 반영 |
| `tests/` | 오프라인 테스트 72개 |
| `TEAM_HANDOFF.md` | 역할별 인계 메모 |

## 한계

- **평가셋이 아직 검토 전**(`draft`)입니다. 실험 수치는 잠정치이고, 답변 정확성은 사람이 따로 확인해야 합니다.
- **같은 질문도 실행마다 결과가 조금씩 다를 수 있습니다.** 재정렬과 검증을 LLM이 하기 때문입니다.
- **알려진 실패**:
  - "빨간불인데 우회전해도 돼?"에서 "정지 후 방해하지 않으면 우회전 가능"이라는 예외가 빠집니다.
  - 사고 대화 중 "빨간불인데 그냥 갔어"에 맥락을 쓰지 않고 신호등인지 계기판인지 되묻습니다.
- **그림 설명은 비공식 자료**입니다. 시동 버튼의 좌우처럼 그림으로 확정하지 못한 위치가 있고, 답변이 그 "확인 불가"를 함께 전하지는 않습니다.
- **원본 PDF가 다를 수 있습니다.** 설명서 원본은 공식 웹 매뉴얼·PDF를 변환한 것이고, `manual_scope_filter_v1`로 서비스 범위 밖 구간(그림 목차 등)을 뺐습니다.
