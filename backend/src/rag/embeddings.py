"""Calcul des embeddings avec un modèle Hugging Face (bibliothèque sentence-transformers).

Le modèle est choisi dans config.EMBEDDING_MODEL. Il est téléchargé depuis le Hub
Hugging Face au premier usage, puis gardé en cache (dossier ~/.cache/huggingface,
ou HF_HOME). Pour en tester un autre, changer la variable EMBEDDING_MODEL puis
réindexer : les vecteurs de deux modèles différents ne sont pas comparables.
"""

from functools import lru_cache

from src import config


class EmbeddingError(RuntimeError):
    """Le modèle d'embeddings n'a pas pu être chargé ou a échoué."""


@lru_cache(maxsize=1)
def _charger_modele(nom: str, device: str):
    """Charge le modèle une seule fois par processus (le chargement est lent).

    L'import est fait ici et non en haut du fichier : sentence-transformers
    importe PyTorch, ce qui prend plusieurs secondes et n'est inutile ni pour
    les tests ni pour les modules qui n'ont pas besoin d'embeddings.
    """
    try:
        from sentence_transformers import SentenceTransformer

        modele = SentenceTransformer(nom, device=device)
        modele.max_seq_length = config.EMBEDDING_MAX_TOKENS
        return modele
    except Exception as erreur:  # nom invalide, pas de réseau, mémoire insuffisante...
        raise EmbeddingError(
            f"Impossible de charger le modèle '{nom}' : {erreur}"
        ) from erreur


def _encoder(textes: list[str]) -> list[list[float]]:
    """Transforme des textes en vecteurs normalisés (norme 1)."""
    modele = _charger_modele(config.EMBEDDING_MODEL, config.EMBEDDING_DEVICE)
    try:
        vecteurs = modele.encode(
            textes,
            batch_size=config.EMBEDDING_BATCH_SIZE,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
    except Exception as erreur:
        raise EmbeddingError(f"Échec du calcul des embeddings : {erreur}") from erreur
    return vecteurs.tolist()


def embed_documents(textes: list[str]) -> list[list[float]]:
    """Embeddings des textes à indexer (avec le préfixe « document » du modèle)."""
    return _encoder([config.EMBEDDING_DOC_PREFIX + t for t in textes])


def embed_query(question: str) -> list[float]:
    """Embedding d'une question utilisateur (avec le préfixe « question » du modèle)."""
    return _encoder([config.EMBEDDING_QUERY_PREFIX + question])[0]