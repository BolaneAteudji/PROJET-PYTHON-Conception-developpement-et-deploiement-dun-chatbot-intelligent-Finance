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

# Découpage à taille fixe (PDF, et sections trop longues)
FIXED_CHUNK_SIZE = 500
FIXED_CHUNK_OVERLAP = 80
