"""Pipeline d'ingestion du RAG : charger les documents, puis les découper en chunks.

Étapes :
    1. Chargement : lire chaque fichier (.md ou .pdf) et extraire ses métadonnées.
    2. Découpage : transformer chaque document en une liste de chunks.
    3. Sauvegarde : écrire les chunks dans un fichier JSON pour les inspecter.

Les embeddings et l'indexation dans la base vectorielle viendront à l'étape suivante.

Lancement, depuis le dossier backend/ :
    python -m src.rag.ingestion
"""

import json
import re
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path

from pypdf import PdfReader

from src import config

# En-tête en haut des fiches Markdown, entre deux lignes "---"
FRONT_MATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


@dataclass
class Document:
    """Un document chargé, avant découpage."""

    doc: str        # nom du fichier, par exemple "pea.md"
    titre: str
    source: str
    date_maj: str
    corps: str      # texte complet, sans l'en-tête


@dataclass
class Chunk:
    """Un morceau de document, prêt à être transformé en embedding."""

    chunk_id: str
    doc: str
    titre: str
    section: str
    source: str
    date_maj: str
    contenu: str

    def texte_a_indexer(self) -> str:
        """Texte envoyé au modèle d'embedding.

        On ajoute le titre du document et le nom de la section devant le contenu,
        car beaucoup de sections ont des noms génériques ("Définition", "Limites")
        qui ne disent pas de quoi elles parlent.
        """
        return f"{self.titre} > {self.section}\n{self.contenu}"


# --------------------------------------------------------------------------
# 1. Chargement
# --------------------------------------------------------------------------

def lire_entete(bloc: str) -> dict[str, str]:
    """Lit l'en-tête "cle: valeur", une clé par ligne.

    On coupe seulement au premier ":" de chaque ligne. Un vrai parseur YAML
    échouerait sur un titre comme "OPCVM, SICAV et FCP : les fonds...".
    """
    meta = {}
    for ligne in bloc.splitlines():
        if ":" in ligne:
            cle, valeur = ligne.split(":", 1)
            meta[cle.strip()] = valeur.strip()
    return meta


def charger_markdown(chemin: Path) -> Document:
    """Lit une fiche Markdown et sépare l'en-tête du corps du texte."""
    texte = chemin.read_text(encoding="utf-8")
    entete = FRONT_MATTER.match(texte)
    meta = lire_entete(entete.group(1)) if entete else {}
    corps = texte[entete.end():] if entete else texte
    return Document(
        doc=chemin.name,
        titre=str(meta.get("titre", chemin.stem)),
        source=str(meta.get("source", "inconnue")),
        date_maj=str(meta.get("date_maj", "inconnue")),
        corps=corps,
    )


def charger_pdf(chemin: Path) -> Document:
    """Extrait le texte d'un PDF. Sa première ligne sert de titre."""
    pages = [page.extract_text() or "" for page in PdfReader(chemin).pages]
    lignes = [ligne.strip() for ligne in "\n".join(pages).splitlines() if ligne.strip()]
    titre = lignes[0] if lignes else chemin.stem
    return Document(
        doc=chemin.name,
        titre=titre,
        source="Guide PDF rédigé par le groupe",
        date_maj="inconnue",
        corps=" ".join(lignes[1:]),
    )


CHARGEURS = {".md": charger_markdown, ".pdf": charger_pdf}


# --------------------------------------------------------------------------
# 2. Découpage
# --------------------------------------------------------------------------

def decouper_taille_fixe(texte: str, taille: int, overlap: int) -> list[str]:
    """Découpe un texte en morceaux d'environ `taille` caractères.

    Deux morceaux consécutifs partagent `overlap` caractères, pour ne pas couper
    une idée en deux. Les coupures se font entre deux mots.
    """
    texte = " ".join(texte.split())  # espaces et retours à la ligne normalisés
    morceaux = []
    debut = 0
    while debut < len(texte):
        fin = min(debut + taille, len(texte))
        if fin < len(texte):
            espace = texte.rfind(" ", debut, fin)
            if espace > debut:
                fin = espace
        morceaux.append(texte[debut:fin].strip())
        if fin >= len(texte):
            break
        # On recule de `overlap` caractères, puis on se cale au début d'un mot.
        debut = max(fin - overlap, debut + 1)
        espace = texte.find(" ", debut, fin)
        if espace != -1:
            debut = espace + 1
    return morceaux


