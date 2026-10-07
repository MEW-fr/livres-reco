"""Comptes de démonstration : contraintes de démo, dates, reset, bandeau sur /profil.

Le script tourne sur une base temporaire qui reçoit une copie du catalogue réel."""

from collections import Counter
from datetime import date, timedelta

import pytest

from app import create_app
from conftest import login
from src import db, engine, seed
from src.profile import FAMILIES, FAMILY_OF, build_profile, recompute_learned

TODAY = date(2026, 10, 7)
CATALOG = db.DB_PATH

pytestmark = pytest.mark.skipif(not CATALOG.exists(), reason="catalogue data/books.db absent")


@pytest.fixture
def path(tmp_path):
    path = tmp_path / "books.db"
    db.init_db(path)
    with db.get_connection(path) as conn:
        columns = ", ".join(row["name"] for row in conn.execute("PRAGMA table_info(books)"))
        conn.execute("ATTACH DATABASE ? AS catalog", (str(CATALOG),))
        conn.execute(f"INSERT INTO books ({columns}) SELECT {columns} FROM catalog.books")
    engine.reset_cache()
    yield path
    engine.reset_cache()


def quiet(*_):
    pass


def demo_readings(path):
    with db.get_connection(path) as conn:
        return conn.execute("SELECT u.username, r.* FROM readings r JOIN users u"
                            " ON u.id = r.user_id WHERE u.is_demo = 1").fetchall()


def test_contraintes_de_demo(path):
    result = seed.run(path, today=TODAY, out=quiet)
    assert result["accounts"] == len(seed.PERSONAS)

    # (a) au moins 20 lecteurs cette semaine ; 5 livres du moment à 4-8 lecteurs chacun.
    assert result["week_readers"] >= 20
    assert sum(4 <= n <= 8 for _, n in result["popular"]) >= 5
    # (b) au moins 6 lecteurs contributeurs et 3 livres terminés en commun par famille.
    families = result["families"]
    assert set(families) == set(FAMILIES)
    for data in families.values():
        assert data["members"] >= 6 and data["contributors"] == data["members"]
        assert len(data["shared"]) >= 3
    # Première vague : 4 livres terminés par au moins 5 des 6 premiers suspense.
    assert sum(n >= 5 for n in families["suspense"]["shared"]) >= 4


def test_livres_du_moment(path):
    result = seed.run(path, today=TODAY, out=quiet)
    index = engine.get_index(path)
    by_title = {b["title"]: b for b in index.books}
    moments = [by_title[title] for title, n in result["popular"] if 4 <= n <= 8]
    assert sorted(FAMILY_OF[b["main_category"]] for b in moments) == sorted(seed.MOMENT_FAMILIES)
    for book in moments:
        assert len(book["description"]) >= seed.MOMENT_MIN_DESCRIPTION
        assert not any(word in book["title"].lower() for word in seed.MOMENT_BANNED)
        assert "\ufffd" not in book["description"]


def test_premiere_vague_inchangee(path):
    """Les personas de la première vague ne dépendent pas de la seconde."""
    first = seed.PERSONAS[:seed.FIRST_WAVE]
    seed.run(path, today=TODAY, out=quiet)
    full = {(r["username"], r["book_id"], r["rank"], r["start_date"], r["end_date"], r["rating"],
             r["comment"]) for r in demo_readings(path) if r["username"] in {p[0] for p in first}}
    original = seed.PERSONAS
    try:
        seed.PERSONAS = first
        seed.run(path, reset=True, today=TODAY, out=quiet)
    finally:
        seed.PERSONAS = original
    assert {(r["username"], r["book_id"], r["rank"], r["start_date"], r["end_date"], r["rating"],
             r["comment"]) for r in demo_readings(path)} == full


def test_aucun_livre_masque(path):
    with db.get_connection(path) as conn:
        hidden = conn.execute("SELECT id FROM books WHERE hidden = 0 LIMIT 1").fetchone()["id"]
        conn.execute("UPDATE books SET hidden = 1 WHERE id = ?", (hidden,))
    engine.reset_cache()
    seed.run(path, today=TODAY, out=quiet)
    with db.get_connection(path) as conn:
        assert not conn.execute("SELECT 1 FROM readings r JOIN books b ON b.id = r.book_id"
                                " WHERE b.hidden = 1").fetchone()


