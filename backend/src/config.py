"""Paramètres centralisés du backend.

Tous les réglages qu'on veut pouvoir faire varier pendant les expériences
(taille des chunks, overlap, etc.) sont ici, et nulle part ailleurs.
"""

from pathlib import Path

# Dossiers
BACKEND_DIR = Path(__file__).resolve().parents[1]
DOCS_DIR = BACKEND_DIR / "data" / "documents"
CHUNKS_PATH = BACKEND_DIR / "data" / "chunks.json"

# Découpage des fiches Markdown, section par section (titres "## ")
# Une section plus courte que CHUNK_MIN_CHARS est regroupée avec la suivante.
CHUNK_MIN_CHARS = 200
# Une section plus longue que CHUNK_MAX_CHARS est redécoupée à taille fixe.
CHUNK_MAX_CHARS = 1200

# Découpage à taille fixe
FIXED_CHUNK_SIZE = 500
FIXED_CHUNK_OVERLAP = 80

#RAG : embeddings
# Modèle multilingue (les fiches sont en français). Changer de modèle impose
# de réindexer : les vecteurs de deux modèles ne sont pas comparables.
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DEVICE = "cpu"
EMBEDDING_BATCH_SIZE = 32
# MiniLM a été entraîné sur des séquences de 128 tokens : au-delà, la fin du
# chunk est tronquée et n'est pas représentée dans le vecteur.
EMBEDDING_MAX_TOKENS = 128
# Préfixes propres à certains modèles (ex. e5 : "query: " / "passage: ").
# MiniLM n'en demande pas : on les laisse vides.
EMBEDDING_QUERY_PREFIX = ""
EMBEDDING_DOC_PREFIX = ""

# RAG : base vectorielle et recherche
CHROMA_DIR = BACKEND_DIR / "data" / "chroma"
COLLECTION_NAME = "finance_docs"
TOP_K = 4
# Similarité cosinus minimale pour garder un chunk (à calibrer sur les
# questions types, voir le rapport).
SIMILARITY_THRESHOLD = 0.30
