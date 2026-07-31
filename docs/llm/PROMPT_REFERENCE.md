# LLM 프롬프트·API 참고자료

> 검증일: 2026.07.31
>
> 적용 범위: OpenAI API, 챗봇, 세션 요약, Structured Outputs, 페르소나, 위기 탐지,
> 프롬프트 인젝션 및 안전장치

이 문서는 참고자료의 “절대 순위”가 아니라 작업별 신뢰 순서를 정합니다. API와 모델 동작은
빠르게 바뀌므로, 아래 내용을 기억만으로 적용하지 말고 작업 시점의 공식 문서를 다시 확인합니다.

## 결론

원문의 큰 방향은 맞지만 다음 세 가지는 바로잡아야 합니다.

1. OpenAI API 구현의 정본은 Cookbook이 아니라 **OpenAI API 공식 문서와 API 명세**입니다.
   Cookbook은 공식 실전 예제 모음으로 그다음에 사용합니다.
2. Anthropic 자료의 “최고봉”, “엉뚱한 답변 방지” 같은 표현은 객관적으로 검증할 수 없습니다.
   Claude 전용 프롬프트에는 유용하지만 OpenAI 모델 동작의 근거로 쓰지 않습니다.
3. Learn Prompting의 방어 기법이나 네거티브 프롬프트만으로 의료 안전·탈옥 방지가 보장되지
   않습니다. 서버 검증, 권한, 입력·출력 필터, 위기 대응 규칙, 평가 테스트가 함께 필요합니다.

## 작업별 우선순위

| 작업 | 1순위 | 보조 자료 | 주의 |
|---|---|---|---|
| OpenAI API 스키마·파라미터 | OpenAI API 공식 문서·API 명세 | OpenAI Cookbook | 예제의 모델명·SDK 문법이 오래됐을 수 있음 |
| Structured Outputs | OpenAI 공식 Structured Outputs 가이드 | Cookbook 입문 예제 | JSON mode와 JSON Schema 준수를 혼동하지 않기 |
| 대화 상태·요약 | OpenAI 공식 Conversation state·Compaction 가이드 | Cookbook 요약 예제 | 장문 문서 요약과 대화 메모리 설계는 다른 문제 |
| 지연·재시도·오류 | OpenAI 공식 Latency·Rate limits·Error codes | Cookbook rate-limit 예제 | 프롬프트만 줄인다고 전체 지연이 해결되지는 않음 |
| 일반 프롬프트 구조 | 사용 모델 제공사의 공식 가이드 | DAIR.AI Prompting Guide | 기법을 이름만 보고 도입하지 말고 평가로 비교 |
| Claude 프롬프트 | Anthropic Prompting best practices | DAIR.AI | Claude 전용 XML·역할 팁을 타 모델 규칙으로 일반화하지 않기 |
| 인젝션·탈옥 위협 학습 | 제공사 공식 안전 문서 | Learn Prompting | 단일 방어법을 안전 보장으로 취급하지 않기 |
| 페르소나 아이디어 | 제품 요구사항·직접 작성한 명세 | prompts.chat | 커뮤니티 품질이 균일하지 않아 복사 사용 금지 |

## 사이트별 검증

### 1. OpenAI Cookbook

- 현재 `cookbook.openai.com`의 주요 예제는 `developers.openai.com/cookbook`으로 연결됩니다.
- Structured Outputs, rate limit 처리, 장문 요약 등 Python 중심의 공식 예제가 실제로 있습니다.
- 따라서 “실무 코드 기반 레퍼런스”라는 평가는 타당합니다.
- 다만 API 계약, 최신 파라미터, 지원 모델은 공식 API 가이드·명세를 먼저 확인해야 합니다.
- 장문 문서 요약 예제가 곧바로 “대화 세션 요약의 완성된 모범답안”을 뜻하지는 않습니다.

참고:

