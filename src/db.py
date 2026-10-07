"""Connexion SQLite et création du schéma de la base."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "books.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY,
    google_id TEXT UNIQUE,
    title TEXT,
    authors TEXT,
    description TEXT,
    categories_raw TEXT,
    main_category TEXT,
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
    password_hash TEXT NOT NULL,
    created_at TEXT,
    profile_label TEXT,
    profile_vector TEXT  -- JSON {catégorie: poids}
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


def init_db(db_path=DB_PATH):
    """Crée les tables et index s'ils n'existent pas encore."""
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)
