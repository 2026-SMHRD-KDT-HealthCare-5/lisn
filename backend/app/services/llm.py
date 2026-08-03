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
from app.services import risk_policy

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

판정은 두 축이다. is_crisis 는 **위기 신호가 있는가**이고,
severity 는 **얼마나 임박했는가**다. 둘을 섞지 않는다.

is_crisis=true, severity=HIGH — 의도가 드러나거나 이미 벌어진 경우
- 자살 또는 자해에 대한 의도, 계획, 준비를 드러냄
- 구체적인 방법이나 시점을 언급함
- 작별 인사, 신변 정리를 암시함
- 자해를 이미 했거나 하는 중임을 말함. 아물지 않은 상처·자국·출혈 등
  현재 남아 있는 신체 손상을 언급하는 경우를 포함한다
- 지금 도움이 필요한 상태임을 드러냄

is_crisis=true, severity=MEDIUM — 위기 신호는 있으나 의도가 불명확한 경우
- 삶의 의미나 목적이 사라졌다는 표현 ("뭘 해도 의미가 없어요",
  "왜 사는지 모르겠어요", "내가 여기 왜 있는지 모르겠어요")
- 자신의 존재가 부담이라는 인식
- 죽음을 소망하지만 실행 의도는 드러나지 않는 표현
- 예전에 좋아하던 것에 흥미를 완전히 잃었다는 서술
- 미래에 대한 기대가 없다는 표현
- 사회적 단절과 고립 — 연락할 사람이 없다, 며칠째 아무와도 말하지 않았다,
  사람들 속에 있어도 혼자라고 느낀다, 아무도 찾지 않는다
  ※ 이 서비스의 대상은 1인가구이고 고립은 흔한 상태이지만,
    흔하다는 것이 안전하다는 뜻은 아니다. 놓치지 않는다.
- 농담이나 웃음으로 감싼 부정적 서술 ("아무리 해도 제자리예요 ㅋㅋ").
  웃음 표시가 붙었다고 신호를 낮추지 않는다. 다만 "배고파 죽겠다"처럼
  관용구 자체가 과장인 경우는 아래 is_crisis=false 로 둔다.

is_crisis=false — 위기 신호로 보지 않는다
- 특정 상황에 한정된 피로감·스트레스 ("이 일 그만두고 싶어요")
- "죽겠다" 같은 관용적 과장 표현
- 과거의 힘들었던 경험을 회상하되, 지금은 지나갔거나 회복되었음이
  함께 드러나는 서술
- 말하는 사람 본인이 아니라 제3자(친구·가족 등)의 상태를 걱정하거나
  도울 방법을 묻는 경우
- 창작·보도·학습 등 본인의 상태가 아닌 맥락에서 소재로 다루는 경우

