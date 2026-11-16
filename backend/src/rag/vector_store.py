"""Accès à la base vectorielle ChromaDB (stockage persistant sur disque)."""

from functools import lru_cache

import chromadb

from src import config


@lru_cache(maxsize=1)
def _client() -> chromadb.ClientAPI:
    """Client Chroma partagé (un seul par processus et par dossier)."""
    return chromadb.PersistentClient(path=str(config.CHROMA_DIR))


def get_collection(reset: bool = False) -> chromadb.Collection:
    """Renvoie la collection de chunks, en la vidant d'abord si `reset` est vrai.

    La distance cosinus est choisie explicitement : Chroma utilise la distance
    L2 par défaut, qui n'est pas adaptée à nos scores de similarité.
    """
    client = _client()
    if reset:
        try:
            client.delete_collection(config.COLLECTION_NAME)
        except Exception:  # collection absente : rien à supprimer
            pass
    return client.get_or_create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )