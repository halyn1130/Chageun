# Typecast 음성 시험과 롤백

현재 설정은 `ssfm-v30`, `smart`, 한국어, WAV 출력입니다. SDK 예제와 동일한 요청을 기존 httpx로 공식 REST API에 전달합니다. 키는 서버 `.env`에만 보관합니다. STT와 RAG는 변경하지 않습니다.

## 설정

루트 `.env`:

```dotenv
TTS_PROVIDER=typecast
TYPECAST_API_KEY=발급받은키
TYPECAST_VOICE_ID=선택한목소리ID
```

VOICE_ID를 비워두면 공식 SDK 예제의 `tc_672c5f5ce59fac2a48faeaee`를 사용합니다. 계정에서 사용할 수 있는 원하는 목소리 ID로 바꿀 수 있습니다.

`frontend/.env.local`:

```dotenv
VITE_TTS_PROVIDER=typecast
```

```sh
docker compose up -d --build voice-ai
cd frontend
npm run dev
```

이미 Vite가 켜져 있다면 다시 시작합니다. 로그인 후 답변 듣기 버튼으로 시험합니다. 개발 프록시 `/voice/tts`가 8008 서버로 JWT와 읽을 문장을 보냅니다. 서버가 WAV를 반환하면 브라우저에서 재생하고, 음성 대화 중이었다면 재생 종료 후 듣기를 재개합니다. 홈·중지 시 요청과 재생을 취소하고 임시 URL을 해제합니다. 실패 시 기존 목소리로 자동 전환하지 않습니다.

## 즉시 롤백 (화면 수정 유지)

`frontend/.env.local`을 다음으로 바꾸고 Vite를 재시작하면 기존 브라우저 음성으로 돌아옵니다.

```dotenv
VITE_TTS_PROVIDER=browser
```

음성 서버의 기존 OpenAI nova도 복원하려면 루트 `.env`의 `TTS_PROVIDER=openai`로 변경한 뒤 `docker compose up -d --force-recreate voice-ai`를 실행합니다. OPENAI_API_KEY가 필요합니다. 브라우저 음성만 사용할 때는 서버 변경이 필요 없습니다.

기존 UI 변경까지 없애는 `git reset --hard`는 사용하지 않습니다. Typecast 변경 전 소스 백업은 `/Users/halyn/Desktop/project/output/backups/before-typecast-20261024-220017.zip`에 있습니다(비밀키 제외). 신규 remoteSpeech.js 및 테스트는 설정 롤백 시 그대로 두어도 실행되지 않습니다.

## 배포

Vite proxy는 개발 서버용입니다. 정적 배포 시에도 `/voice`를 voice-ai:8008로 전달하는 프록시가 필요합니다. `VITE_TTS_PROVIDER`는 빌드 시 반영되므로 배포본은 다시 빌드합니다. Typecast 무료 플랜은 비상업용 및 출처 표시 조건이 있으며 홈 음성 영역에 출처 링크를 표시합니다.

공식 요청 규격: https://typecast.ai/docs/api-reference/text-to-speech/text-to-speech
