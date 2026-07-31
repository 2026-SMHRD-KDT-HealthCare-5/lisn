"""LLM 호출 — 페르소나 응답 · 위기 문맥 판정 · 세션 요약.

공급자를 **전환할 수 있다**(2026.08.01 PM 확정).

  개발 기본값  Gemini  — 무료 한도. **임시 수단이다.**
  정확도·시연  OpenAI  — .env 에서 LLM_PROVIDER=openai

**산출 문서(01 기획서 · 02 MLCM_310/320)의 "외부 OpenAI API" 는 그대로 정본이다.**
Gemini 는 개발 중 비용을 줄이려는 임시 경로일 뿐이므로 **문서를 고치지 않는다.**
따라서 OpenAI 경로를 죽이면 안 된다 — 문서와 실제가 어긋나게 된다.

계약 근거(2026.08.01 조회):
  https://ai.google.dev/gemini-api/docs/openai
  Gemini 는 OpenAI 호환 엔드포인트를 제공하므로 **SDK 는 openai 를 그대로 쓴다.**
  base_url 과 api_key 만 바꾸면 된다.

  ⚠ **Responses API 는 지원하지 않는다.** Chat Completions 만 된다.
    그래서 responses.parse()  → beta.chat.completions.parse()
           responses.create() → chat.completions.create()
    로 옮겼다. Structured Outputs(Pydantic 스키마 강제)는 그대로 지원되므로
    위기 판정의 스키마 보장은 유지된다 — 파싱 실패 재시도 로직이 필요 없다.

기록: docs/llm/USAGE_LOG.md LLM-004
"""

import asyncio
import logging

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def client() -> AsyncOpenAI:
    """공급자에 맞는 클라이언트. Gemini 도 openai SDK 로 붙는다."""
    global _client
    if _client is None:
        # ⚠ timeout·max_retries 를 반드시 준다. 기본 재시도(2회)를 두면 죽은 모델
        #   하나가 3초 예산(NFR-DV-001)을 통째로 먹는다 — 실측 13.95초.
        #   빨리 포기하고 키워드 fallback(NFR-DV-003) 으로 넘기는 편이 맞다.
        common = {
            "timeout": settings.llm_timeout_seconds,
            "max_retries": settings.llm_max_retries,
        }
        if settings.llm_provider == "openai":
            if not settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY 가 설정되지 않았습니다")
            _client = AsyncOpenAI(api_key=settings.openai_api_key, **common)
        else:
            if not settings.gemini_api_key:
                raise RuntimeError("GEMINI_API_KEY 가 설정되지 않았습니다")
            _client = AsyncOpenAI(
                api_key=settings.gemini_api_key,
                base_url=settings.gemini_base_url,
                **common,
            )
    return _client


def reset_client() -> None:
    """설정을 바꾼 뒤 캐시된 클라이언트를 버린다. 테스트에서 쓴다."""
    global _client
    _client = None


def model_for(task: str) -> str:
    """작업별 모델. 공급자에 따라 달라진다.

    task: "reply" | "crisis" | "summary" | "daily"

    Gemini 는 무료 한도가 **모델별로** 잡히므로 작업마다 다른 모델을 배정해
    쿼터 버킷을 나눈다. 특히 reply·crisis 는 analyze_and_reply 에서 동시에
    호출되므로, 같은 모델을 쓰면 한쪽이 다른 쪽의 RPM 을 잡아먹는다.

    OpenAI 는 유료라 쿼터를 나눌 이유가 없고, **정확도 기준선**으로 쓰는 경로라
    네 작업이 같은 모델을 써야 Gemini 와의 비교가 의미를 갖는다.
    """
    if settings.llm_provider == "openai":
        return settings.openai_model
    return {
        "reply": settings.gemini_model_reply,
        "crisis": settings.gemini_model_crisis,
        "summary": settings.gemini_model_summary,
        "daily": settings.gemini_model_daily,
    }[task]


# --------------------------------------------------------------------------
# 안전 가이드라인 — FR-AI-005. 페르소나와 무관하게 항상 붙는다.
# --------------------------------------------------------------------------
SAFETY_RULES = """
반드시 지킬 것:
- 의학적 진단을 내리지 않는다. 병명을 단정하거나 확진하듯 말하지 않는다.
- 자해·자살 방법, 약물의 종류나 용량 등 위험을 실행하는 데 쓰일 수 있는
  구체적 정보를 어떤 형태로도 제공하지 않는다.
- 사용자가 알려주지 않은 개인정보를 추측해서 언급하지 않는다.
- 힘들어하는 신호가 보이면 전문가 상담을 권한다. 다만 겁을 주거나
  단정적으로 위험하다고 말하지 않는다.
- 한국어로, 2~4문장으로 짧게 답한다.
"""

