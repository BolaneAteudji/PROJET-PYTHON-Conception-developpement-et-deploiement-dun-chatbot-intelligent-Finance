"""GET /health : l'API répond-elle, et ses dépendances aussi ?"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.api.schemas import HealthResponse
from src.database.connexion import base_accessible
from src.rag.vector_store import get_collection

router = APIRouter(tags=["santé"])


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "La base ou l'index Chroma ne répond pas."}},
)
def health():
    base_ok = base_accessible()
    try:
        chunks = get_collection().count()
    except Exception:  # index Chroma absent ou illisible
        chunks = 0

    tout_va_bien = base_ok and chunks > 0
    etat = HealthResponse(
        status="ok" if tout_va_bien else "degraded",
        database="ok" if base_ok else "unavailable",
        chunks=chunks,
    )
    # 503 pour qu'un outil de surveillance (ou la CI) voie tout de suite le problème
    return JSONResponse(status_code=200 if tout_va_bien else 503, content=etat.model_dump())
