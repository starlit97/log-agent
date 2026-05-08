"""엑셀 파일을 DataFrame 으로 로드하고 컬럼을 정규화한다."""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


def load_excel(path: Path) -> "pd.DataFrame":
    """엑셀 파일을 정규화된 DataFrame 으로 로드한다."""
    raise NotImplementedError
