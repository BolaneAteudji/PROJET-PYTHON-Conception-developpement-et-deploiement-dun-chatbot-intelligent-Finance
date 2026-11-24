"""Historique des conversations : lecture et écriture dans PostgreSQL.

Les valeurs sont toujours passées en paramètres (%s), jamais dans le texte SQL.
"""

from uuid import UUID

from src import config
from src.database.connexion import connexion


def enregistrer_echange(user_id: str, conversation_id: UUID | None,
                        question: str, reponse: str) -> UUID:
    """Enregistre la question et la réponse, et crée la conversation si besoin.

    Tout se passe dans une seule transaction : si l'insertion des messages
    plante, la conversation n'est pas créée non plus (pas de conversation vide).
    """
    with connexion() as conn:
        if conversation_id is None:
            titre = question[:config.TITRE_MAX_CHARS]
            conversation_id = conn.execute(
                "INSERT INTO conversations (user_id, titre) VALUES (%s, %s) RETURNING id",
                (user_id, titre),
            ).fetchone()[0]
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content) "
            "VALUES (%s, 'user', %s), (%s, 'assistant', %s)",
            (conversation_id, question, conversation_id, reponse),
        )
    return conversation_id


def conversation_de(user_id: str, conversation_id: UUID) -> bool:
    """True si la conversation existe et appartient bien à cet utilisateur."""
    with connexion() as conn:
        ligne = conn.execute(
            "SELECT 1 FROM conversations WHERE id = %s AND user_id = %s",
            (conversation_id, user_id),
        ).fetchone()
    return ligne is not None
