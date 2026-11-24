"""Connexion à PostgreSQL.

Les identifiants sont lus dans le .env à la racine du projet (voir .env.example).
Sous Docker, ils arrivent directement en variables d'environnement.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from dotenv import load_dotenv

from src import config

load_dotenv(config.BACKEND_DIR.parent / ".env")


class BaseIndisponible(Exception):
    """La base ne répond pas ou la configuration est incomplète."""


def _parametres() -> dict:
    manquantes = [v for v in ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
                  if not os.getenv(v)]
    if manquantes:
        raise BaseIndisponible(f"Variables absentes du .env : {', '.join(manquantes)}")
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
        "dbname": os.getenv("POSTGRES_DB"),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
    }


@contextmanager
def connexion() -> Iterator[psycopg.Connection]:
    """Ouvre une connexion le temps d'un bloc `with`.

    Commit à la sortie du bloc, rollback si une erreur s'y produit.
    """
    try:
        conn = psycopg.connect(**_parametres(), connect_timeout=5)
    except psycopg.OperationalError as erreur:
        raise BaseIndisponible(f"Connexion à PostgreSQL impossible : {erreur}") from erreur
    with conn:
        yield conn


def base_accessible() -> bool:
    try:
        with connexion() as conn:
            conn.execute("SELECT 1")
        return True
    except (BaseIndisponible, psycopg.Error):
        return False
