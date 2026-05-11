"""loader.load_excel() 동작 검증.

모든 fixture 는 합성 데이터다. 실 출입 로그·사번·이름은 사용하지 않는다.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook

from log_agent import loader

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_load_excel_returns_dataframe_with_normalized_columns():
    frame = loader.load_excel(FIXTURE_DIR / "sample_log.xlsx")

    assert list(frame.columns) == ["timestamp", "employee_id", "gate"]


def test_load_excel_preserves_row_data():
    frame = loader.load_excel(FIXTURE_DIR / "sample_log.xlsx")

    assert len(frame) == 2
    assert frame.iloc[0]["employee_id"] == "EMP-TEST-0001"
    assert frame.iloc[1]["gate"] == "Gate-B"


def test_load_excel_returns_empty_frame_when_sheet_is_empty():
    frame = loader.load_excel(FIXTURE_DIR / "empty_log.xlsx")

    assert isinstance(frame, pd.DataFrame)
    assert frame.empty


def test_load_excel_raises_file_not_found_when_path_missing(tmp_path):
    missing = tmp_path / "does_not_exist.xlsx"

    with pytest.raises(FileNotFoundError):
        loader.load_excel(missing)


def test_load_excel_raises_value_error_when_extension_is_not_xlsx(tmp_path):
    not_excel = tmp_path / "log.txt"
    not_excel.write_text("not an excel file", encoding="utf-8")

    with pytest.raises(ValueError):
        loader.load_excel(not_excel)


def test_load_excel_reads_only_first_sheet_when_multiple_sheets_exist(tmp_path):
    multi_sheet = tmp_path / "multi.xlsx"
    workbook = Workbook()
    first = workbook.active
    first.title = "first"
    first.append(["col"])
    first.append(["first_value"])
    second = workbook.create_sheet("second")
    second.append(["other"])
    second.append(["second_value"])
    workbook.save(multi_sheet)

    frame = loader.load_excel(multi_sheet)

    assert list(frame.columns) == ["col"]
    assert frame.iloc[0]["col"] == "first_value"
