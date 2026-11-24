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
# Similarité cosinus minimale pour garder un chunk. Calibrée sur le jeu d'évaluation :
# hors domaine < 0,1 ; questions RAG >= 0,13. Les questions du domaine non couvertes
# (PER, SCPI : 0,52 à 0,60) ne sont pas séparables par un seuil : le prompt système
# demande au LLM de dire quand le contexte ne contient pas la réponse.
SIMILARITY_THRESHOLD = 0.20

# API
MESSAGE_MAX_CHARS = 2000  # au-delà, la question est refusée (422)
TITRE_MAX_CHARS = 60  # début du premier message gardé comme titre de conversation
