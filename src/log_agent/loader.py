"""엑셀 파일을 DataFrame 으로 로드하고 컬럼을 정규화한다."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

_EXCEL_SUFFIX = ".xlsx"


def load_excel(path: Path) -> pd.DataFrame:
    """엑셀 파일을 정규화된 DataFrame 으로 로드한다.

    첫 시트만 사용한다. 컬럼명은 좌우 공백 제거 후 소문자로 통일한다.
    빈 시트는 빈 DataFrame 으로 반환한다 (예외 아님).
    """
    if not path.exists():
        raise FileNotFoundError(f"엑셀 파일을 찾을 수 없습니다: {path}")
    if path.suffix.lower() != _EXCEL_SUFFIX:
        raise ValueError(
            f"지원하지 않는 파일 형식입니다(.xlsx 만 허용): {path.suffix or '<no suffix>'}"
        )

    frame = pd.read_excel(path, sheet_name=0, engine="openpyxl")
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    return frame
