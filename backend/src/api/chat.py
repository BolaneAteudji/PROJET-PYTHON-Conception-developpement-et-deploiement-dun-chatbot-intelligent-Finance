"""POST /chat.

Pour l'instant le LLM n'est pas branché : on renvoie les passages trouvés par le
retriever au lieu d'une vraie réponse. Le reste (validation, conversation,
historique) est déjà définitif. Quand le LLM arrivera, seule `repondre()` changera.
"""

from fastapi import APIRouter, HTTPException

from src.api.schemas import ChatRequest, ChatResponse, Source
from src.database import historique
from src.rag.retriever import RetrievedChunk, retrieve

router = APIRouter(tags=["chat"])


def repondre(passages: list[RetrievedChunk]) -> str:
    """Réponse provisoire, en attendant le LLM."""
    if not passages:
        return "Je n'ai rien trouvé dans mes documents sur ce sujet."
    lignes = ["(Réponse provisoire, le LLM n'est pas encore branché.) Passages trouvés :"]
    for i, p in enumerate(passages, start=1):
        extrait = p.contenu[:200].replace("\n", " ")
        lignes.append(f"[Source {i}] {p.titre} > {p.section} : {extrait}...")
    return "\n".join(lignes)


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        404: {"description": "Conversation inconnue, ou qui appartient à un autre utilisateur."},
        503: {"description": "Base de données ou recherche dans les documents indisponible."},
    },
)
def chat(demande: ChatRequest) -> ChatResponse:
    if demande.conversation_id and not historique.conversation_de(
        demande.user_id, demande.conversation_id
    ):
        raise HTTPException(404, "Conversation introuvable pour cet utilisateur.")

    # On cherche d'abord : si la recherche plante, rien n'est écrit en base.
    try:
        passages = retrieve(demande.message)
    except RuntimeError as erreur:
        raise HTTPException(503, f"Recherche dans les documents impossible : {erreur}")
    reponse = repondre(passages)

    conversation_id = demande.conversation_id or historique.creer_conversation(
        demande.user_id, demande.message
    )
    historique.enregistrer_echange(conversation_id, demande.message, reponse)

    return ChatResponse(
        conversation_id=conversation_id,
        answer=reponse,
        sources=[Source(doc=p.doc, titre=p.titre, section=p.section, score=p.score)
                 for p in passages],
    )
