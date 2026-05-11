"""테스트 fixture 엑셀을 결정론적으로 재생성한다.

사용:
    python tests/fixtures/generate_excel.py

`tests/fixtures/sample_log.xlsx` 와 `tests/fixtures/empty_log.xlsx` 를
덮어쓴다. 모든 값은 합성이며 실 데이터·실명·실 사번을 포함하지 않는다.
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

FIXTURE_DIR = Path(__file__).parent


def _write_sample_log() -> None:
    """정상 시트: 헤더에 의도적으로 공백/대문자 섞은 컬럼명."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "log"
    sheet.append(["  Timestamp  ", "Employee_ID", "GATE"])
    sheet.append(["2099-01-01T02:30:00", "EMP-TEST-0001", "Gate-A"])
    sheet.append(["2099-01-01T09:30:00", "EMP-TEST-0002", "Gate-B"])
    workbook.save(FIXTURE_DIR / "sample_log.xlsx")


def _write_empty_log() -> None:
    """빈 시트: 헤더·데이터 모두 없다."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "log"
    workbook.save(FIXTURE_DIR / "empty_log.xlsx")


def main() -> None:
    _write_sample_log()
    _write_empty_log()


if __name__ == "__main__":
    main()