def lire_sections(corps: str) -> list[tuple[str, str]]:
    """Coupe une fiche Markdown en sections (nom, contenu) aux titres "## "."""
    sections = []
    nom, lignes = "Introduction", []
    for ligne in corps.splitlines():
        if ligne.startswith("## "):
            if "\n".join(lignes).strip():
                sections.append((nom, "\n".join(lignes).strip()))
            nom, lignes = ligne[3:].strip(), []
        elif not ligne.startswith("# "):  # le titre "# " est déjà dans les métadonnées
            lignes.append(ligne)
    if "\n".join(lignes).strip():
        sections.append((nom, "\n".join(lignes).strip()))
    return sections


def nouveau_chunk(document: Document, numero: int, section: str, contenu: str) -> Chunk:
    """Crée un chunk qui hérite des métadonnées de son document."""
    return Chunk(
        chunk_id=f"{Path(document.doc).stem}-{numero:02d}",
        doc=document.doc,
        titre=document.titre,
        section=section,
        source=document.source,
        date_maj=document.date_maj,
        contenu=contenu,
    )


def decouper_markdown(document: Document) -> list[Chunk]:
    """Une section = un chunk, sauf deux cas.

    Les sections trop courtes sont regroupées avec les suivantes (c'est le cas
    du glossaire), et les sections trop longues sont redécoupées à taille fixe.
    """
    chunks: list[Chunk] = []
    en_attente: list[tuple[str, str]] = []  # sections courtes à regrouper

    def vider_attente() -> None:
        if not en_attente:
            return
        if len(en_attente) == 1:
            nom, contenu = en_attente[0]
        else:
            nom = ", ".join(n for n, _ in en_attente)
            contenu = "\n\n".join(f"{n} : {c}" for n, c in en_attente)
        chunks.append(nouveau_chunk(document, len(chunks), nom, contenu))
        en_attente.clear()

    for nom, contenu in lire_sections(document.corps):
        if len(contenu) > config.CHUNK_MAX_CHARS:
            vider_attente()
            morceaux = decouper_taille_fixe(
                contenu, config.FIXED_CHUNK_SIZE, config.FIXED_CHUNK_OVERLAP
            )
            for i, morceau in enumerate(morceaux, start=1):
                chunks.append(nouveau_chunk(document, len(chunks), f"{nom} ({i})", morceau))
            continue
        en_attente.append((nom, contenu))
        if sum(len(c) for _, c in en_attente) >= config.CHUNK_MIN_CHARS:
            vider_attente()
    vider_attente()
    return chunks


def decouper_pdf(document: Document) -> list[Chunk]:
    """Les PDF n'ont pas de titres "## " fiables : découpage à taille fixe."""
    morceaux = decouper_taille_fixe(
        document.corps, config.FIXED_CHUNK_SIZE, config.FIXED_CHUNK_OVERLAP
    )
    return [
        nouveau_chunk(document, i, f"partie {i + 1}", morceau)
        for i, morceau in enumerate(morceaux)
    ]


# --------------------------------------------------------------------------
# 3. Pipeline complet
# --------------------------------------------------------------------------

def ingerer_dossier(dossier: Path) -> list[Chunk]:
    """Charge et découpe tous les documents .md et .pdf d'un dossier."""
    chunks: list[Chunk] = []
    for chemin in sorted(dossier.iterdir()):
        chargeur = CHARGEURS.get(chemin.suffix.lower())
        if chargeur is None:
            print(f"Ignoré (format non pris en charge) : {chemin.name}")
            continue
        document = chargeur(chemin)
        if chemin.suffix.lower() == ".pdf":
            chunks.extend(decouper_pdf(document))
        else:
            chunks.extend(decouper_markdown(document))
    return chunks


def sauvegarder(chunks: list[Chunk], chemin: Path) -> None:
    """Écrit les chunks en JSON, avec le texte qui sera indexé."""
    donnees = [asdict(c) | {"texte_a_indexer": c.texte_a_indexer()} for c in chunks]
    chemin.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    chunks = ingerer_dossier(config.DOCS_DIR)
    sauvegarder(chunks, config.CHUNKS_PATH)
    tailles = [len(c.contenu) for c in chunks]
    print(f"{len({c.doc for c in chunks})} documents -> {len(chunks)} chunks")
    print(f"Taille en caractères : min {min(tailles)}, "
          f"médiane {statistics.median(tailles):.0f}, max {max(tailles)}")
    print(f"Chunks écrits dans {config.CHUNKS_PATH}")


if __name__ == "__main__":
    main()