def test_lectures_coherentes(path):
    seed.run(path, today=TODAY, out=quiet)
    rows = demo_readings(path)
    totals = {row[0]: row[-1] for row in seed.PERSONAS}
    for pseudo, total in totals.items():
        mine = [r for r in rows if r["username"] == pseudo]
        statuses = [db.reading_status(r) for r in mine]
        assert len(mine) == total
        assert statuses.count(db.TO_READ) in (2, 3)
        assert statuses.count(db.READING) <= 2
        assert sorted(r["rank"] for r in mine if r["rank"]) == list(
            range(1, statuses.count(db.TO_READ) + 1))

    for r in rows:
        if r["start_date"]:
            assert date.fromisoformat(r["start_date"]) <= TODAY
        if r["end_date"]:
            start, end = date.fromisoformat(r["start_date"]), date.fromisoformat(r["end_date"])
            assert TODAY - timedelta(days=90) <= start
            assert 5 <= (end - start).days <= 30 and end <= TODAY
        else:
            assert r["rating"] is None
    # Notes et commentaires : tirés vague par vague.
    for wave in (seed.PERSONAS[:seed.FIRST_WAVE], seed.PERSONAS[seed.FIRST_WAVE:]):
        pseudos = {row[0] for row in wave}
        finished = [r for r in rows if r["end_date"] and r["username"] in pseudos]
        rated = [r for r in finished if r["rating"]]
        assert len(finished) - len(rated) == round(0.2 * len(finished))
        assert sum(r["comment"] is not None for r in rated) == round(len(rated) / 2)


def test_profils_et_filtres(path):
    seed.run(path, today=TODAY, out=quiet)
    with db.get_connection(path) as conn:
        users = {u["username"]: u for u in conn.execute("SELECT * FROM users WHERE is_demo = 1")}
    assert users["aline"]["email"] == "aline@exemple.fr"
    assert users["karim"]["profile_family"] == "suspense"
    assert users["marc"]["profile_family"] == "psychologie"
    assert users["camille"]["profile_family"] == "éclectique"
    families = Counter(u["profile_family"] for u in users.values())
    assert families == {"suspense": 11, "psychologie": 11, "imaginaire": 6, "histoire": 6,
                        "réel et idées": 6, "éclectique": 6}
    assert db.get_filters(users["antoine"]["id"], path)["exclusions"] == ["romance", "fantasy"]
    # Profil enregistré = profil du questionnaire recalculé avec toutes les notes, dans
    # l'ordre où l'application les relit (save_learned).
    index = engine.get_index(path)
    for row in seed.PERSONAS:
        user_id = users[row[0]]["id"]
        notes = [(index.books[index.row_of[book_id]], rating)
                 for book_id, rating in db.list_ratings(user_id, path)]
        expected = recompute_learned(build_profile(seed.answers_of(row)), notes)
        assert db.load_profile(user_id, path) == expected


def test_reset_et_refus(path):
    real = db.create_user("vrai", "vrai@example.com", "x", path)
    first = seed.run(path, today=TODAY, out=quiet)
    snapshot = {(r["username"], r["book_id"], r["start_date"], r["end_date"], r["rating"])
                for r in demo_readings(path)}

    with pytest.raises(seed.SeedError):
        seed.run(path, today=TODAY, out=quiet)
    again = seed.run(path, reset=True, today=TODAY, out=quiet)
    assert again["accounts"] == first["accounts"]
    assert {(r["username"], r["book_id"], r["start_date"], r["end_date"], r["rating"])
            for r in demo_readings(path)} == snapshot  # graine fixe : même résultat
    assert db.get_user(real, path) is not None  # les vrais comptes ne sont pas touchés


def test_pseudo_deja_pris(path):
    db.create_user("aline", "aline@example.com", "x", path)
    with pytest.raises(seed.SeedError):
        seed.run(path, today=TODAY, out=quiet)


def test_bandeau_compte_de_demonstration(path):
    seed.run(path, today=TODAY, out=quiet)
    client = create_app({"TESTING": True, "SECRET_KEY": "test", "DB_PATH": path}).test_client()
    login(client, db.find_user("aline", path)["id"])
    assert "Compte de démonstration" in client.get("/profil").get_data(as_text=True)
