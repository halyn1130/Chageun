# 차근 AI · 데이터 작업 기반

유하린·변현준·서준영이 프론트/백엔드 API 명세와 독립적으로 작업하는 폴더입니다. 기존 강의 예제는 수정하지 않습니다. HTTP 서버, 인증, 지도, 음성 입출력, 개인 차량 DB는 포함하지 않습니다.

## 현재 구현과 한계

| 구현한 것 | 아직 필요한 것 |
|---|---|
| 문서 등록 규격, PDF 페이지별 추출·청킹 | 공식 PDF 수집 및 사람이 이용조건·적용 범위 확인 |
| 원본 해시·안정적인 청크 ID·출처 메타데이터 | 표/경고문/조항 단위 파싱, OCR, 인쇄 페이지 매핑 |
| 문서들을 함께 적재한 버전별 FAISS 저장소 | 실제 문서로 임베딩 생성 및 검색 품질 측정 |
| 차종·연식·파워트레인 사전 필터 검색 | 설명서별 적용 연식/트림/동력계통 규칙 확정 |
| 근거 기반 LLM 답변 함수 및 출처 ID 검증 | 실제 LLM 호출 검증, 답변 사실성·충분성 사람 평가 |
| 24개 평가 시나리오 초안 및 검색 평가 코드 | 정답 문서/청크 지정, 정답 작성·검토 |
| 독립 CLI와 8개 오프라인 테스트 | 의도 분류·Tool Calling·대화 이력·백엔드 연결 |

실제 PDF와 정답셋은 아직 없습니다. `data/registry.json`은 의도적으로 비어 있으며, 예제 등록 양식의 자리표시자를 실제 데이터로 취급하지 않습니다. 테스트 자료는 가상 데이터입니다. 실제 도로교통법 내용이나 차량 정비 수치는 작성하지 않았습니다.

## 폴더

- `data/source_inventory.csv`: 수집 범위와 미결정 사항
- `data/registry.example.json`: 법규·차량 문서 등록 양식
- `data/registry.json`: 검토를 마친 문서만 등록하는 운영 목록
- `data/raw/`: 수집한 PDF (Git 제외)
- `chageun_ai/core.py`: 데이터 검증·추출·청킹·검색·답변·평가 함수
- `chageun_ai/__main__.py`: 실행 CLI
- `evaluation/cases.json`: 24개 질문과 기대 동작 초안
- `evaluation/REVIEW_GUIDE.md`: 정답 검토·실패 분류 기준
- `TEAM_HANDOFF.md`: 역할별 다음 작업과 민솔 명세에 연결할 경계
- `tests/test_core.py`: 키·외부 API 없이 실행하는 테스트

## 공통 데이터 규격 v1

문서 공통 필수값: `doc_id`, `title`, `kind`, `source_url`, `retrieved_at`, `revision`, `file`, `usage_note`.

- `kind=law`: `effective_date` 필수. 이번 버전에서 사용할 시행일과 개정판을 사람이 확인합니다. 같은 법령의 과거·현재 버전을 함께 등록하지 않거나 `doc_id`/`revision`/`effective_date`를 명시하여 검색합니다. 최신 법령을 자동 확인하지 않습니다.
- `kind=manual`: `manufacturer`, `model`, `model_year`, `powertrain` 필수. `model`은 `K5` 또는 `디 올 뉴 아반떼`. 실제 지원 연식과 동력계통은 팀에서 확정합니다. 여러 연식에 적용되는 문서의 범위 규격은 후속 설계 대상입니다.
- `source_url`: PDF를 확인한 공식 출처. HTTPS 형식 검사는 공식성/사용권 확인을 대신하지 않습니다. 수집 담당자가 출처와 이용조건을 확인해 `usage_note`에 기록합니다.
- 청크: `schema_version`, `chunk_id`, `text`, `metadata`.
- 추가 메타데이터: `pdf_page`는 1부터 시작하는 **PDF 파일 순서**, `printed_page`는 책에 인쇄된 페이지입니다. 현재는 `printed_page`, `article`, `section`이 null이며 추측하지 않습니다.
- 설명서 청크 메타데이터(검색 힌트, 청크 ID·본문에는 영향 없음): `topic`(`warning_light`·`lcd_message`·`maintenance`·`emergency`·`feature`, 섹션 경로로 분류), `lights`(본문에 나오는 경고등 ID 목록), `maintenance_items`(정비 항목 코드, maintenance·emergency 청크만), `content_role`(K5 요약본이면 `summary`, 그 외 `detail`).
- 경고등·표시등 사전: `data/warning_lights.json`. 경고등마다 `id`, 대표 이름 `name`, 두 설명서의 다른 표기 `aliases`, 운전자가 아이콘을 묘사하는 말 `shapes`. 청크의 `lights` 태깅과 `agent.WARNING_LIGHTS`(모양으로 경고등 찾기)가 이 파일을 함께 읽습니다. 이름은 공백을 빼고 비교하며 중복되면 로드 시 오류가 납니다.
- 청크 ID는 문서 ID·버전·PDF 해시·페이지·텍스트 위치·내용으로 결정됩니다. PDF/청킹 변경 시 평가용 정답 ID도 재검토합니다.

