"""Recherche des chunks pertinents pour une question, et mise en forme du contexte."""

from dataclasses import dataclass

from src import config
from src.rag.embeddings import embed_query
from src.rag.vector_store import get_collection


@dataclass
class RetrievedChunk:
    """Un chunk renvoyé par la recherche, avec son score de similarité."""

    chunk_id: str
    doc: str
    titre: str
    section: str
    source: str
    date_maj: str
    contenu: str
    score: float  # similarité cosinus : 1 = identique, 0 = sans rapport


def construire_resultats(brut: dict, seuil: float) -> list[RetrievedChunk]:
    """Convertit la réponse brute de Chroma et écarte les chunks sous le seuil.

    Chroma renvoie une distance cosinus : similarité = 1 - distance.
    """
    chunks = []
    lignes = zip(
        brut["ids"][0], brut["documents"][0], brut["metadatas"][0], brut["distances"][0]
    )
    for chunk_id, contenu, meta, distance in lignes:
        score = 1.0 - distance
        if score < seuil:
            continue
        chunks.append(RetrievedChunk(
            chunk_id=chunk_id,
            doc=meta.get("doc", ""),
            titre=meta.get("titre", ""),
            section=meta.get("section", ""),
            source=meta.get("source", ""),
            date_maj=meta.get("date_maj", ""),
            contenu=contenu,
            score=round(score, 4),
        ))
    return chunks


def retrieve(
    question: str,
    top_k: int | None = None,
    seuil: float | None = None,
) -> list[RetrievedChunk]:
    """Renvoie au plus `top_k` chunks dont le score atteint `seuil`, du meilleur au moins bon.

    Une liste vide signifie « rien de pertinent dans les documents » : à
    l'appelant (le prompt) de dire alors au LLM de ne pas inventer.
    """
    top_k = config.TOP_K if top_k is None else top_k
    seuil = config.SIMILARITY_THRESHOLD if seuil is None else seuil

    collection = get_collection()
    total = collection.count()
    if total == 0:
        raise RuntimeError("Index vide : lancer `python -m src.rag.indexation`")

    brut = collection.query(
        query_embeddings=[embed_query(question)],
        n_results=min(top_k, total),
        include=["documents", "metadatas", "distances"],
    )
    return construire_resultats(brut, seuil)


def format_context(chunks: list[RetrievedChunk]) -> str:
    """Met en forme les chunks pour les injecter dans le prompt du LLM.

    Chaque passage est numéroté et accompagné de sa source et de sa date de mise
    à jour, ce qui permet au LLM de citer ses sources et à l'interface de les
    afficher. Renvoie une chaîne vide s'il n'y a aucun chunk.
    """
    blocs = []
    for i, c in enumerate(chunks, start=1):
        entete = (f"[Source {i}] {c.titre} > {c.section} "
                  f"(source : {c.source}, mise à jour : {c.date_maj})")
        blocs.append(f"{entete}\n{c.contenu}")
    return "\n\n".join(blocs)