- [OpenAI Cookbook](https://developers.openai.com/cookbook)
- [Structured Outputs 예제](https://developers.openai.com/cookbook/examples/structured_outputs_intro)
- [Rate limit 처리 예제](https://developers.openai.com/cookbook/examples/how_to_handle_rate_limits)
- [장문 요약 예제](https://developers.openai.com/cookbook/examples/summarizing_long_documents)
- [Structured Outputs 공식 가이드](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Conversation state 공식 가이드](https://developers.openai.com/api/docs/guides/conversation-state)
- [Latency optimization 공식 가이드](https://developers.openai.com/api/docs/guides/latency-optimization)

### 2. DAIR.AI Prompt Engineering Guide

- 한국어 경로(`/kr`)가 실제로 제공됩니다.
- Few-shot, Chain-of-Thought, prompt chaining, RAG, prompt injection, jailbreaking 등 개념과
  예제가 폭넓게 정리되어 있어 개념 학습용이라는 평가는 타당합니다.
- 다만 특정 모델의 최신 권장 방식은 해당 제공사의 공식 가이드가 우선입니다.
- Chain-of-Thought는 학습할 개념이지, 운영 프롬프트에서 숨은 추론 전문을 출력하라고
  요구하는 기본 규칙이 아닙니다. 필요한 경우 짧은 근거·검증 결과·구조화된 필드를 요청합니다.

참고:

- [Prompt Engineering Guide](https://www.promptingguide.ai/)
- [한국어판](https://www.promptingguide.ai/kr)

### 3. Anthropic Prompting 자료

- 기존 Prompt Library URL은 현재 Claude의 살아 있는 `Prompting best practices` 문서로
  이동합니다.
- 공식 문서는 명확한 지시, 예시, XML 구조, 역할 부여, 출력 제어, 평가 선행을 다룹니다.
- 페르소나와 톤 설계에 참고할 수 있지만 “업계 최고”라는 순위는 주관적입니다.
- LISN이 OpenAI API를 호출한다면 Anthropic 자료는 구조 아이디어용이며, 최종 동작은
  OpenAI 공식 문서와 실제 모델 평가로 확인합니다.

참고:

- [Claude Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
- [Claude Prompt engineering overview](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview)

### 4. Learn Prompting

- 프롬프트 인젝션, 탈옥과 다양한 방어 기법을 다루므로 위협 사례를 학습하는 데 유용합니다.
- 그러나 “의학적 진단 금지와 위험 정보 차단에 특화된 완성형 Guardrails 자료”라는 표현은
  과장입니다. 도메인별 의료 정책과 실제 애플리케이션 통제는 별도로 설계해야 합니다.
- post-prompting 같은 개별 기법도 우회될 수 있으므로 다층 방어의 한 요소로만 취급합니다.

참고:

- [Learn Prompting](https://learnprompting.org/docs/introduction)
- [Prompt injection 방어 개요](https://learnprompting.org/docs/prompt_hacking/defensive_measures/introduction)

### 5. Awesome ChatGPT Prompts

- 저장소는 현재 `prompts.chat`으로 확장·개명되었고, 기존 GitHub URL은 계속 접근됩니다.
- 다양한 역할·페르소나 아이디어를 찾는 용도라는 평가는 타당합니다.
- 커뮤니티 자료이므로 정확성·안전성·최신성이 균일하지 않습니다. 문장을 그대로 제품 시스템
  프롬프트에 복사하지 않고 요구사항에 맞게 재작성한 뒤 평가합니다.

참고:

- [prompts.chat GitHub 저장소](https://github.com/f/awesome-chatgpt-prompts)
- [prompts.chat](https://prompts.chat/)

## LISN 적용 원칙

프롬프트 관련 구현은 다음 순서로 진행합니다.

1. 기능의 성공 조건과 실패 조건을 먼저 작성합니다.
2. 현재 사용하는 모델과 API의 공식 문서를 조회합니다.
3. 출력은 가능한 경우 JSON Schema 기반 Structured Outputs로 제한합니다.
4. 위기 감지는 확정 설계대로 **서버 키워드 규칙 + LLM 문맥 판정**의 두 단계로 유지합니다.
5. 의료 진단 금지, 위기 안내, 개인정보 최소화는 프롬프트와 서버 코드 양쪽에서 검사합니다.
6. 정상·모호·적대적·위기 입력을 포함한 대표 평가 사례를 실행합니다.
7. 채택한 기법, 거부한 대안, 평가 결과를 `USAGE_LOG.md`에 기록합니다.
