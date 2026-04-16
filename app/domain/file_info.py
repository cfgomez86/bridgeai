from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FileInfo:
    path: str
    size: int
    extension: str
    last_modified: datetime
