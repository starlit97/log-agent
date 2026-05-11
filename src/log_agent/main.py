"""설정 로드 후 watcher → loader → analyzer → mailer 파이프라인을 실행한다."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from log_agent import analyzer, loader, mailer, watcher

logger = logging.getLogger(__name__)

_REQUIRED_ENV_VARS = (
    "WATCH_DIR",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "ALERT_TO",
)


def main() -> None:
    """자동 모드 엔트리포인트."""
    load_dotenv()
    _ensure_required_env()
    _configure_logging()

    watch_dir = Path(os.environ["WATCH_DIR"])
    alert_to = os.environ["ALERT_TO"]

    logger.info("자동 모드 시작 — watch_dir=%s", watch_dir)
    try:
        for path in watcher.watch(watch_dir):
            _process_file(path, alert_to)
    except KeyboardInterrupt:
        logger.info("Ctrl-C 수신 — 종료합니다.")


def _process_file(path: Path, alert_to: str) -> None:
    """단일 파일 처리. 예외는 흡수해 다음 파일로 넘어가도록 한다."""
    logger.info("파일 처리 시작: %s", path.name)
    try:
        frame = loader.load_excel(path)
        findings = analyzer.analyze(frame)
        if not findings:
            logger.info("파일 처리 완료(이상 없음): %s", path.name)
            return
        subject = f"[log-agent] 이상 행 {len(findings)}건 감지: {path.name}"
        mailer.send(alert_to, subject, findings)
        logger.info("파일 처리 완료(메일 발송): %s findings=%d", path.name, len(findings))
    except Exception:
        logger.exception("파일 처리 중 예외 발생, 다음 파일로 진행: %s", path.name)


def _ensure_required_env() -> None:
    missing = [name for name in _REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"필수 환경변수가 누락되었습니다: {', '.join(missing)}")


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


if __name__ == "__main__":
    main()
