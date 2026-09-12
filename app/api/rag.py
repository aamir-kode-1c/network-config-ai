from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.rag import ingest_document, search_documents
from app.core.security import require_auth
from app.core.observability import increment

router = APIRouter(prefix="/api/v1/knowledge", tags=["vendor knowledge"])


class IngestRequest(BaseModel):
    vendor: str = Field(min_length=1, max_length=64)
    product: str = Field(min_length=1, max_length=128)
    source_url: str = Field(min_length=12, max_length=2048)
    version: str = Field(default="latest", min_length=1, max_length=64)


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    vendor: str | None = None
    product: str | None = None
    limit: int = Field(default=5, ge=1, le=20)


@router.post("/documents", status_code=201)
def ingest(request: IngestRequest, x_api_key: str | None = Header(default=None), x_actor: str | None = Header(default=None)):
    require_auth(x_api_key=x_api_key, x_actor=x_actor, permission="knowledge:write")
    try:
        increment("ai_tool_invocations_total", {"tool": "knowledge_ingest"})
        return ingest_document(request.vendor, request.product, request.source_url, request.version)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/search")
def search(request: SearchRequest, x_api_key: str | None = Header(default=None), x_actor: str | None = Header(default=None)):
    require_auth(x_api_key=x_api_key, x_actor=x_actor, permission="knowledge:read")
    try:
        increment("ai_tool_invocations_total", {"tool": "knowledge_search"})
        return {"query": request.query, "results": search_documents(request.query, request.vendor, request.product, request.limit)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
