"""Historique des conversations : lecture et écriture dans PostgreSQL.

Les valeurs sont toujours passées en paramètres (%s), jamais dans le texte SQL.
"""

from uuid import UUID

from src import config
from src.database.connexion import connexion


def creer_conversation(user_id: str, premier_message: str) -> UUID:
    """Crée une conversation, avec le début du premier message comme titre."""
    titre = premier_message[:config.TITRE_MAX_CHARS]
    with connexion() as conn:
        ligne = conn.execute(
            "INSERT INTO conversations (user_id, titre) VALUES (%s, %s) RETURNING id",
            (user_id, titre),
        ).fetchone()
    return ligne[0]


def conversation_de(user_id: str, conversation_id: UUID) -> bool:
    """True si la conversation existe et appartient bien à cet utilisateur."""
    with connexion() as conn:
        ligne = conn.execute(
            "SELECT 1 FROM conversations WHERE id = %s AND user_id = %s",
            (conversation_id, user_id),
        ).fetchone()
    return ligne is not None


def enregistrer_echange(conversation_id: UUID, question: str, reponse: str) -> None:
    """Enregistre la question et la réponse dans la même transaction."""
    with connexion() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content) "
            "VALUES (%s, 'user', %s), (%s, 'assistant', %s)",
            (conversation_id, question, conversation_id, reponse),
        )
