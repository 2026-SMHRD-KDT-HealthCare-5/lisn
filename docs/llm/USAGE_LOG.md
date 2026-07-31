# LLM 참고자료 사용 이력

LLM·프롬프트·OpenAI API 관련 작업을 시작할 때 최신 관련 항목을 먼저 검색합니다. 새 기록은
맨 위에 추가합니다. 단순 열람은 기록하지 않고, 구현이나 설계 판단에 영향을 준 자료만 남깁니다.

## 기록 양식

```markdown
## YYYY-MM-DD · LLM-XXX · 작업명

- 작업 범위:
- 조회한 자료:
- 채택한 방법:
- 채택하지 않은 방법과 이유:
- 성공 조건·평가 사례:
- 검증 결과:
- 반영 파일:
```

---

## 2026-07-31 · LLM-002 · 챗봇 라우터 구현 (페르소나 응답·위기 판정·세션 요약)

- 작업 범위: `backend/app/services/llm.py`, `services/safety.py`, `api/v1/chat.py`,
  `data/crisis_keywords.json` 신규 작성
- 조회한 자료:
  - `openaiDeveloperDocs` MCP → [Structured model outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
    (2026.07.31 조회). Python 예제에서 현재 계약이 **Responses API** 임을 확인:
    `client.responses.parse(model=..., input=[...], text_format=PydanticModel)` →
    `response.output_parsed`. 문서 예제 모델은 `gpt-5.6`
  - 같은 문서의 Structured Outputs 보장 범위 — 공급한 JSON Schema 를 모델이
    반드시 따르므로 파싱 실패 재시도 로직이 불필요
- 채택한 방법:
  - **위기 판정을 Structured Outputs 로 강제.** `CrisisVerdict(is_crisis, severity,
    matched_context)` Pydantic 모델을 `text_format` 으로 넘긴다. 03-B 가 규정한
    반환 스키마와 일치
  - **위기 판정과 응답 생성을 `asyncio.gather` 로 병렬 호출.** 순차면 OpenAI 왕복이
    2회라 `NFR-DV-001` 3초 요건을 넘긴다. `return_exceptions=True` 로 한쪽 실패가
    다른 쪽을 죽이지 않게 함
  - **1차 키워드 필터를 백엔드 내부 로직으로 분리.** `services/safety.py` 는 외부
    API 에 의존하지 않아 OpenAI 장애 시에도 동작한다 — `NFR-DV-003` fallback 근거
  - 키워드 사전을 `app/data/crisis_keywords.json` 으로 분리(03-B "운영 중 갱신 가능")
  - 안전 가이드라인(`SAFETY_RULES`)을 페르소나와 무관하게 시스템 프롬프트에 고정
    — `FR-AI-002`·`FR-AI-005`. 진단 금지, 자해·약물 구체 정보 금지, 미확인 개인정보
    언급 금지, 전문가 상담 권유
  - 위험도→액션 매핑을 **서버에서 확정**해 `action` 필드로 내려보냄
- 채택하지 않은 방법과 이유:
  - **스트리밍(SSE)**: LLM 챗의 실무 표준이지만 위기 판정 전에 흘린 글자를 회수할
    수 없다. `CRITICAL` 일 때 이미 나간 문장이 남으면 안전 기능이 무력화된다
  - **Chat Completions 의 `response_format`**: 공식 문서의 현재 Python 예제가
    Responses API 기준이므로 그쪽을 따랐다
  - **JSON mode**: 스키마 준수를 보장하지 않는다. `PROMPT_REFERENCE.md` 가 경고한
    "JSON mode 와 JSON Schema 준수 혼동" 지점
  - **키워드 사전에 `죽겠다` 포함**: "배고파 죽겠다" 같은 관용 표현 오탐이 과도해
    제외. 대신 `죽고 싶`, `죽어버리` 같은 의도 표현만 넣음
  - **LLM 실패 시 조용히 NORMAL 처리**: 미탐이 발생한다. 키워드 HIGH 가 걸리면
    문맥 판단 없이 CRITICAL 로 본다
- 성공 조건·평가 사례:
  - 일상 발화 → `NORMAL`/`CHAT`
  - 모호한 부정 감정("지쳤고 아무도 없는") → `CAUTION`/`CONTENT`
  - 명확한 위기 발화("다 사라지고 싶어, 죽고 싶다") → `CRITICAL`/`EMERGENCY`
  - `CRITICAL` 일 때 `reply` 가 `null`
  - PII 포함 발화가 마스킹되어 저장
  - **OpenAI 장애 상황에서도 위기 탐지가 동작**
- 검증 결과:
  - 실제 서버(포트 8013)로 4개 사례 전부 기대값 일치
  - `OPENAI_API_KEY` 미설정 상태였으므로 LLM 호출이 전부 실패했는데도
    **키워드 fallback 이 단독으로 위기를 탐지**했고 `source=KEYWORD` 로 표기됨.
    `NFR-DV-003` 이 실증됨
  - PII 마스킹 확인 — `[MASK:전화]` `[MASK:이메일]`
  - ⚠ **LLM 경로(2차 문맥 판정)는 미검증.** API 키 설정 후 재평가 필요.
    특히 관용 표현("배고파 죽겠다")을 LLM 이 걸러내는지 확인해야 함
- 반영 파일: `backend/app/services/llm.py`, `backend/app/services/safety.py`,
  `backend/app/api/v1/chat.py`, `backend/app/schemas/chat.py`,
  `backend/app/data/crisis_keywords.json`, `backend/requirements.txt`

---

## 2026-07-31 · LLM-001 · 프롬프트 참고자료 검증 및 지속 조회 체계

- 작업 범위: 추천 자료 5종의 현재 상태·용도 검증, Codex·Claude 공용 작업 규칙 구성
- 조회한 자료:
  - OpenAI 공식 Structured Outputs·Conversation state·Latency optimization 가이드
  - OpenAI Cookbook의 Structured Outputs·rate limit·장문 요약 예제
  - DAIR.AI 영문·한국어 Prompt Engineering Guide
  - Anthropic Prompting best practices·Prompt engineering overview
  - Learn Prompting의 prompt injection 방어 개요
  - `f/awesome-chatgpt-prompts`의 현재 `prompts.chat` 저장소
  - Codex 공식 매뉴얼의 `AGENTS.md`·Docs MCP 지침
  - Claude Code 공식 문서의 프로젝트 범위 `.mcp.json` 지침
- 채택한 방법:
  - 제공사 공식 문서 → 공식 Cookbook → 교육·커뮤니티 자료 순으로 출처 우선순위 지정
  - LLM 관련 구현 전 참고 문서와 최신 로그 조회
  - 구현 전 성공 조건 정의, 구현 후 대표 사례 평가
  - Codex `AGENTS.md`와 Claude `CLAUDE.md`에 같은 절차 유지
  - OpenAI 공식 Docs MCP를 Codex와 Claude 프로젝트 설정에 등록
- 채택하지 않은 방법과 이유:
  - 사이트 전체의 절대 순위: 작업별 강점과 권위가 달라 단일 순위가 부정확함
  - 커뮤니티 페르소나 원문 복사: 품질과 안전성이 검증되지 않음
  - 네거티브 프롬프트만으로 안전 보장: 의료·위기 기능에는 서버 통제와 테스트가 필요함
  - Chain-of-Thought 전문 출력 요구: 숨은 추론 대신 결론·근거·구조화 필드를 검증함
- 성공 조건·평가 사례:
  - 다음 Codex 세션이 루트 `AGENTS.md`에서 절차를 발견할 수 있음
  - `.mcp.json`이 Claude Code 공식 프로젝트 범위 HTTP 서버 형식과 일치함
  - 두 지침 모두 이 문서와 `PROMPT_REFERENCE.md`를 가리킴
  - JSON·TOML 문법과 Markdown 링크가 유효함
- 검증 결과:
  - JSON·TOML 파싱 통과
  - `codex mcp list`에서 `openaiDeveloperDocs`가 `enabled`로 확인됨
  - Claude CLI는 현재 PC에 없어 런타임 연결은 미검증이며, 새 Claude Code 세션에서 프로젝트
    서버를 한 번 승인한 뒤 `/mcp`로 확인해야 함
  - 지침 간 문서 경로와 Git 추적 상태 확인
- 반영 파일: `AGENTS.md`, `CLAUDE.md`, `.codex/config.toml`, `.mcp.json`,
  `docs/llm/PROMPT_REFERENCE.md`, `docs/llm/USAGE_LOG.md`, `docs/SESSION-HANDOFF.md`,
  `docs/review/작업이력.md`
