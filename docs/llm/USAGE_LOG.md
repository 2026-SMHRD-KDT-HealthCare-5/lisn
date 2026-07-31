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
