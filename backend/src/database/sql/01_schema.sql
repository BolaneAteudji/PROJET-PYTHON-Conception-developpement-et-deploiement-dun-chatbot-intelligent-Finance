-- Schéma de la base du chatbot finance : données métier (lues par les tools)
-- et historique des conversations (écrit par l'API).
-- Exécuté automatiquement au premier démarrage du conteneur PostgreSQL.

-- ===================== Données métier =====================

CREATE TABLE users (
    user_id        TEXT PRIMARY KEY,
    nom            TEXT NOT NULL,
    profil_risque  TEXT NOT NULL
                   CHECK (profil_risque IN ('prudent', 'equilibre', 'dynamique')),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE comptes (
    id              SERIAL PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    type_compte     TEXT NOT NULL
                    CHECK (type_compte IN ('PEA', 'CTO', 'ASSURANCE_VIE')),
    date_ouverture  DATE NOT NULL
);

CREATE TABLE securities (
    id            SERIAL PRIMARY KEY,
    ticker        TEXT NOT NULL UNIQUE,
    isin          TEXT UNIQUE,
    nom           TEXT NOT NULL,
    type          TEXT NOT NULL CHECK (type IN ('action', 'etf', 'fonds', 'obligation')),
    secteur       TEXT,
    zone          TEXT,
    devise        CHAR(3) NOT NULL DEFAULT 'EUR',
    eligible_pea  BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE prices (
    security_id  INTEGER NOT NULL REFERENCES securities (id) ON DELETE CASCADE,
    date         DATE NOT NULL,
    cloture      NUMERIC(12, 4) NOT NULL CHECK (cloture > 0),
    PRIMARY KEY (security_id, date)
);

-- Frais en % par an (frais_courants = TER) et en % du montant investi (frais_entree).
CREATE TABLE fund_fees (
    security_id     INTEGER PRIMARY KEY REFERENCES securities (id) ON DELETE CASCADE,
    frais_courants  NUMERIC(5, 3) NOT NULL CHECK (frais_courants >= 0),
    frais_entree    NUMERIC(5, 3) NOT NULL DEFAULT 0 CHECK (frais_entree >= 0)
);

CREATE TABLE transactions (
    id             SERIAL PRIMARY KEY,
    compte_id      INTEGER NOT NULL REFERENCES comptes (id) ON DELETE CASCADE,
    security_id    INTEGER NOT NULL REFERENCES securities (id),
    sens           TEXT NOT NULL CHECK (sens IN ('achat', 'vente')),
    quantite       NUMERIC(14, 4) NOT NULL CHECK (quantite > 0),
    prix_unitaire  NUMERIC(12, 4) NOT NULL CHECK (prix_unitaire > 0),
    frais          NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (frais >= 0),
    date           DATE NOT NULL
);
CREATE INDEX idx_transactions_compte_date ON transactions (compte_id, date);

-- Le portefeuille n'est pas stocké : il se calcule (achats - ventes).
CREATE VIEW positions AS
SELECT c.user_id,
       c.id AS compte_id,
       c.type_compte,
       t.security_id,
       SUM(CASE WHEN t.sens = 'achat' THEN t.quantite ELSE -t.quantite END) AS quantite
FROM transactions t
JOIN comptes c ON c.id = t.compte_id
GROUP BY c.user_id, c.id, c.type_compte, t.security_id
HAVING SUM(CASE WHEN t.sens = 'achat' THEN t.quantite ELSE -t.quantite END) > 0;

-- ===================== Historique des conversations =====================

-- Pas de clé étrangère vers users : tout identifiant saisi dans Streamlit
-- peut avoir des conversations, même sans portefeuille.
CREATE TABLE conversations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     TEXT NOT NULL,
    titre       TEXT NOT NULL DEFAULT 'Nouvelle conversation',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_conversations_user ON conversations (user_id, updated_at DESC);

CREATE TABLE messages (
    id               BIGSERIAL PRIMARY KEY,
    conversation_id  UUID NOT NULL REFERENCES conversations (id) ON DELETE CASCADE,
    role             TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content          TEXT NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_messages_conversation ON messages (conversation_id, id);