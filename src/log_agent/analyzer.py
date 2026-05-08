"""프롬프트를 조립하고 LLM 응답을 pydantic 으로 검증해 결과를 구조화한다."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


def analyze(frame: "pd.DataFrame") -> list[dict]:
    """이상 행 판정 결과를 구조화된 레코드 리스트로 반환한다."""
    raise NotImplementedError
