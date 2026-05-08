"""SMTP 로 이상 판정 결과 메일을 발송한다."""

from collections.abc import Sequence


def send(to: str, subject: str, findings: Sequence[dict]) -> None:
    """판정 결과를 메일 본문으로 렌더해 SMTP 로 발송한다."""
    raise NotImplementedError
