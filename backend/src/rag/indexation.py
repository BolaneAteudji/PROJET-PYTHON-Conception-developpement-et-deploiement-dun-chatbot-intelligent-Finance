"""Indexation : documents -> chunks -> embeddings -> base vectorielle.

Lancement, depuis le dossier backend/ :
    python -m src.rag.indexation

L'index est reconstruit entièrement à chaque lancement : c'est simple et
reproductible, et le corpus est petit. Au premier lancement, le modèle
d'embeddings est téléchargé depuis Hugging Face (puis mis en cache).
"""

import time
from collections import Counter

from src import config
from src.rag import ingestion
from src.rag.embeddings import embed_documents
from src.rag.vector_store import get_collection


def verifier_ids_uniques(chunks: list[ingestion.Chunk]) -> None:
    """Refuse d'indexer si deux chunks ont le même identifiant.

    Chroma écraserait silencieusement l'un des deux (par exemple si pea.md
    et pea.pdf coexistent, car leurs chunk_id commencent tous deux par "pea-").
    """
    doublons = [i for i, n in Counter(c.chunk_id for c in chunks).items() if n > 1]
    if doublons:
        raise ValueError(f"chunk_id en double : {doublons[:5]}")


def indexer() -> int:
    """Reconstruit l'index vectoriel et renvoie le nombre de chunks indexés."""
    chunks = ingestion.ingerer_dossier(config.DOCS_DIR)
    if not chunks:
        raise ValueError(f"Aucun document exploitable dans {config.DOCS_DIR}")
    verifier_ids_uniques(chunks)

    collection = get_collection(reset=True)
    taille = config.EMBEDDING_BATCH_SIZE
    for debut in range(0, len(chunks), taille):
        lot = chunks[debut:debut + taille]
        collection.upsert(
            ids=[c.chunk_id for c in lot],
            embeddings=embed_documents([c.texte_a_indexer() for c in lot]),
            documents=[c.contenu for c in lot],
            metadatas=[
                {
                    "doc": c.doc,
                    "titre": c.titre,
                    "section": c.section,
                    "source": c.source,
                    "date_maj": c.date_maj,
                }
                for c in lot
            ],
        )
    return len(chunks)


def main() -> None:
    debut = time.perf_counter()
    nombre = indexer()
    duree = time.perf_counter() - debut
    print(f"{nombre} chunks indexés dans '{config.COLLECTION_NAME}' "
          f"avec {config.EMBEDDING_MODEL} en {duree:.1f} s")


if __name__ == "__main__":
    main()