현재 청킹은 페이지 경계를 지키는 최대 900자/120자 중첩 방식입니다. 페이지 안 줄바꿈을 우선하지만 **조항·표·정비 항목 단위 의미 청킹이 완성된 것은 아닙니다**. 빈 페이지는 보고서에 남깁니다. 텍스트가 전혀 없는 PDF는 오류 처리합니다. 짧은 텍스트/표 추출 누락/그림 속 경고는 사람이 확인해야 합니다.

## 실행

Python 3.10 이상에서 프로젝트 루트에 가상환경을 준비한 다음 실행합니다. 기존 설치 환경과 동일한 핵심 패키지 버전을 사용합니다.

```sh
# mini-project 폴더에서
python3 -m venv .venv
.venv/bin/python -m pip install -r ai_data/requirements.txt
cd ai_data
../.venv/bin/python -m unittest discover -s tests -v
```

1. 공식 PDF를 `data/raw/`에 넣고 실제 값으로 `data/registry.json`을 작성합니다. 파일 경로는 registry.json이 있는 폴더 기준입니다.

```sh
../.venv/bin/python -m chageun_ai ingest
```

결과는 `data/processed/chunks.jsonl`과 `ingestion_report.json`입니다. 적재는 등록된 모든 문서를 한 번에 처리합니다. PDF 업로드마다 기존 문서를 덮는 강의 예제 방식과 다릅니다. 전처리 결과는 다시 실행하면 갱신되므로, 배포 버전은 별도 `--out` 경로를 사용하세요.

2. 임베딩·검색·답변에는 mini-project 루트 `.env`의 `OPENAI_API_KEY`가 필요합니다. 다음 명령은 외부 API 호출과 비용이 발생합니다. 키는 Git에 넣지 않습니다.

```sh
../.venv/bin/python -m chageun_ai build --index data/indexes/v001
../.venv/bin/python -m chageun_ai search '정차와 주차의 차이' --index data/indexes/v001 --filters '{"kind":"law"}'
../.venv/bin/python -m chageun_ai answer '정차와 주차의 차이' --index data/indexes/v001 --filters '{"kind":"law"}'
```

이미 있는 인덱스 디렉터리는 덮어쓰지 않습니다. 인덱스·청크 파일 해시, 임베딩 모델, 차원, 개수를 저장하고 검색 시 무결성을 검사합니다. 본인이 만든 신뢰할 수 있는 인덱스만 사용하세요.

차량 검색에는 아래 다섯 필드가 모두 필요합니다. `선택한 연식`, `선택한 파워트레인`은 실제 등록 값으로 바꿉니다.

```sh
../.venv/bin/python -m chageun_ai search '엔진오일 점검 방법' --index data/indexes/v001 --filters '{"kind":"manual","manufacturer":"기아","model":"K5","model_year":"선택한 연식","powertrain":"선택한 파워트레인"}'
```

차량 정보를 모를 때 아무 설명서나 검색하지 않습니다. 상위 서비스에서 추가 질문을 한 뒤 필터를 전달해야 합니다. 필터를 먼저 적용한 후 코사인 유사도 순으로 검색합니다. 유사도 점수는 정답 확률이 아니며 자동 정답 판정에 사용하지 않습니다.

3. 근거를 검토해 `evaluation/cases.json`의 RAG 질문에 `expected_chunk_ids`, `reference_answer`, `reviewer`, 실제 필터 값을 넣고 `status`를 `reviewed`로 바꿉니다.

```sh
../.venv/bin/python -m chageun_ai evaluate --index data/indexes/v001
```

정답 검토가 끝난 RAG 질문만 Hit Rate, 평균 Recall, MRR로 평가합니다. 초안과 지도·차량 DB·대화 시나리오는 pending으로 남습니다. 평가 0건이면 점수는 null입니다. 이 수치는 **검색 평가**이며 답변 사실성 점수가 아닙니다.

## 답변 모듈의 내부 반환값

`answer_from_hits(question, hits, generate)`는 `status`, `answer_text`, `speech_text`, `sources`를 반환합니다. HTTP API 명세가 아니며 민솔의 명세에 맞춰 어댑터에서 변환합니다.

- `answered`: 모델이 선택한 청크 ID가 검색 결과에 모두 존재함을 확인한 경우.
- `insufficient_evidence`: 검색 결과 없음, 근거 부족, JSON 형식 오류, 존재하지 않는 출처 ID 등. 모델의 임의 출처는 전달하지 않습니다.
- 실제 페이지/URL/차종은 저장된 메타데이터에서 가져옵니다.
- 유효한 출처 ID가 답변 전체의 사실성을 보증하지 않습니다. 인용 내용의 적합성·누락·과도한 단정은 평가셋과 사람이 확인해야 합니다.
- 모델/네트워크 호출 실패는 예외로 전달됩니다. 서비스 어댑터가 재시도·오류 응답으로 처리해야 하며 정답처럼 숨기지 않습니다.
- 대화 상태나 개인 차량 이력은 이 모듈에 저장하지 않습니다.

## 검증 상태

오프라인 테스트 8개 통과: 페이지 보존·ID 안정성, 차량 규격 누락, 잘못된 차종 혼입 방지, 인덱스 변조 검사, 버전 덮어쓰기/잘못된 벡터 방지, 허위 출처/형식 오류 처리, 미검토 평가 제외, 이미지 PDF 실패 처리.

실제 공식 문서 수집, 실제 임베딩·LLM 호출, 서비스 통합 성능은 아직 검증하지 않았습니다.
