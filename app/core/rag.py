"""Versioned vendor-documentation RAG using SQLite FTS and local embeddings."""

from __future__ import annotations

import hashlib
import html
import ipaddress
import json
import math
import os
import re
import socket
import sqlite3
import urllib.parse
import urllib.request
import uuid
from html.parser import HTMLParser
from typing import Any

from app.core.observability import increment


RAG_DB_PATH = os.getenv("RAG_DB_PATH", os.path.join("configs", "vendor_knowledge.db"))
EMBEDDING_DIMENSIONS = 256


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._ignored = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "nav", "footer"}:
            self._ignored += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "nav", "footer"} and self._ignored:
            self._ignored -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored:
            self.parts.append(data)


def _clean_document(raw: bytes, content_type: str) -> str:
    text = raw.decode("utf-8", errors="replace")
    if "json" in content_type or text.lstrip().startswith(("{", "[")):
        try:
            return json.dumps(json.loads(text), indent=2)
        except json.JSONDecodeError:
            pass
    parser = _TextParser()
    parser.feed(text)
    return re.sub(r"\s+", " ", html.unescape(" ".join(parser.parts))).strip()


def _safe_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only absolute HTTP(S) documentation URLs are allowed")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise ValueError("Documentation host cannot be resolved") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("Private and local documentation hosts are not allowed")
    return url


def _embedding(text: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    tokens = re.findall(r"[a-z0-9][a-z0-9_.:-]*", text.lower())
    for token in tokens:
        digest = hashlib.sha256(token.encode()).digest()
        index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _db() -> sqlite3.Connection:
    path = os.getenv("RAG_DB_PATH", RAG_DB_PATH)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS rag_documents (
        id TEXT PRIMARY KEY, vendor TEXT NOT NULL, product TEXT NOT NULL,
        source_url TEXT NOT NULL, version TEXT NOT NULL, content_hash TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS rag_chunks (
        id TEXT PRIMARY KEY, document_id TEXT NOT NULL, chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL, embedding TEXT NOT NULL,
        FOREIGN KEY(document_id) REFERENCES rag_documents(id)
    )""")
    db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunks_fts USING fts5(id UNINDEXED, content)")
    db.commit()
    return db


def _chunks(text: str, size: int = 1200, overlap: int = 150) -> list[str]:
    words = text.split()
    result = []
    step = max(1, size - overlap)
    for start in range(0, len(words), step):
        chunk = " ".join(words[start:start + size])
        if chunk:
            result.append(chunk)
    return result


def ingest_document(vendor: str, product: str, source_url: str, version: str = "latest") -> dict[str, Any]:
    url = _safe_url(source_url)
    request = urllib.request.Request(url, headers={"User-Agent": "network-config-ai-rag/1.0", "Accept": "text/html, application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read()
            text = _clean_document(raw, response.headers.get("Content-Type", ""))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Documentation import failed: {exc}") from exc
    if not text:
        raise ValueError("Documentation source contained no readable text")
    digest = hashlib.sha256(text.encode()).hexdigest()
    db = _db()
    existing = db.execute("SELECT id FROM rag_documents WHERE vendor=? AND product=? AND version=? AND content_hash=?", (vendor.lower(), product, version, digest)).fetchone()
    if existing:
        db.close()
        return {"document_id": existing["id"], "status": "unchanged", "chunks": 0, "citation": {"url": url, "version": version}}
    document_id = f"doc-{uuid.uuid4().hex[:12]}"
    db.execute("INSERT INTO rag_documents(id,vendor,product,source_url,version,content_hash) VALUES(?,?,?,?,?,?)", (document_id, vendor.lower(), product, url, version, digest))
    chunks = _chunks(text)
    for index, content in enumerate(chunks):
        chunk_id = f"{document_id}-{index}"
        db.execute("INSERT INTO rag_chunks(id,document_id,chunk_index,content,embedding) VALUES(?,?,?,?,?)", (chunk_id, document_id, index, content, json.dumps(_embedding(content))))
        db.execute("INSERT INTO rag_chunks_fts(id,content) VALUES(?,?)", (chunk_id, content))
    db.commit()
    db.close()
    return {"document_id": document_id, "status": "indexed", "chunks": len(chunks), "citation": {"url": url, "version": version}}


def ingest_text(vendor: str, product: str, text: str, source_url: str, version: str = "latest") -> dict[str, Any]:
    increment("ai_tool_invocations_total", {"tool": "local_knowledge_ingest"})
    if not text.strip():
        raise ValueError("Document content must not be empty")
    digest = hashlib.sha256(text.encode()).hexdigest()
    db = _db()
    existing = db.execute(
        "SELECT id FROM rag_documents WHERE vendor=? AND product=? AND version=? AND content_hash=?",
        (vendor.lower(), product, version, digest),
    ).fetchone()
    if existing:
        db.close()
        return {"document_id": existing["id"], "status": "unchanged", "chunks": 0, "citation": {"url": source_url, "version": version}}
    document_id = f"doc-{uuid.uuid4().hex[:12]}"
    db.execute(
        "INSERT INTO rag_documents(id,vendor,product,source_url,version,content_hash) VALUES(?,?,?,?,?,?)",
        (document_id, vendor.lower(), product, source_url, version, digest),
    )
    chunks = _chunks(text)
    for index, content in enumerate(chunks):
        chunk_id = f"{document_id}-{index}"
        db.execute(
            "INSERT INTO rag_chunks(id,document_id,chunk_index,content,embedding) VALUES(?,?,?,?,?)",
            (chunk_id, document_id, index, content, json.dumps(_embedding(content))),
        )
        db.execute("INSERT INTO rag_chunks_fts(id,content) VALUES(?,?)", (chunk_id, content))
    db.commit()
    db.close()
    return {"document_id": document_id, "status": "indexed", "chunks": len(chunks), "citation": {"url": source_url, "version": version}}


def search_documents(query: str, vendor: str | None = None, product: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    if not query.strip():
        raise ValueError("query must not be empty")
    limit = max(1, min(limit, 20))
    db = _db()
    rows = db.execute("""SELECT c.content,c.embedding,c.chunk_index,d.vendor,d.product,d.source_url,d.version
        FROM rag_chunks c JOIN rag_documents d ON d.id=c.document_id
        WHERE (? IS NULL OR d.vendor=?) AND (? IS NULL OR d.product=?)""", (vendor, vendor, product, product)).fetchall()
    query_vector = _embedding(query)
    results = []
    for row in rows:
        vector = json.loads(row["embedding"])
        score = sum(a * b for a, b in zip(query_vector, vector))
        results.append({"score": round(score, 6), "content": row["content"], "citation": {"url": row["source_url"], "vendor": row["vendor"], "product": row["product"], "version": row["version"], "chunk": row["chunk_index"]}})
    db.close()
    return sorted(results, key=lambda item: item["score"], reverse=True)[:limit]
