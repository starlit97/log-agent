"""감시 폴더에서 새 엑셀 파일을 감지해 큐잉한다."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from pathlib import Path
from queue import Queue

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

_EXCEL_SUFFIX = ".xlsx"
_LOCK_PREFIX = "~$"
_PARTIAL_SUFFIXES = (".tmp", ".crdownload")

# 엑셀 저장은 zip 압축이 끝날 때까지 파일 크기가 변한다.
# 두 번 연속 같은 크기가 관측되면 쓰기 완료로 판단한다.
_STABILITY_POLL_INTERVAL = 0.2
_STABILITY_TIMEOUT = 10.0


def watch(directory: Path) -> Iterator[Path]:
    """디렉터리에 새로 추가된 .xlsx 파일 경로를 yield 한다.

    감시는 비재귀(하위 폴더 무시), 생성 이벤트만 처리한다. Excel 잠금
    파일(`~$*`) 과 다운로드 부분 파일(`.tmp`, `.crdownload`) 은 제외하고,
    파일 크기가 안정될 때까지 대기한 뒤 yield 한다. 호출자가 generator
    를 close 하면 감시 스레드도 종료된다.
    """
    if not directory.exists():
        raise FileNotFoundError(f"감시 디렉터리가 존재하지 않습니다: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"감시 대상이 디렉터리가 아닙니다: {directory}")
    return _watch(directory)


def _watch(directory: Path) -> Iterator[Path]:
    queue: Queue[Path] = Queue()
    handler = _NewExcelHandler(queue)
    observer = Observer()
    observer.schedule(handler, str(directory), recursive=False)
    observer.start()
    try:
        while True:
            path = queue.get()
            if _wait_until_stable(path):
                yield path
            else:
                logger.warning("파일이 안정화되지 않아 건너뜁니다: %s", path.name)
    finally:
        observer.stop()
        observer.join()


class _NewExcelHandler(FileSystemEventHandler):
    """`.xlsx` 생성 이벤트만 큐에 넣는 핸들러."""

    def __init__(self, queue: Queue[Path]) -> None:
        self._queue = queue

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if not _is_target_excel(path):
            return
        logger.debug("새 엑셀 감지: %s", path.name)
        self._queue.put(path)


def _is_target_excel(path: Path) -> bool:
    name = path.name
    if name.startswith(_LOCK_PREFIX):
        return False
    if name.lower().endswith(_PARTIAL_SUFFIXES):
        return False
    return path.suffix.lower() == _EXCEL_SUFFIX


def _wait_until_stable(
    path: Path,
    *,
    poll_interval: float = _STABILITY_POLL_INTERVAL,
    timeout: float = _STABILITY_TIMEOUT,
) -> bool:
    """파일 크기가 두 번 연속 같으면 쓰기가 끝났다고 본다.

    파일이 사라지거나 timeout 안에 안정화되지 못하면 False.
    """
    deadline = time.monotonic() + timeout
    previous_size: int | None = None
    while time.monotonic() < deadline:
        try:
            current_size = path.stat().st_size
        except OSError:
            time.sleep(poll_interval)
            continue
        if previous_size is not None and current_size == previous_size:
            return True
        previous_size = current_size
        time.sleep(poll_interval)
    return False
