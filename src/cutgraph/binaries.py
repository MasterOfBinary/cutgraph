from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import Callable


class MissingBinaryError(RuntimeError):
    """Raised when a required FFmpeg-family binary is unavailable."""


@dataclass(frozen=True)
class BinaryInfo:
    name: str
    path: str
    available: bool


Locator = Callable[[str], str | None]


def require_binary(name: str, *, locator: Locator | None = None) -> BinaryInfo:
    path = (locator or shutil.which)(name)
    if not path:
        raise MissingBinaryError(
            f"{name} was not found. Install FFmpeg/ffprobe and ensure {name} is on PATH."
        )
    return BinaryInfo(name=name, path=path, available=True)
