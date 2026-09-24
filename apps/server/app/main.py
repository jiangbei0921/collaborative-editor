from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.database.database import init_db, close_db
from app.websocket.server import router as ws_router
from app.websocket.connection import ConnectionManager
from app.types.models import normalize_title


class CreateDocumentRequest(BaseModel):
    title: str = ""


class UpdateTitleRequest(BaseModel):
    title: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()

app = FastAPI(title="协同编辑器 API", version="0.1.0", lifespan=lifespan)
app.include_router(ws_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/documents/{doc_id}")
async def create_document(doc_id: str, body: CreateDocumentRequest) -> dict[str, str]:
    from app.document.service import DocumentService
    await DocumentService.create_document(doc_id, body.title)
    return {"status": "created", "document_id": doc_id}


@app.get("/api/documents/{doc_id}")
async def get_document(doc_id: str):
    from app.document.service import DocumentService
    doc = await DocumentService.get_document(doc_id)
    if doc is None:
        return {"status": "not_found"}
    return doc.model_dump()


@app.patch("/api/documents/{doc_id}/title")
async def update_document_title(doc_id: str, body: UpdateTitleRequest) -> dict[str, str]:
    from app.document.service import DocumentService
    normalized = normalize_title(body.title)
    success = await DocumentService.update_title(doc_id, normalized)
    if not success:
        return {"status": "not_found"}
    await ConnectionManager.broadcast_title_update(doc_id, normalized)
    return {"status": "updated", "document_id": doc_id, "title": normalized}


_dist_dir = Path(__file__).resolve().parent.parent.parent / "web" / "dist"

if _dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=_dist_dir / "assets"), name="static")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        return FileResponse(_dist_dir / "index.html")