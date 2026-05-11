"""analyzer.analyze() 동작 검증.

외부 LLM 호출(llm.complete)은 모두 monkeypatch 로 모킹한다.
실 데이터는 절대 사용하지 않고 합성 행만 사용한다.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import pytest
from pydantic import ValidationError

from log_agent import analyzer


def _patch_llm(monkeypatch: pytest.MonkeyPatch, response: str) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    def fake_complete(prompt: str, *, system: str | None = None) -> str:
        captured["prompt"] = prompt
        captured["system"] = system
        return response

    monkeypatch.setattr("log_agent.analyzer.llm.complete", fake_complete)
    return captured


def _make_response(*verdicts: dict[str, Any]) -> str:
    return json.dumps({"verdicts": list(verdicts)})


def _sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"timestamp": "2099-01-01T02:30:00", "employee_id": "EMP-TEST-0001", "gate": "Gate-A"},
            {"timestamp": "2099-01-01T09:30:00", "employee_id": "EMP-TEST-0002", "gate": "Gate-B"},
        ]
    )


def test_analyze_returns_only_anomaly_rows_when_llm_marks_subset(monkeypatch):
    response = _make_response(
        {"row_id": 0, "is_anomaly": True, "reason": "야간 출입", "severity": "high"},
        {"row_id": 1, "is_anomaly": False, "reason": "정상", "severity": "low"},
    )
    _patch_llm(monkeypatch, response)

    result = analyzer.analyze(_sample_frame())

    assert result == [
        {"row_id": 0, "is_anomaly": True, "reason": "야간 출입", "severity": "high"}
    ]


def test_analyze_returns_empty_list_when_frame_is_empty(monkeypatch):
    monkeypatch.setattr("log_agent.analyzer.llm.complete", lambda *a, **k: "")

    assert analyzer.analyze(pd.DataFrame()) == []


def test_analyze_skips_llm_call_when_frame_is_empty(monkeypatch):
    call_count = {"n": 0}

    def fake_complete(prompt, *, system=None):
        call_count["n"] += 1
        return ""

    monkeypatch.setattr("log_agent.analyzer.llm.complete", fake_complete)

    analyzer.analyze(pd.DataFrame())

    assert call_count["n"] == 0


def test_analyze_returns_empty_list_when_no_rows_flagged(monkeypatch):
    response = _make_response(
        {"row_id": 0, "is_anomaly": False, "reason": "정상", "severity": "low"},
        {"row_id": 1, "is_anomaly": False, "reason": "정상", "severity": "low"},
    )
    _patch_llm(monkeypatch, response)

    assert analyzer.analyze(_sample_frame()) == []


def test_analyze_passes_system_prompt_to_llm(monkeypatch):
    captured = _patch_llm(
        monkeypatch,
        _make_response({"row_id": 0, "is_anomaly": False, "reason": "정상", "severity": "low"}),
    )

    analyzer.analyze(pd.DataFrame([{"col": "value"}]))

    assert captured["system"] == analyzer.SYSTEM_PROMPT


def test_analyze_serializes_row_data_into_user_prompt(monkeypatch):
    captured = _patch_llm(
        monkeypatch,
        _make_response({"row_id": 0, "is_anomaly": False, "reason": "정상", "severity": "low"}),
    )

    analyzer.analyze(pd.DataFrame([{"gate": "Gate-A", "employee_id": "EMP-TEST-0001"}]))

    assert "Gate-A" in captured["prompt"]
    assert "EMP-TEST-0001" in captured["prompt"]


def test_analyze_raises_value_error_when_llm_returns_invalid_json(monkeypatch):
    _patch_llm(monkeypatch, "not json {")

    with pytest.raises(ValueError):
        analyzer.analyze(pd.DataFrame([{"col": 1}]))


def test_analyze_raises_validation_error_when_severity_is_unknown(monkeypatch):
    _patch_llm(
        monkeypatch,
        _make_response(
            {"row_id": 0, "is_anomaly": True, "reason": "x", "severity": "critical"}
        ),
    )

    with pytest.raises(ValidationError):
        analyzer.analyze(pd.DataFrame([{"col": 1}]))


def test_analyze_raises_validation_error_when_required_field_missing(monkeypatch):
    _patch_llm(
        monkeypatch,
        _make_response({"row_id": 0, "is_anomaly": True, "reason": "x"}),
    )

    with pytest.raises(ValidationError):
        analyzer.analyze(pd.DataFrame([{"col": 1}]))


def test_analyze_handles_pandas_timestamp_columns(monkeypatch):
    captured = _patch_llm(
        monkeypatch,
        _make_response({"row_id": 0, "is_anomaly": False, "reason": "정상", "severity": "low"}),
    )

    frame = pd.DataFrame([{"ts": pd.Timestamp("2099-01-01T02:30:00"), "gate": "Gate-A"}])

    analyzer.analyze(frame)

    assert "2099-01-01T02:30:00" in captured["prompt"]


def test_analyze_handles_nan_values_as_null(monkeypatch):
    captured = _patch_llm(
        monkeypatch,
        _make_response({"row_id": 0, "is_anomaly": False, "reason": "정상", "severity": "low"}),
    )

    frame = pd.DataFrame([{"gate": "Gate-A", "note": float("nan")}])

    analyzer.analyze(frame)

    assert '"note": null' in captured["prompt"]
