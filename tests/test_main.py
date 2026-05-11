"""main.main() 동작 검증 — watcher/loader/analyzer/mailer 결합.

각 모듈은 monkeypatch 로 모킹한다. 실 파일시스템·실 LLM·실 SMTP 호출 금지.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from log_agent import main as main_module

REQUIRED_ENV: dict[str, str] = {
    "WATCH_DIR": "/tmp/incoming",
    "LLM_BASE_URL": "http://localhost:11434",
    "LLM_MODEL": "qwen2.5:7b-instruct",
    "SMTP_HOST": "smtp.example.test",
    "SMTP_PORT": "587",
    "SMTP_USER": "agent@example.test",
    "SMTP_PASSWORD": "fake-password",
    "ALERT_TO": "ops@example.test",
}


def _set_required_env(
    monkeypatch: pytest.MonkeyPatch, **overrides: str | None
) -> None:
    env: dict[str, str | None] = {**REQUIRED_ENV, **overrides}
    for name, value in env.items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    # load_dotenv 가 실제 .env 를 찾아 덮어쓰지 못하도록 호출 자체를 무력화한다.
    monkeypatch.setattr("log_agent.main.load_dotenv", lambda *a, **k: False)


def _patch_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    *,
    paths: list[Path],
    findings_by_path: dict[str, list[dict]] | None = None,
    loader_errors: dict[str, Exception] | None = None,
    analyzer_errors: dict[str, Exception] | None = None,
    mailer_errors: dict[str, Exception] | None = None,
) -> dict[str, list[Any]]:
    findings_by_path = findings_by_path or {}
    loader_errors = loader_errors or {}
    analyzer_errors = analyzer_errors or {}
    mailer_errors = mailer_errors or {}

    calls: dict[str, list[Any]] = {"load": [], "analyze": [], "send": []}

    def fake_watch(directory: Path):
        yield from paths

    def fake_load(path: Path) -> pd.DataFrame:
        calls["load"].append(path)
        if path.name in loader_errors:
            raise loader_errors[path.name]
        return pd.DataFrame([{"_origin": path.name}])

    def fake_analyze(frame: pd.DataFrame) -> list[dict]:
        calls["analyze"].append(frame)
        name = frame.iloc[0]["_origin"]
        if name in analyzer_errors:
            raise analyzer_errors[name]
        return findings_by_path.get(name, [])

    def fake_send(to: str, subject: str, findings: list[dict]) -> None:
        calls["send"].append((to, subject, list(findings)))
        # mailer_errors 는 path.name 이 아닌 subject 의 일부로 매칭한다.
        for marker, exc in mailer_errors.items():
            if marker in subject:
                raise exc

    monkeypatch.setattr("log_agent.main.watcher.watch", fake_watch)
    monkeypatch.setattr("log_agent.main.loader.load_excel", fake_load)
    monkeypatch.setattr("log_agent.main.analyzer.analyze", fake_analyze)
    monkeypatch.setattr("log_agent.main.mailer.send", fake_send)
    return calls


def test_main_runs_loader_analyzer_and_mailer_when_findings_present(monkeypatch):
    _set_required_env(monkeypatch)
    finding = {"row_id": 0, "is_anomaly": True, "reason": "야간 출입", "severity": "high"}
    calls = _patch_pipeline(
        monkeypatch,
        paths=[Path("a.xlsx")],
        findings_by_path={"a.xlsx": [finding]},
    )

    main_module.main()

    assert [p.name for p in calls["load"]] == ["a.xlsx"]


def test_main_calls_mailer_with_alert_to_and_findings(monkeypatch):
    _set_required_env(monkeypatch)
    finding = {"row_id": 0, "is_anomaly": True, "reason": "야간 출입", "severity": "high"}
    calls = _patch_pipeline(
        monkeypatch,
        paths=[Path("a.xlsx")],
        findings_by_path={"a.xlsx": [finding]},
    )

    main_module.main()

    assert len(calls["send"]) == 1
    to, _subject, findings = calls["send"][0]
    assert to == "ops@example.test"
    assert findings == [finding]


def test_main_skips_mailer_when_findings_empty(monkeypatch):
    _set_required_env(monkeypatch)
    calls = _patch_pipeline(
        monkeypatch,
        paths=[Path("a.xlsx")],
        findings_by_path={"a.xlsx": []},
    )

    main_module.main()

    assert calls["send"] == []


def test_main_continues_to_next_file_when_loader_raises(monkeypatch):
    _set_required_env(monkeypatch)
    finding = {"row_id": 0, "is_anomaly": True, "reason": "x", "severity": "low"}
    calls = _patch_pipeline(
        monkeypatch,
        paths=[Path("bad.xlsx"), Path("good.xlsx")],
        findings_by_path={"good.xlsx": [finding]},
        loader_errors={"bad.xlsx": OSError("disk read failed")},
    )

    main_module.main()

    assert [p.name for p in calls["load"]] == ["bad.xlsx", "good.xlsx"]
    assert len(calls["send"]) == 1


def test_main_continues_to_next_file_when_analyzer_raises(monkeypatch):
    _set_required_env(monkeypatch)
    finding = {"row_id": 0, "is_anomaly": True, "reason": "x", "severity": "low"}
    calls = _patch_pipeline(
        monkeypatch,
        paths=[Path("bad.xlsx"), Path("good.xlsx")],
        findings_by_path={"good.xlsx": [finding]},
        analyzer_errors={"bad.xlsx": ValueError("LLM 응답 오류")},
    )

    main_module.main()

    assert len(calls["analyze"]) == 2
    assert len(calls["send"]) == 1


def test_main_continues_to_next_file_when_mailer_raises(monkeypatch):
    _set_required_env(monkeypatch)
    finding = {"row_id": 0, "is_anomaly": True, "reason": "x", "severity": "low"}
    calls = _patch_pipeline(
        monkeypatch,
        paths=[Path("first.xlsx"), Path("second.xlsx")],
        findings_by_path={
            "first.xlsx": [finding],
            "second.xlsx": [finding],
        },
        mailer_errors={"first.xlsx": RuntimeError("smtp down")},
    )

    main_module.main()

    assert [s[1].split(": ")[-1] for s in calls["send"]] == ["first.xlsx", "second.xlsx"]


def test_main_raises_runtime_error_when_required_env_missing(monkeypatch):
    _set_required_env(monkeypatch, ALERT_TO=None)

    with pytest.raises(RuntimeError, match="ALERT_TO"):
        main_module.main()


def test_main_lists_all_missing_env_vars_in_error(monkeypatch):
    _set_required_env(monkeypatch, SMTP_HOST=None, ALERT_TO=None)

    with pytest.raises(RuntimeError) as exc_info:
        main_module.main()

    assert "SMTP_HOST" in str(exc_info.value)
    assert "ALERT_TO" in str(exc_info.value)


def test_main_does_not_call_watcher_when_env_missing(monkeypatch):
    _set_required_env(monkeypatch, WATCH_DIR=None)
    calls = _patch_pipeline(monkeypatch, paths=[Path("a.xlsx")])

    with pytest.raises(RuntimeError):
        main_module.main()

    assert calls["load"] == []


def test_main_exits_cleanly_on_keyboard_interrupt(monkeypatch):
    _set_required_env(monkeypatch)

    def fake_watch(directory: Path):
        raise KeyboardInterrupt
        yield  # pragma: no cover

    monkeypatch.setattr("log_agent.main.watcher.watch", fake_watch)

    main_module.main()
