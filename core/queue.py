# core/queue.py
import uuid
from dataclasses import dataclass, field


@dataclass
class QueuedTask:
    url: str
    modes: list[int]
    depth: int
    cookies_path: str | None
    respect_robots: bool = False
    url_filter: str = ""
    use_playwright: bool = False
    playwright_opts: dict = field(default_factory=dict)
    img_ext_filter: set | None = None
    vid_ext_filter: set | None = None
    aud_ext_filter: set | None = None
    doc_ext_filter: set | None = None
    arc_ext_filter: set | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


class QueueManager:
    def __init__(self) -> None:
        self._tasks: list[QueuedTask] = []

    def add(self, task: QueuedTask) -> None:
        self._tasks.append(task)

    def remove(self, task_id: str) -> None:
        self._tasks = [t for t in self._tasks if t.id != task_id]

    def clear(self) -> None:
        self._tasks = []

    def next(self) -> QueuedTask | None:
        if not self._tasks:
            return None
        return self._tasks.pop(0)

    def all(self) -> list[QueuedTask]:
        return list(self._tasks)

    def count(self) -> int:
        return len(self._tasks)
