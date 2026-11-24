"""API du chatbot financier.

Lancement depuis backend/ :
    uvicorn main:app --reload
Documentation interactive : http://localhost:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api import chat, sante
from src.database.connexion import BaseIndisponible
from src.rag.embeddings import embed_query

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Le modèle d'embedding met plusieurs secondes à se charger :
    # on le fait au démarrage plutôt qu'à la première question.
    try:
        embed_query("chargement")
    except Exception as erreur:
        logger.warning("Modèle d'embedding non chargé : %s", erreur)
    yield


app = FastAPI(title="Chatbot financier", version="0.1.0", lifespan=lifespan)
app.include_router(sante.router)
app.include_router(chat.router)


@app.exception_handler(BaseIndisponible)
async def base_indisponible(request: Request, erreur: BaseIndisponible):
    logger.error("PostgreSQL : %s", erreur)
    return JSONResponse(status_code=503, content={"detail": "Base de données indisponible."})
