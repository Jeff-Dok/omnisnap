# tests/test_queue.py
from core.queue import QueuedTask, QueueManager


def _task(**kw):
    defaults = {"url": "https://example.com", "modes": [1], "depth": 0, "cookies_path": None}
    defaults.update(kw)
    return QueuedTask(**defaults)


class TestQueueManager:
    def setup_method(self):
        self.q = QueueManager()

    def test_empty_by_default(self):
        assert self.q.count() == 0
        assert self.q.all() == []

    def test_add_increases_count(self):
        self.q.add(_task())
        assert self.q.count() == 1

    def test_all_returns_copy(self):
        task = _task()
        self.q.add(task)
        result = self.q.all()
        assert result[0] is task
        result.clear()
        assert self.q.count() == 1  # copie, pas la liste interne

    def test_remove_by_id(self):
        task = _task()
        self.q.add(task)
        self.q.remove(task.id)
        assert self.q.count() == 0

    def test_remove_unknown_id_silent(self):
        self.q.remove("nonexistent-id")  # ne doit pas lever d'exception

    def test_next_returns_first_and_removes(self):
        t1 = _task(url="https://a.com")
        t2 = _task(url="https://b.com")
        self.q.add(t1)
        self.q.add(t2)
        assert self.q.next() is t1
        assert self.q.count() == 1

    def test_next_empty_returns_none(self):
        assert self.q.next() is None

    def test_fifo_order(self):
        urls = ["https://a.com", "https://b.com", "https://c.com"]
        for u in urls:
            self.q.add(_task(url=u))
        for u in urls:
            assert self.q.next().url == u

    def test_clear(self):
        self.q.add(_task())
        self.q.add(_task())
        self.q.clear()
        assert self.q.count() == 0
        assert self.q.all() == []

    def test_unique_ids(self):
        t1 = _task()
        t2 = _task()
        assert t1.id != t2.id
