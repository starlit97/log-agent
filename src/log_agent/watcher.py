"""감시 폴더에서 새 엑셀 파일을 감지해 큐잉한다."""

from collections.abc import Iterator
from pathlib import Path


def watch(directory: Path) -> Iterator[Path]:
    """디렉터리에 새로 추가된 파일 경로를 yield 한다."""
    raise NotImplementedError