PERSONA_PROMPTS = {
    # MBTI F형. 감정 수용과 정서적 지지가 중심.
    "FRIEND": """너는 '마음이'라는 이름의 다정한 친구야.
사용자의 감정을 먼저 있는 그대로 받아들이고 따뜻하게 위로해.
해결책을 제시하기보다 "많이 힘들었겠다", "그런 마음이 드는 게 자연스러워"처럼
공감을 먼저 건네. 조언은 사용자가 원할 때만 짧게 덧붙여.
""",
    # MBTI T형. 상황 정리와 실행 가능한 다음 행동이 중심.
    "COUNSELOR": """너는 '마음이'라는 이름의 차분한 상담자야.
사용자의 상황을 객관적으로 정리해주고, 실질적으로 도움이 되는 다음 행동을 제안해.
다만 감정을 무시하지는 마. 먼저 한 문장으로 상황을 인정한 뒤 정리로 넘어가.
사용자가 스스로 판단할 수 있도록 선택지를 제시하는 방식으로 말해.
""",
}


# --------------------------------------------------------------------------
# 위기 문맥 판정 — MLCM_320 2단계
# --------------------------------------------------------------------------

class CrisisVerdict(BaseModel):
    """03-B 가 규정한 반환 스키마.

    Structured Outputs 로 강제하므로 파싱이 깨질 일이 없다.
    """

    is_crisis: bool = Field(description="즉각적 위기 개입이 필요한 발화인지")
    severity: str = Field(description="NONE, LOW, MEDIUM, HIGH 중 하나")
    matched_context: str = Field(description="그렇게 판단한 근거가 된 발화 부분")


CRISIS_SYSTEM = """너는 한국어 대화에서 위기 신호를 판정하는 분류기다.

다음 중 하나라도 해당하면 is_crisis=true, severity=HIGH 로 판정한다.
- 자살 또는 자해에 대한 의도, 계획, 준비를 드러냄
- 구체적인 방법이나 시점을 언급함
- 작별 인사, 신변 정리를 암시함

다음은 is_crisis=false 로 두되 severity 를 MEDIUM 이하로 표시한다.
- 일반적인 우울감, 무기력, 피로감 표현
- "죽겠다" 같은 관용적 과장 표현
- 과거의 힘들었던 경험을 회상하는 서술

판단이 애매하면 안전한 쪽으로 기운다. 위기를 놓치는 비용이
불필요한 안내를 노출하는 비용보다 크다.
"""


async def detect_crisis(utterance: str, recent_turns: list[dict]) -> CrisisVerdict:
    """2차 LLM 문맥 판정.

    호출 전에 PII 를 마스킹한 텍스트를 넣어야 한다.
    실패는 호출자가 처리한다 — 여기서 삼키면 키워드 fallback 이 동작하지 않는다.
    """
    context = "\n".join(f"{t['role']}: {t['content']}" for t in recent_turns[-6:])
    resp = await client().beta.chat.completions.parse(
        model=model_for("crisis"),
        messages=[
            {"role": "system", "content": CRISIS_SYSTEM},
            {
                "role": "user",
                "content": f"[최근 대화]\n{context}\n\n[판정 대상 발화]\n{utterance}",
            },
        ],
        response_format=CrisisVerdict,
    )
    parsed = resp.choices[0].message.parsed
    if parsed is None:
        # 스키마 강제가 걸려 있어 정상적으로는 오지 않는다. 오면 판정 실패로
        # 취급해 키워드 fallback 으로 넘긴다 — None 을 판정 결과로 쓰면 안 된다.
        raise RuntimeError("위기 판정 응답을 파싱하지 못했습니다")
    return parsed


# --------------------------------------------------------------------------
# 페르소나 응답 — MLCM_310
# --------------------------------------------------------------------------

async def generate_reply(
    persona_type: str, utterance: str, recent_turns: list[dict]
) -> str:
    persona = PERSONA_PROMPTS.get(persona_type, PERSONA_PROMPTS["FRIEND"])
    messages = [{"role": "system", "content": persona + SAFETY_RULES}]
    messages += [
        {"role": t["role"], "content": t["content"]} for t in recent_turns[-10:]
    ]
    messages.append({"role": "user", "content": utterance})

    resp = await client().chat.completions.create(
        model=model_for("reply"), messages=messages
    )
    return resp.choices[0].message.content or ""


