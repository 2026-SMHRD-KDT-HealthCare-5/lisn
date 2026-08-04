# AGENTS.md

## LLM·프롬프트 작업 규칙

OpenAI API, LLM 프롬프트, 챗봇 대화 상태·요약, 페르소나, 위기 탐지, 안전장치와 관련된
코드나 문서를 변경하기 전에 반드시 다음 순서로 작업합니다.

1. [`docs/llm/PROMPT_REFERENCE.md`](docs/llm/PROMPT_REFERENCE.md)를 읽습니다.
2. [`docs/llm/USAGE_LOG.md`](docs/llm/USAGE_LOG.md)의 최신 관련 항목을 검색합니다.
3. OpenAI 기능·API 계약은 `openaiDeveloperDocs` MCP의 최신 공식 문서를 먼저 확인합니다.
   MCP를 사용할 수 없으면 OpenAI 공식 도메인만 검색하고, Cookbook은 구현 예제로 사용합니다.
4. Claude 전용 동작은 Anthropic 공식 문서를 우선하며, DAIR.AI·Learn Prompting·prompts.chat은
   개념·위협 사례·아이디어 보조 자료로만 사용합니다.
5. 구현 전에 성공 조건과 대표 평가 사례를 정하고, 구현 후 같은 사례로 검증합니다.
6. 참고 자료에서 실제로 채택하거나 거부한 방법과 검증 결과를
   `docs/llm/USAGE_LOG.md` 맨 위에 기록합니다.

커뮤니티 프롬프트를 검증 없이 복사하지 않습니다. 의료적 안전, 위기 대응, 접근 통제는
프롬프트만으로 보장하지 말고 서버 검증·정책·테스트를 함께 둡니다. 사용자에게 숨은
Chain-of-Thought를 출력하도록 요구하지 말고, 필요한 결론·근거·검증 가능한 필드만 요청합니다.

---

## LLM 공급자 — 되돌리면 안 되는 것

`.env` 의 `LLM_PROVIDER` 로 **Gemini(임시) ↔ OpenAI(정본)** 를 갈아탑니다. 아래 넷은
겉보기에 이상해 보이지만 전부 의도한 것입니다.

| 코드 | 되돌리면 안 되는 이유 |
|---|---|
| **OpenAI 경로 유지** | Gemini 는 임시 수단입니다. 산출 문서(기획서·요구사항정의서 `MLCM_310`/`MLCM_320`)의 "외부 OpenAI API" 가 정본이고 **문서는 고치지 않습니다.** 지우면 문서와 실제가 어긋납니다 |
| **Chat Completions 사용** | Gemini 는 OpenAI 호환 엔드포인트지만 **Responses API 를 지원하지 않습니다.** 양쪽을 통일하려고 맞췄습니다 |
| **작업마다 다른 모델** | 무료 한도가 **모델별**입니다. 특히 `reply`·`crisis` 는 `analyze_and_reply` 에서 동시 호출되므로 같은 모델을 쓰면 서로 한도를 먹습니다 |
| **`max_retries=0`** | 무료 티어는 모델이 통째로 503 이 되는 일이 있고, 기본 재시도(2회)면 죽은 모델 하나가 `NFR-DV-001` 3초 예산을 통째로 먹습니다(**실측 13.95초**) |

**쓰면 안 되는 모델** — `gemini-3.5-flash`(503 UNAVAILABLE) · `gemini-2.5-pro`(429, 무료 한도 없음).
실측값은 [`docs/llm/USAGE_LOG.md`](docs/llm/USAGE_LOG.md) LLM-004.

---

## 위기 탐지는 비즈니스 서버에 둡니다

`NFR-DV-003` 이 **외부 API 장애 시에도 키워드 필터 단독 동작**을 요구합니다. AI 추론
서버로 옮기면 그 서버가 죽을 때 위기 탐지가 같이 죽습니다. API 명세 초안에 있던
`POST /internal/analyze/crisis` 는 그래서 철회됐습니다.

`risk_level_of()`(`ai/server/main.py`)는 모델이 아니라 **정책**(데이터베이스요구사항분석서 6항)입니다.
`_predict()` 를 교체할 때 같이 들어내지 마세요. 비즈니스 서버가 이 계산을 다시 하면
규칙이 두 곳에 생겨 반드시 어긋납니다.
