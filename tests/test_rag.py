import io
import json

from app.core.rag import ingest_document, search_documents


def test_rag_indexes_versioned_document_and_returns_citation(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_DB_PATH", str(tmp_path / "knowledge.db"))

    class Response:
        headers = {"Content-Type": "text/html"}

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return b"<html><h1>Commit confirmed</h1><p>Use candidate validation before deployment.</p></html>"

    monkeypatch.setattr("app.core.rag.urllib.request.urlopen", lambda *args, **kwargs: Response())
    monkeypatch.setattr("app.core.rag.socket.getaddrinfo", lambda *args: [(None, None, None, None, ("93.184.216.34", 0))])

    indexed = ingest_document("cisco", "ASR 9000", "https://docs.example/asr", "7.9")
    assert indexed["status"] == "indexed"
    results = search_documents("candidate validation", "cisco", "ASR 9000")
    assert results
    assert results[0]["citation"]["version"] == "7.9"
    assert results[0]["citation"]["url"] == "https://docs.example/asr"
