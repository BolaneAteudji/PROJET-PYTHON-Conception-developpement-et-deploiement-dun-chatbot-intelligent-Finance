"""Formats des requêtes et des réponses de l'API (validés par Pydantic)."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from src import config

# strip_whitespace : "   " devient "" et est donc refusé par min_length
UserId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Texte = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1,
                                         max_length=config.MESSAGE_MAX_CHARS)]


class ChatRequest(BaseModel):
    user_id: UserId = Field(examples=["alice"])
    conversation_id: UUID | None = Field(
        default=None, description="À laisser vide pour commencer une nouvelle conversation."
    )
    message: Texte = Field(examples=["Quel est le plafond du PEA ?"])


class Source(BaseModel):
    doc: str
    titre: str
    section: str
    score: float


class ChatResponse(BaseModel):
    conversation_id: UUID
    answer: str
    sources: list[Source]


class HealthResponse(BaseModel):
    status: str
    database: str
    chunks: int
