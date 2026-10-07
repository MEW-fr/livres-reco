"""Connexion SQLite et création du schéma de la base."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "books.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY,
    google_id TEXT UNIQUE,
    title TEXT,
    authors TEXT,
    description TEXT,
    categories_raw TEXT,  -- JSON, catégories Google Books
    main_category TEXT,
    categories TEXT,      -- JSON, catégories cibles sous lesquelles le livre a été collecté
    themes TEXT,          -- JSON, liste de thèmes (src.tagging)
    ambiance TEXT,        -- JSON, ambiance ou null (src.tagging)
    published_year INTEGER,
    page_count INTEGER,
    language TEXT,
    isbn TEXT,
    thumbnail TEXT,
    info_link TEXT,
    avg_rating REAL,
    ratings_count INTEGER
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT,
    password_hash TEXT NOT NULL,
    created_at TEXT,
    profile_label TEXT,
    profile_vector TEXT,  -- JSON, profil complet (src.profile.build_profile)
    profile_confidence REAL,
    profile_family TEXT   -- famille du profil (src.profile.FAMILY_OF)
);

CREATE TABLE IF NOT EXISTS survey_answers (
    user_id INTEGER NOT NULL REFERENCES users(id),
    question_id TEXT NOT NULL,
    answer TEXT,
    answered_at TEXT,
    PRIMARY KEY (user_id, question_id)
);

CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    book_id INTEGER NOT NULL REFERENCES books(id),
    start_date TEXT,
    end_date TEXT,
    rating INTEGER,
    comment TEXT
);

CREATE INDEX IF NOT EXISTS idx_readings_user ON readings(user_id);
CREATE INDEX IF NOT EXISTS idx_readings_book ON readings(book_id);
CREATE INDEX IF NOT EXISTS idx_readings_start ON readings(start_date);
"""


def get_connection(db_path=DB_PATH):
    """Ouvre une connexion SQLite (lignes accessibles par nom de colonne)."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


BOOKS_NEW_COLUMNS = {"categories", "themes", "ambiance"}
USERS_NEW_COLUMNS = {"email": "TEXT", "profile_confidence": "REAL", "profile_family": "TEXT"}


def init_db(db_path=DB_PATH):
    """Crée les tables et index s'ils n'existent pas encore.

    Si la table books date d'un ancien schéma (colonnes manquantes), elle est
    supprimée puis recréée : son contenu est régénéré par src.clean.
    """
    with get_connection(db_path) as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(books)")}
        if columns and not BOOKS_NEW_COLUMNS <= columns:
            conn.execute("DROP TABLE books")
        conn.executescript(SCHEMA)
        # Colonnes ajoutées à users après coup : ajoutées sans perdre les comptes.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
        for name, sql_type in USERS_NEW_COLUMNS.items():
            if name not in columns:
                conn.execute(f"ALTER TABLE users ADD COLUMN {name} {sql_type}")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")


# --- Profil et réponses au questionnaire ---------------------------------------------

def save_profile(user_id, profile, db_path=DB_PATH):
    """Enregistre le profil (JSON), son libellé, sa confiance et sa famille."""
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE users SET profile_vector = ?, profile_label = ?, profile_confidence = ?,"
            " profile_family = ? WHERE id = ?",
            (json.dumps(profile, ensure_ascii=False), profile["label"], profile["confidence"],
             profile["family"], user_id),
        )


def load_profile(user_id, db_path=DB_PATH):
    """Profil de l'utilisateur, ou None s'il n'a pas encore été calculé."""
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT profile_vector FROM users WHERE id = ?", (user_id,)).fetchone()
    return json.loads(row["profile_vector"]) if row and row["profile_vector"] else None


def save_answer(user_id, question_id, answer, db_path=DB_PATH):
    """Enregistre (ou remplace) la réponse à une question : code ou liste de codes."""
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO survey_answers (user_id, question_id, answer, answered_at)"
            " VALUES (?, ?, ?, ?)",
            (user_id, question_id, json.dumps(answer, ensure_ascii=False),
             datetime.now().isoformat(timespec="seconds")),
        )


def load_answers(user_id, db_path=DB_PATH):
    """{question_id: réponse} de l'utilisateur."""
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT question_id, answer FROM survey_answers WHERE user_id = ?",
                            (user_id,)).fetchall()
    return {row["question_id"]: json.loads(row["answer"]) for row in rows}


# --- Comptes utilisateurs ---------------------------------------------------------------

def create_user(username, email, password_hash, db_path=DB_PATH):
    """Crée un compte et renvoie son id."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (username, email, password_hash, datetime.now().isoformat(timespec="seconds")),
        )
        return cursor.lastrowid


def find_user(login, db_path=DB_PATH):
    """Utilisateur dont le pseudo ou l'e-mail vaut login (sans tenir compte de la casse)."""
    with get_connection(db_path) as conn:
        return conn.execute(
            "SELECT * FROM users WHERE lower(username) = lower(?) OR lower(email) = lower(?)",
            (login, login),
        ).fetchone()


def get_user(user_id, db_path=DB_PATH):
    with get_connection(db_path) as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