판단이 애매하면 안전한 쪽으로 기운다. 위기를 놓치는 비용이
불필요한 안내를 노출하는 비용보다 크다.
특히 **시제로 위기를 낮추지 않는다.** 이미 벌어진 일이라고 해서
지나간 일인 것은 아니다.
무기력과 무의미감을 "흔한 감정"이라는 이유로 낮추지 않는다.
의도가 안 보이는 것과 위기가 아닌 것은 다르다.
"""


def crisis_user_message(utterance: str, recent_turns: list[dict]) -> str:
    """위기 판정에 넣을 user 메시지.

    ⚠ **평가 스크립트(`tools/eval_crisis.py`)가 이 함수를 그대로 씁니다.**
      전에는 운영이 `[최근 대화]…[판정 대상 발화]…` 로 감싸고 평가는 발화
      원문만 보냈습니다. 스크립트 주석은 "프롬프트와 스키마는 똑같이 쓴다 —
      다르면 평가 결과가 운영과 무관해진다"고 적어뒀는데, 정작 **메시지
      형식이 달라 다른 것을 재고 있었습니다**
      (→ `docs/검증/구현_갭_20260803.md`).

      프롬프트만 공유하는 것으로는 부족합니다. **넣는 문자열을 만드는
      코드까지 공유해야** 같은 것을 재는 게 보장됩니다.
    """
    context = "\n".join(f"{t['role']}: {t['content']}" for t in recent_turns[-6:])
    return f"[최근 대화]\n{context}\n\n[판정 대상 발화]\n{utterance}"


async def detect_crisis(utterance: str, recent_turns: list[dict]) -> CrisisVerdict:
    """2차 LLM 문맥 판정.

    호출 전에 PII 를 마스킹한 텍스트를 넣어야 한다.
    실패는 호출자가 처리한다 — 여기서 삼키면 키워드 fallback 이 동작하지 않는다.
    """
    resp = await client().beta.chat.completions.parse(
        model=model_for("crisis"),
        messages=[
            {"role": "system", "content": CRISIS_SYSTEM},
            {
                "role": "user",
                "content": crisis_user_message(utterance, recent_turns),
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
    persona_type: str,
    utterance: str,
    recent_turns: list[dict],
    keyword_level: str = "NONE",
) -> tuple[str | None, CrisisVerdict | None]:
    """위기 판정과 응답 생성을 동시에 호출한다.

    순차로 하면 LLM 왕복이 2회가 되어 전체 3초 요건(NFR-DV-001)을 넘긴다.
    Gemini 를 쓸 때는 두 호출이 **서로 다른 모델**로 나가므로(model_for 참조)
    무료 한도 RPM 도 서로 잡아먹지 않는다.

    두 호출은 독립이므로 한쪽이 실패해도 다른 쪽 결과는 살린다.

    ---
    ## 위기가 확정되면 응답 생성을 기다리지 않는다 (2026.08.03)

    전에는 `gather` 로 **둘 다 기다린 뒤** CRITICAL 이면 응답을 버렸다.
    **버릴 것을 기다리고 있었다.** 실측에서 위기 발화가 일반 발화의 2.3배로
    느렸던 원인이다(`NFR-TS-001` 중앙값 4964ms · 예산 3000ms).

    이제 위기 판정이 먼저 끝나고 **버릴 것이 확정되면** 응답 생성을 취소하고
    즉시 돌아온다. 실측에서 응답 생성이 위기 판정보다 **2.7배** 길었다
    (위기 발화 기준 5151ms vs 1920ms).

    **문맥 판단을 그대로 유지하므로 정밀도 손실이 없다** — 키워드만으로
    끊는 방식(HIGH 키워드 정밀도 0.500)과 다른 점이다.

    ⚠ **`keyword_level` 을 받는 이유** — 버릴지 여부는 LLM 판정만으로
      정해지지 않는다. 「죽고 싶다」에 LLM 이 MEDIUM 을 주는 일이 잦은데,
      최종 CRITICAL 은 HIGH 키워드가 함께 있어서 나온다. 처음 구현할 때
      `severity == HIGH` 만 보고 취소했더니 **정작 이 경우에 취소가 안
      걸려 효과가 없었다.** 판정 규칙은 `risk_policy.level_for()` 한 곳에
      있고 여기서도 그것을 쓴다.

    ⚠ 위기 판정이 **먼저 끝날 때만** 이득이다. 응답 생성이 먼저 끝나면
      그대로 둘 다 받는다. 순서를 강제하지 않는다.

    → `docs/검증/성능실측_20260803_openai.md`
    """
    reply_task = asyncio.create_task(generate_reply(persona_type, utterance, recent_turns))
    crisis_task = asyncio.create_task(detect_crisis(utterance, recent_turns))

    pending = {reply_task, crisis_task}
    reply: object = None
    verdict: object = None

    while pending:
        done, pending = await asyncio.wait(
            pending, return_when=asyncio.FIRST_COMPLETED
        )
        for task in done:
            if task is crisis_task:
                verdict = task.exception() or task.result()
            else:
                reply = task.exception() or task.result()

        # 위기가 확정됐고 응답이 아직이면, 기다릴 이유가 없다. 어차피 버린다.
        if (
            crisis_task in done
            and not isinstance(verdict, BaseException)
            and verdict is not None
            and risk_policy.will_discard_reply(
                keyword_level, verdict.is_crisis, verdict.severity
            )
            and reply_task in pending
        ):
            reply_task.cancel()
            pending.discard(reply_task)
            reply = None
            break

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
