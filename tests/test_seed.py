"""Comptes de démonstration : contraintes de démo, dates, reset, bandeau sur /profil.

Le script tourne sur une base temporaire qui reçoit une copie du catalogue réel."""

from datetime import date, timedelta

import pytest

from app import create_app
from conftest import login
from src import db, engine, seed
from src.profile import FAMILY_OF, build_profile, recompute_learned

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

    # (a) au moins 8 lecteurs cette semaine ; 3 livres du moment à 4-6 lecteurs chacun.
    assert result["week_readers"] >= 8
    assert sum(4 <= n <= 6 for _, n in result["popular"]) >= 3
    # (b) 4 livres terminés par au moins 5 des 6 suspense (lucie n'a que 4 lectures dont
    # 2 à lire) ; 3 livres terminés par les 6 psychologie.
    assert result["shared"]["suspense"]["members"] == 6
    assert sum(n >= 5 for n in result["shared"]["suspense"]["books"]) >= 4
    assert result["shared"]["psychologie"]["members"] == 6
    assert sum(n == 6 for n in result["shared"]["psychologie"]["books"]) >= 3
    # Lecteurs contributeurs : au moins 5 en psychologie et en imaginaire.
    contributors = dict(result["contributors"])
    assert contributors["psychologie"] >= 5 and contributors["imaginaire"] >= 5


def test_livres_du_moment(path):
    result = seed.run(path, today=TODAY, out=quiet)
    index = engine.get_index(path)
    by_title = {b["title"]: b for b in index.books}
    moments = [by_title[title] for title, n in result["popular"] if 4 <= n <= 6]
    assert sorted(FAMILY_OF[b["main_category"]] for b in moments) == [
        "imaginaire", "psychologie", "suspense"]
    for book in moments:
        assert len(book["description"]) >= seed.MOMENT_MIN_DESCRIPTION
        assert not any(word in book["title"].lower() for word in seed.MOMENT_BANNED)


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
    finished = [r for r in rows if r["end_date"]]
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
    assert db.get_filters(users["antoine"]["id"], path)["exclusions"] == ["romance", "fantasy"]
    # Profil enregistré = profil du questionnaire recalculé avec toutes les notes.
    index = engine.get_index(path)
    for row in seed.PERSONAS:
        user_id = users[row[0]]["id"]
        notes = [(index.books[index.row_of[r["book_id"]]], r["rating"])
                 for r in db.list_readings(user_id, db_path=path) if r["rating"]]
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
