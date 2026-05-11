"""mailer.send() 동작 검증.

외부 SMTP 호출(smtplib.SMTP)은 모두 monkeypatch 로 모킹한다.
실 SMTP 서버 접속 및 실 자격증명 사용 금지.
"""

from __future__ import annotations

from typing import Any

import pytest

from log_agent import mailer


class _FakeSMTPClient:
    """smtplib.SMTP 의 context-manager 인터페이스를 흉내내는 테스트 더블."""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.starttls_calls = 0
        self.login_calls: list[tuple[str, str]] = []
        self.sent_messages: list[Any] = []

    def __enter__(self) -> _FakeSMTPClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def starttls(self) -> None:
        self.starttls_calls += 1

    def login(self, user: str, password: str) -> None:
        self.login_calls.append((user, password))

    def send_message(self, message: Any) -> None:
        self.sent_messages.append(message)


def _install_fake_smtp(monkeypatch: pytest.MonkeyPatch) -> dict[str, _FakeSMTPClient]:
    holder: dict[str, _FakeSMTPClient] = {}

    def factory(host: str, port: int) -> _FakeSMTPClient:
        client = _FakeSMTPClient(host, port)
        holder["client"] = client
        return client

    monkeypatch.setattr("log_agent.mailer.smtplib.SMTP", factory)
    return holder


def _set_smtp_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "agent@example.test")
    monkeypatch.setenv("SMTP_PASSWORD", "fake-password")


def _decode_body(message: Any) -> str:
    payload = message.get_payload(decode=True)
    assert isinstance(payload, bytes)
    return payload.decode("utf-8")


def test_send_skips_smtp_when_findings_empty(monkeypatch):
    _set_smtp_env(monkeypatch)
    holder = _install_fake_smtp(monkeypatch)

    mailer.send("ops@example.test", "subject", [])

    assert "client" not in holder


def test_send_opens_smtp_with_configured_host_and_port(monkeypatch):
    _set_smtp_env(monkeypatch)
    holder = _install_fake_smtp(monkeypatch)
    findings = [{"row_id": 0, "is_anomaly": True, "reason": "x", "severity": "low"}]

    mailer.send("ops@example.test", "s", findings)

    client = holder["client"]
    assert client.host == "smtp.example.test"
    assert client.port == 587


def test_send_calls_starttls_before_login(monkeypatch):
    _set_smtp_env(monkeypatch)
    holder = _install_fake_smtp(monkeypatch)
    findings = [{"row_id": 0, "is_anomaly": True, "reason": "x", "severity": "low"}]

    mailer.send("ops@example.test", "s", findings)

    client = holder["client"]
    assert client.starttls_calls == 1
    assert client.login_calls == [("agent@example.test", "fake-password")]


def test_send_sets_subject_and_to_headers(monkeypatch):
    _set_smtp_env(monkeypatch)
    holder = _install_fake_smtp(monkeypatch)
    findings = [{"row_id": 0, "is_anomaly": True, "reason": "x", "severity": "low"}]

    mailer.send("ops@example.test", "이상 감지", findings)

    message = holder["client"].sent_messages[0]
    assert message["Subject"] == "이상 감지"
    assert message["To"] == "ops@example.test"
    assert message["From"] == "agent@example.test"


def test_send_renders_row_id_into_body(monkeypatch):
    _set_smtp_env(monkeypatch)
    holder = _install_fake_smtp(monkeypatch)
    findings = [{"row_id": 7, "is_anomaly": True, "reason": "야간 출입", "severity": "high"}]

    mailer.send("ops@example.test", "s", findings)

    body = _decode_body(holder["client"].sent_messages[0])
    assert "row_id=7" in body


def test_send_renders_reason_text_into_body(monkeypatch):
    _set_smtp_env(monkeypatch)
    holder = _install_fake_smtp(monkeypatch)
    findings = [{"row_id": 0, "is_anomaly": True, "reason": "야간 출입", "severity": "high"}]

    mailer.send("ops@example.test", "s", findings)

    body = _decode_body(holder["client"].sent_messages[0])
    assert "야간 출입" in body


def test_send_renders_severity_into_body(monkeypatch):
    _set_smtp_env(monkeypatch)
    holder = _install_fake_smtp(monkeypatch)
    findings = [{"row_id": 0, "is_anomaly": True, "reason": "x", "severity": "high"}]

    mailer.send("ops@example.test", "s", findings)

    body = _decode_body(holder["client"].sent_messages[0])
    assert "high" in body


def test_send_renders_all_findings_when_multiple_present(monkeypatch):
    _set_smtp_env(monkeypatch)
    holder = _install_fake_smtp(monkeypatch)
    findings = [
        {"row_id": 1, "is_anomaly": True, "reason": "야간 출입", "severity": "high"},
        {"row_id": 2, "is_anomaly": True, "reason": "권한 외 접근", "severity": "med"},
    ]

    mailer.send("ops@example.test", "s", findings)

    body = _decode_body(holder["client"].sent_messages[0])
    assert "row_id=1" in body
    assert "row_id=2" in body
    assert "야간 출입" in body
    assert "권한 외 접근" in body


def test_send_raises_runtime_error_when_smtp_host_missing(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "agent@example.test")
    monkeypatch.setenv("SMTP_PASSWORD", "fake-password")
    findings = [{"row_id": 0, "is_anomaly": True, "reason": "x", "severity": "low"}]

    with pytest.raises(RuntimeError, match="SMTP_HOST"):
        mailer.send("ops@example.test", "s", findings)


def test_send_raises_runtime_error_when_smtp_password_missing(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "agent@example.test")
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    findings = [{"row_id": 0, "is_anomaly": True, "reason": "x", "severity": "low"}]

    with pytest.raises(RuntimeError, match="SMTP_PASSWORD"):
        mailer.send("ops@example.test", "s", findings)


def test_send_raises_runtime_error_when_smtp_port_not_numeric(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_PORT", "not-a-number")
    monkeypatch.setenv("SMTP_USER", "agent@example.test")
    monkeypatch.setenv("SMTP_PASSWORD", "fake-password")
    findings = [{"row_id": 0, "is_anomaly": True, "reason": "x", "severity": "low"}]

    with pytest.raises(RuntimeError, match="SMTP_PORT"):
        mailer.send("ops@example.test", "s", findings)


def test_send_does_not_load_smtp_config_when_findings_empty(monkeypatch):
    """빈 입력일 때는 환경변수 누락이라도 예외를 던지지 않고 조용히 반환한다."""
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_PORT", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)

    mailer.send("ops@example.test", "s", [])
