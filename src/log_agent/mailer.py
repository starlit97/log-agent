"""SMTP 로 이상 판정 결과 메일을 발송한다."""

from __future__ import annotations

import logging
import os
import smtplib
from collections.abc import Sequence
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

_REQUIRED_ENV_VARS = ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD")


def send(to: str, subject: str, findings: Sequence[dict]) -> None:
    """판정 결과를 메일 본문으로 렌더해 SMTP 로 발송한다.

    findings 가 비어 있으면 발송 호출 자체를 생략한다 — "이상 있음 → 발송" 판단은
    호출자(main.py / ui/app.py) 책임이지만, 빈 입력 방어는 모듈 안에서 한 번 더 보호한다.
    """
    if not findings:
        return

    host, port, user, password = _load_smtp_config()

    message = MIMEText(_render_body(findings), "plain", "utf-8")
    message["From"] = user
    message["To"] = to
    message["Subject"] = subject

    with smtplib.SMTP(host, port) as client:
        client.starttls()
        client.login(user, password)
        client.send_message(message)


def _load_smtp_config() -> tuple[str, int, str, str]:
    values = {name: os.environ.get(name, "") for name in _REQUIRED_ENV_VARS}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RuntimeError(f"SMTP 설정 환경변수가 누락되었다: {', '.join(missing)}")

    try:
        port = int(values["SMTP_PORT"])
    except ValueError as exc:
        raise RuntimeError(f"SMTP_PORT 가 정수가 아니다: {values['SMTP_PORT']!r}") from exc

    return values["SMTP_HOST"], port, values["SMTP_USER"], values["SMTP_PASSWORD"]


def _render_body(findings: Sequence[dict]) -> str:
    lines = [f"이상 행 {len(findings)}건이 감지되었습니다.", ""]
    for finding in findings:
        row_id = finding.get("row_id")
        severity = finding.get("severity")
        is_anomaly = finding.get("is_anomaly")
        reason = finding.get("reason")
        lines.append(f"[row_id={row_id}] severity={severity} is_anomaly={is_anomaly}")
        lines.append(f"  reason: {reason}")
        lines.append("")
    return "\n".join(lines)
