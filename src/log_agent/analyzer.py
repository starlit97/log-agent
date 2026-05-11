"""프롬프트를 조립하고 LLM 응답을 pydantic 으로 검증해 결과를 구조화한다."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel

from log_agent import llm

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 보안 출입/접근 로그를 검토해 이상 행을 식별하는 보조자다.

이상 판정 기준:
- 비정상 시간대 출입 (야간/주말, 일반 근무시간 외)
- 비정상 빈도 (단시간 반복 출입, 동시 다지점 접근)
- 권한 범위 외 자원 접근 시도
- 인증 실패 누적
- 동일 사용자의 다른 행과 비교해 명백히 벗어난 패턴

응답은 다음 JSON 구조만 출력한다. 마크다운 코드 펜스, 본문 설명, 추가 텍스트 금지.

{
  "verdicts": [
    {"row_id": <입력 row_id>, "is_anomaly": <true|false>,
     "reason": "<짧은 한국어 설명>", "severity": "low"|"med"|"high"}
  ]
}

규칙:
- 모든 입력 행에 대해 정확히 하나의 verdict 객체를 반환한다.
- 정상 행도 객체를 포함하되 is_anomaly=false 로 표시한다.
- severity 는 정상 행이라도 "low" 로 채운다.
"""


class AnomalyVerdict(BaseModel):
    """단일 행에 대한 LLM 의 이상 판정 결과."""

    row_id: int
    is_anomaly: bool
    reason: str
    severity: Literal["low", "med", "high"]


class _AnalyzerResponse(BaseModel):
    """LLM 이 반환하는 응답 전체 구조."""

    verdicts: list[AnomalyVerdict]


def analyze(frame: pd.DataFrame) -> list[dict]:
    """이상 행 판정 결과를 구조화된 레코드 리스트로 반환한다."""
    if frame.empty:
        return []

    rows = _serialize_rows(frame)
    user_prompt = "분석 대상 로그 행 (JSON):\n" + json.dumps(
        rows, ensure_ascii=False, default=str
    )

    raw = llm.complete(user_prompt, system=SYSTEM_PROMPT)

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM 응답이 유효한 JSON 이 아니다: {exc}") from exc

    response = _AnalyzerResponse.model_validate(payload)
    return [verdict.model_dump() for verdict in response.verdicts if verdict.is_anomaly]


def _serialize_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """DataFrame 행을 JSON 직렬화 가능한 dict 리스트로 변환한다."""
    import pandas as pd

    records: list[dict[str, Any]] = []
    for index, row in frame.iterrows():
        record: dict[str, Any] = {"row_id": int(index)}
        for column, value in row.items():
            record[str(column)] = _coerce_value(value, pd)
        records.append(record)
    return records


def _coerce_value(value: Any, pd_module: Any) -> Any:
    """pandas/numpy 스칼라를 JSON 호환 기본 타입으로 변환한다."""
    if value is None:
        return None
    try:
        if pd_module.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            return str(value)
    return value
