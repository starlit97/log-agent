"""watcher.watch() 동작 검증.

watchdog 통합 테스트로 tmp_path 에 실제 파일을 만들고 yield 여부를
확인한다. 이슈 IBI-5 의 검증 절차에 따라 실 파일시스템 이벤트를 사용한다.
모든 파일은 합성이며 실 로그·실명·실 사번을 포함하지 않는다.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from log_agent import watcher

OBSERVER_STARTUP_DELAY = 0.5
EVENT_TIMEOUT = 5.0
INTER_FILE_DELAY = 0.3


def _start_consumer(
    directory: Path, stop_after_name: str
) -> tuple[list[Path], threading.Thread]:
    """백그라운드 스레드에서 watcher 를 돌리고, 지정한 파일이 yield 되면 종료한다."""
    results: list[Path] = []

    def consume() -> None:
        gen = watcher.watch(directory)
        try:
            for path in gen:
                results.append(path)
                if path.name == stop_after_name:
                    break
        finally:
            gen.close()

    thread = threading.Thread(target=consume, daemon=True)
    thread.start()
    return results, thread


def _make_xlsx(path: Path) -> None:
    # zip magic + padding. watcher 는 내용 검증을 하지 않으므로 형식만 흉내내도 충분.
    path.write_bytes(b"PK\x03\x04" + b"\x00" * 256)


def test_watch_yields_newly_created_xlsx(tmp_path: Path) -> None:
    results, thread = _start_consumer(tmp_path, stop_after_name="new.xlsx")
    time.sleep(OBSERVER_STARTUP_DELAY)

    _make_xlsx(tmp_path / "new.xlsx")

    thread.join(timeout=EVENT_TIMEOUT)

    assert not thread.is_alive(), "consumer 스레드가 이벤트를 받지 못했습니다"
    assert [p.name for p in results] == ["new.xlsx"]


def test_watch_filters_excel_lock_files(tmp_path: Path) -> None:
    results, thread = _start_consumer(tmp_path, stop_after_name="real.xlsx")
    time.sleep(OBSERVER_STARTUP_DELAY)

    _make_xlsx(tmp_path / "~$lock.xlsx")
    time.sleep(INTER_FILE_DELAY)
    _make_xlsx(tmp_path / "real.xlsx")

    thread.join(timeout=EVENT_TIMEOUT)

    assert not thread.is_alive()
    assert [p.name for p in results] == ["real.xlsx"]


def test_watch_filters_non_xlsx_files(tmp_path: Path) -> None:
    results, thread = _start_consumer(tmp_path, stop_after_name="real.xlsx")
    time.sleep(OBSERVER_STARTUP_DELAY)

    (tmp_path / "noise.txt").write_text("not excel")
    (tmp_path / "partial.crdownload").write_bytes(b"x" * 100)
    (tmp_path / "draft.tmp").write_bytes(b"x" * 100)
    time.sleep(INTER_FILE_DELAY)
    _make_xlsx(tmp_path / "real.xlsx")

    thread.join(timeout=EVENT_TIMEOUT)

    assert not thread.is_alive()
    assert [p.name for p in results] == ["real.xlsx"]


def test_watch_ignores_subdirectory_creation(tmp_path: Path) -> None:
    results, thread = _start_consumer(tmp_path, stop_after_name="real.xlsx")
    time.sleep(OBSERVER_STARTUP_DELAY)

    (tmp_path / "subdir").mkdir()
    time.sleep(INTER_FILE_DELAY)
    _make_xlsx(tmp_path / "real.xlsx")

    thread.join(timeout=EVENT_TIMEOUT)

    assert not thread.is_alive()
    assert [p.name for p in results] == ["real.xlsx"]


def test_watch_raises_file_not_found_when_directory_missing(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist"

    with pytest.raises(FileNotFoundError):
        watcher.watch(missing)


def test_watch_raises_not_a_directory_when_path_is_file(tmp_path: Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello")

    with pytest.raises(NotADirectoryError):
        watcher.watch(file_path)
