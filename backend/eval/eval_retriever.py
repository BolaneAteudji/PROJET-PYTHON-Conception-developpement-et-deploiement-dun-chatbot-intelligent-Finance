"""Évaluation du retriever sur le jeu de questions annoté.

Le script :
    1. reconstruit la base vectorielle avec les réglages actuels de config.py ;
    2. pose les 44 questions RAG et calcule le hit@1, hit@3, hit@5 et le MRR ;
    3. compare les scores des questions RAG à ceux des questions hors corpus
       ou hors domaine, pour aider à choisir le seuil de similarité ;
    4. ajoute une ligne au journal des expériences (eval/experiences.csv).

Il s'appuie sur indexation.indexer() et retriever.retrieve().

Lancement, depuis le dossier backend/ :
    python -m eval.eval_retriever
"""

import csv
import statistics
from datetime import datetime
from pathlib import Path

from src import config
from src.rag.indexation import indexer
from src.rag.retriever import retrieve

EVAL_DIR = Path(__file__).resolve().parent
QUESTIONS_PATH = EVAL_DIR / "eval_questions.csv"
JOURNAL_PATH = EVAL_DIR / "experiences.csv"
VALEURS_K = (1, 3, 5)
SANS_SEUIL = -1.0  # la similarité cosinus est toujours >= -1 : aucun chunk n'est écarté
CATEGORIES_SANS_REPONSE = ("hors_corpus", "hors_domaine")


def charger_questions() -> list[dict]:
    """Lit le jeu d'évaluation (séparateur point-virgule)."""
    with open(QUESTIONS_PATH, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def rang_du_premier_bon(docs_trouves: list[str], docs_attendus: set[str]) -> int | None:
    """Position (1, 2, 3...) du premier chunk venant d'un document attendu, ou None."""
    for rang, doc in enumerate(docs_trouves, start=1):
        if doc in docs_attendus:
            return rang
    return None


def evaluer_rag(questions: list[dict]) -> tuple[dict, list[float]]:
    """Calcule hit@k et MRR sur les questions de catégorie "rag"."""
    rangs, meilleurs_scores, echecs = [], [], []
    for q in questions:
        attendus = set(q["docs_attendus"].split("|"))
        passages = retrieve(q["question"], top_k=max(VALEURS_K), seuil=SANS_SEUIL)
        docs_trouves = [p.doc for p in passages]
        rang = rang_du_premier_bon(docs_trouves, attendus)
        rangs.append(rang)
        meilleurs_scores.append(passages[0].score)
        if rang is None or rang > 3:
            echecs.append((q["id"], q["question"], docs_trouves[:3]))

    n = len(rangs)
    resultats = {f"hit@{k}": sum(r is not None and r <= k for r in rangs) / n for k in VALEURS_K}
    # MRR : moyenne de 1/rang du premier bon document (0 s'il n'est pas dans le top 5)
    resultats["MRR"] = sum(1 / r for r in rangs if r is not None) / n

    print(f"\nQuestions RAG : {n}")
    for nom, valeur in resultats.items():
        print(f"  {nom:6} = {valeur:.1%}" if nom != "MRR" else f"  {nom:6} = {valeur:.3f}")
    print(f"\nQuestions dont le bon document n'est pas dans le top 3 : {len(echecs)}")
    for id_q, question, docs in echecs:
        print(f"  {id_q} | {question}\n        trouvé : {', '.join(docs)}")
    return resultats, meilleurs_scores


def comparer_scores(questions: list[dict], scores_rag: list[float]) -> None:
    """Compare le meilleur score des questions RAG à celui des questions sans réponse.

    Seules les questions hors corpus ou hors domaine sans document attendu sont
    retenues : les questions de tools n'ont pas de document attendu non plus,
    mais elles parlent de finance et ressemblent donc naturellement aux fiches.
    """
    sans_reponse = [
        q for q in questions
        if q["categorie"] in CATEGORIES_SANS_REPONSE and not q["docs_attendus"]
    ]
    print("\nMeilleur score des questions sans réponse dans les documents :")
    scores_vides = []
    for q in sans_reponse:
        meilleur = retrieve(q["question"], top_k=1, seuil=SANS_SEUIL)[0]
        scores_vides.append(meilleur.score)
        print(f"  {q['id']} | {meilleur.score:.3f} | {q['question']}  (trouvé : {meilleur.doc})")

    print("\nPour choisir le seuil :")
    print(f"  questions RAG          : min {min(scores_rag):.3f}, "
          f"médiane {statistics.median(scores_rag):.3f}")
    print(f"  questions sans réponse : max {max(scores_vides):.3f}, "
          f"médiane {statistics.median(scores_vides):.3f}")
    rag_sous_seuil = sum(s < config.SIMILARITY_THRESHOLD for s in scores_rag)
    vides_sur_seuil = sum(s >= config.SIMILARITY_THRESHOLD for s in scores_vides)
    print(f"  seuil actuel {config.SIMILARITY_THRESHOLD} : {rag_sous_seuil} question(s) RAG "
          f"écartée(s) à tort, {vides_sur_seuil} question(s) sans réponse laissée(s) passer")


def journaliser(resultats: dict) -> None:
    """Ajoute une ligne au journal des expériences, pour le tableau du rapport."""
    nouveau = not JOURNAL_PATH.exists()
    with open(JOURNAL_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        if nouveau:
            writer.writerow(["date", "modele", "max_tokens", "chunk_min_chars", "fixed_chunk_size",
                             "fixed_chunk_overlap", "top_k", "hit@1", "hit@3", "hit@5", "MRR"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            config.EMBEDDING_MODEL,
            config.EMBEDDING_MAX_TOKENS,
            config.CHUNK_MIN_CHARS,
            config.FIXED_CHUNK_SIZE,
            config.FIXED_CHUNK_OVERLAP,
            config.TOP_K,
            *(f"{resultats[f'hit@{k}']:.3f}" for k in VALEURS_K),
            f"{resultats['MRR']:.3f}",
        ])
    print(f"\nRésultats ajoutés à {JOURNAL_PATH}")


def main() -> None:
    print("Reconstruction de la base vectorielle avec les réglages actuels...")
    print(f"{indexer()} chunks indexés avec {config.EMBEDDING_MODEL}")
    questions = charger_questions()
    resultats, scores_rag = evaluer_rag([q for q in questions if q["categorie"] == "rag"])
    comparer_scores(questions, scores_rag)
    journaliser(resultats)


if __name__ == "__main__":
    main()