FALLBACK_REPLY = {
    "FRIEND": "지금 생각을 정리하는 데 시간이 조금 걸리네요. 잠시 후에 다시 말씀해 주시겠어요?",
    "COUNSELOR": "지금 답변을 준비하는 데 시간이 걸리고 있어요. 잠시 후 다시 시도해 주세요.",
}


# --------------------------------------------------------------------------
# 병렬 호출 — NFR-DV-001
# --------------------------------------------------------------------------

async def analyze_and_reply(
    persona_type: str, utterance: str, recent_turns: list[dict]
) -> tuple[str | None, CrisisVerdict | None]:
    """위기 판정과 응답 생성을 동시에 호출한다.

    순차로 하면 LLM 왕복이 2회가 되어 전체 3초 요건(NFR-DV-001)을 넘긴다.
    Gemini 를 쓸 때는 두 호출이 **서로 다른 모델**로 나가므로(model_for 참조)
    무료 한도 RPM 도 서로 잡아먹지 않는다.
    CRITICAL 로 판정되면 생성된 일반 응답은 **호출자가 버린다**.

    두 호출은 독립이므로 한쪽이 실패해도 다른 쪽 결과는 살린다.
    """
    reply_task = asyncio.create_task(generate_reply(persona_type, utterance, recent_turns))
    crisis_task = asyncio.create_task(detect_crisis(utterance, recent_turns))

    results = await asyncio.gather(reply_task, crisis_task, return_exceptions=True)
    reply, verdict = results

    if isinstance(reply, BaseException):
        logger.warning("응답 생성 실패: %s", reply)
        reply = None
    if isinstance(verdict, BaseException):
        # 키워드 fallback 으로 넘어간다. NFR-DV-003.
        logger.warning("위기 판정 실패: %s", verdict)
        verdict = None

    return reply, verdict


# --------------------------------------------------------------------------
# 세션 요약 — MLCM_310 종료조건
# --------------------------------------------------------------------------

DAILY_SYSTEM = """사용자의 오늘 상태를 한두 문장으로 짚어준다.

지켜야 할 것:
- 진단하지 않는다. "우울증", "불안장애" 같은 병명을 쓰지 않는다.
- 수치를 그대로 읊지 않는다. 관찰된 패턴을 사람 말로 옮긴다.
- 단정하지 말고 관찰한 것만 말한다. "~해 보여요", "~인 것 같아요" 처럼 쓴다.
- 위로나 제안으로 마무리한다. 겁을 주지 않는다.
- 한국어로 2문장 이내.
"""


async def daily_summary(
    emotion_name: str, risk_level: str, sleep_min: int | None, steps: int | None
) -> str | None:
    """MAIN_HOME_01 ❸ — LLM 기반 일일 감정 종합 리포트.

    실패하면 None 을 돌려 홈 화면이 그 칸만 비운 채로 뜨게 한다.
    요약 하나 때문에 대시보드 전체가 실패하면 안 된다.
    """
    facts = [f"오늘의 감정 상태는 {emotion_name}, 위험 단계는 {risk_level}"]
    if sleep_min is not None:
        facts.append(f"수면 {sleep_min // 60}시간 {sleep_min % 60}분")
    if steps is not None:
        facts.append(f"걸음 수 {steps}")

    try:
        resp = await client().chat.completions.create(
            model=model_for("daily"),
            messages=[
                {"role": "system", "content": DAILY_SYSTEM},
                {"role": "user", "content": ", ".join(facts)},
            ],
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.info("일일 요약 생성 실패: %s", e)
        return None


SUMMARY_SYSTEM = """대화를 2~3문장으로 요약한다.
사용자가 어떤 상황이었고 어떤 감정을 표현했는지 중심으로 쓴다.
진단이나 평가를 하지 않고, 개인식별정보는 요약에 포함하지 않는다.
"""


async def summarize_session(messages: list[dict]) -> str | None:
    if not messages:
        return None
    body = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
    try:
        resp = await client().chat.completions.create(
            model=model_for("summary"),
            messages=[
                {"role": "system", "content": SUMMARY_SYSTEM},
                {"role": "user", "content": body},
            ],
        )
        return resp.choices[0].message.content
    except Exception as e:
        # 요약 실패로 세션 종료 자체를 막지 않는다.
        logger.warning("세션 요약 실패: %s", e)
        return None
