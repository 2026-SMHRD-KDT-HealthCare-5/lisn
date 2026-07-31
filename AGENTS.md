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
