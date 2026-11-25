"""LLM response cache: offline mode, JSON repair, and the shipped-cache export/restore round trip."""

import gzip
import json

import pytest

from common import cache, llm


@pytest.fixture
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "_CACHE_PATH", tmp_path / "llm_cache.sqlite")
    monkeypatch.setattr(llm, "_db", None)
    monkeypatch.setattr(llm, "_get_client", lambda: pytest.fail("tests must not reach an API"))
    yield tmp_path
    if llm._db is not None:
        llm._db.close()


def test_offline_miss_raises(tmp_cache, monkeypatch):
    monkeypatch.setattr(llm, "OFFLINE", True)
    with pytest.raises(llm.CacheMiss):
        llm.chat("hola", model="m")


def test_offline_hit_returns_cached_response(tmp_cache, monkeypatch):
    monkeypatch.setattr(llm, "_get_client", lambda: _FakeClient("hello"))
    assert llm.chat("hola", model="m") == "hello"           # online call populates the cache
    monkeypatch.setattr(llm, "OFFLINE", True)
    monkeypatch.setattr(llm, "_get_client", lambda: pytest.fail("cache hit must not call the API"))
    assert llm.chat("hola", model="m") == "hello"


def test_chat_json_repairs_once(monkeypatch):
    replies = iter(['{"a": 1', '{"a": 1}'])
    monkeypatch.setattr(llm, "chat", lambda *a, **k: next(replies))
    assert llm.chat_json("x") == {"a": 1}


def test_export_restore_round_trip(tmp_cache, monkeypatch):
    monkeypatch.setattr(llm, "_get_client", lambda: _FakeClient("uno"))
    llm.chat("p1", model="m")
    monkeypatch.setattr(llm, "_get_client", lambda: _FakeClient("dos"))
    llm.chat("p2", model="m")
    keys = [k for (k,) in llm._get_db().execute("SELECT k FROM cache")]
    shipped = tmp_cache / "shipped.jsonl.gz"
    assert cache.export(keys[:1], shipped) == 1
    rows = [json.loads(line) for line in gzip.open(shipped, "rt", encoding="utf-8")]
    assert rows[0]["k"] == keys[0]
    fresh = tmp_cache / "fresh.sqlite"
    assert cache.restore(shipped, fresh) == 1
    # exporting the same entries twice gives identical bytes (gzip mtime pinned)
    first = shipped.read_bytes()
    cache.export(keys[:1], shipped)
    assert shipped.read_bytes() == first


class _FakeClient:
    def __init__(self, text):
        msg = type("M", (), {"content": text})()
        choice = type("C", (), {"message": msg})()
        resp = type("R", (), {"choices": [choice]})()
        self.chat = type("Chat", (), {"completions": type("Comp", (), {"create": staticmethod(lambda **kw: resp)})()})()


def test_batch_mode_queues_submits_and_answers_from_cache(tmp_cache, monkeypatch):
    from types import SimpleNamespace as NS

    from common import batch

    submitted = []

    class Files:
        def create(self, file, purpose):
            submitted.append([json.loads(line) for line in file[1].getvalue().decode().splitlines()])
            return NS(id="file-in")

        def content(self, file_id):
            lines = [json.dumps({"custom_id": r["custom_id"], "response": {"body": {
                "choices": [{"message": {"content": "respuesta"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 3}}}}) for r in submitted[-1]]
            return NS(text="\n".join(lines))

    class Batches:
        def create(self, **kw):
            return NS(id="batch-1")

        def retrieve(self, batch_id):
            return NS(status="completed", output_file_id="file-out", request_counts=None)

    monkeypatch.setattr(llm, "_get_client", lambda: NS(files=Files(), batches=Batches()))
    with batch.mode():
        with pytest.raises(llm.Deferred):
            llm.chat("hola", model="m")
        assert batch.flush(log=lambda *_: None) == 1
        assert llm.chat("hola", model="m") == "respuesta"      # answered from the cache now
        assert batch.flush(log=lambda *_: None) == 0
    assert submitted[0][0]["url"] == "/v1/chat/completions" and submitted[0][0]["body"]["model"] == "m"
    model, = llm._get_db().execute("SELECT model FROM usage").fetchone()
    assert model == "m@batch"
