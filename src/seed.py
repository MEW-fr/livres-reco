"""Comptes fictifs de démonstration, identifiés comme tels (users.is_demo = 1).

Ils peuplent les sections communautaires de l'accueil (« Les lecteurs comme toi »,
« Populaires cette semaine »). Aucune donnée fictive n'est créée hors de ce script.

Usage :
  python -m src.seed           crée les comptes (refuse si des comptes démo existent déjà)
  python -m src.seed --reset   supprime les comptes démo et leurs données, puis recrée tout

Chaque persona (e-mail <pseudo>@exemple.fr, mot de passe commun « demo1234 ») répond au
questionnaire, puis suit des livres tirés de ses recommandations (plus 1 ou 2 hors profil).
Les dates sont relatives à aujourd'hui ; la graine aléatoire est fixe (résultat reproductible).
"""

import json
import random
import sys
from collections import Counter
from datetime import date, datetime, time, timedelta

from werkzeug.security import generate_password_hash

from app.filters import from_answers
from src import db, engine, home
from src.db import DB_PATH
from src.engine import book_categories
from src.profile import FAMILY_OF, build_profile, recommend, recompute_learned
from src.questions import NEUTRAL

SEED = 2026
PASSWORD = "demo1234"
EMAIL_DOMAIN = "exemple.fr"
POOL = 40              # recommandations dans lesquelles on puise les lectures
PILE = (2, 3)          # livres à lire par persona
MAX_READING = 2        # livres en cours par persona
MOMENT_BOOKS = 3       # livres « du moment », commencés cette semaine…
MOMENT_READERS = (4, 6)  # … par 4 à 6 personas chacun
SHARED = {"suspense": 4, "psychologie": 3}  # livres terminés en commun par famille
FINISHED_START = (5, 90)  # début d'un livre terminé : entre J-90 et J-5
FINISHED_SPAN = (5, 30)   # fin : 5 à 30 jours après le début, jamais dans le futur
READING_START = (7, 40)   # début d'un livre en cours (hors livres du moment)

N = NEUTRAL
# pseudo, q1, q2, q3, q5, q6, q8, q9, q10, nombre de lectures ; q4 et q7 neutres.
PERSONAS = [
    # Suspense
    ("aline", ["thriller_polar"], ["crime", "secret"], ["tendue", "sombre"], "moyen", "recents",
     ["aucun"], "themes", "mixte", 9),
    ("karim", ["thriller_polar", "litterature"], ["crime"], ["tendue"], "long", "toutes",
     ["fantasy"], "temps", "proche", 7),
    ("sophie", ["thriller_polar"], ["secret", "famille"], ["sombre"], "court", "nouveautes",
     ["romance"], "varier", "surprise", 6),
    ("mehdi", ["thriller_polar", "science_fiction"], ["crime", "survie"], ["tendue"], N,
     "recents", ["aucun"], "nouveau", "mixte", 10),
    ("lucie", ["thriller_polar"], ["crime"], [N], "moyen", N, ["fantasy"], "profil",
     "sans_pref", 4),
    ("yann", ["thriller_polar", "histoire_aventure"], ["memoire", "crime"], ["sombre"], "long",
     "classiques", ["aucun"], "themes", "proche", 8),
    # Psychologie
    ("nour", ["litterature", "romance"], ["famille", "amour"], ["intimiste"], "moyen", "recents",
     ["thriller_polar"], "themes", "mixte", 8),
    ("clement", ["litterature"], ["famille", "secret"], ["intimiste", "sombre"], "court",
     "toutes", ["aucun"], "varier", "surprise", 6),
    ("ines", ["romance"], ["amour"], ["legere"], "moyen", "nouveautes", ["fantasy"], "temps",
     "proche", 9),
    ("marc", ["litterature", "biographies"], ["memoire", "famille"], ["intimiste"], "long",
     "classiques", ["romance"], "themes", "mixte", 5),
    # Imaginaire
    ("theo", ["science_fiction"], ["science", "survie"], ["epique"], "long", "recents",
     ["romance"], "nouveau", "surprise", 7),
    ("jade", ["fantasy"], ["secret"], ["epique", "poetique"], "long", "toutes", ["aucun"],
     "themes", "mixte", 8),
    ("hugo", ["science_fiction", "fantasy"], ["societe", "survie"], ["sombre"], "moyen", "toutes",
     ["aucun"], "varier", "surprise", 6),
    ("emma", ["fantasy", "romance"], ["amour", "secret"], ["poetique"], "moyen", "nouveautes",
     ["thriller_polar"], "profil", "mixte", 5),
    # Histoire
    ("pierre", ["histoire_aventure"], ["memoire", "societe"], ["epique"], "long", "classiques",
     ["fantasy"], "themes", "proche", 7),
    ("salome", ["histoire_aventure", "litterature"], ["memoire", "famille"], ["intimiste"],
     "moyen", "toutes", ["aucun"], "nouveau", "mixte", 6),
    ("antoine", ["histoire_aventure", "biographies"], ["memoire", "survie"], ["epique"], N,
     "recents", ["romance", "fantasy"], "temps", "proche", 5),
    # Réel et idées
    ("fatou", ["essais", "biographies"], ["societe", "science"], [N], "court", "nouveautes",
     ["aucun"], "themes", "mixte", 6),
    ("louis", ["essais"], ["societe"], [N], "moyen", "recents", ["romance"], "nouveau",
     "surprise", 4),
    # Éclectique
    ("camille", [N], [N], [N], N, N, [N], N, N, 3),
]

COMMENTS = {
    "high": [
        "Impossible de le lâcher, je l'ai fini en quelques soirées.",
        "Une très belle découverte, je le recommande sans hésiter.",
        "Des personnages attachants et une fin vraiment réussie.",
        "Exactement le genre de livre que j'aime.",
        "Je vais vite chercher les autres livres de l'auteur.",
        "Il m'a accompagné longtemps après la dernière page.",
    ],
    "mid": [
        "Agréable, mais un peu long au milieu.",
        "Une bonne idée de départ, une fin moins convaincante.",
        "Sympathique, sans plus.",
        "Bien écrit, mais l'histoire ne m'a pas vraiment emporté.",
    ],
    "low": [
        "Je n'ai pas réussi à m'attacher aux personnages.",
        "Trop lent pour moi, j'ai failli abandonner.",
        "Pas du tout mon style, finalement.",
        "L'intrigue m'a laissé de marbre.",
    ],
}


class SeedError(Exception):
    """Création impossible (comptes démo déjà présents, pseudo pris…)."""


def answers_of(row):
    """Ligne de PERSONAS -> réponses au questionnaire, au format enregistré par l'interface."""
    pseudo, q1, q2, q3, q5, q6, q8, q9, q10, _ = row
    return {"q1": q1, "q2": q2, "q3": q3, "q4": [N], "q5": q5, "q6": q6, "q7": [N],
            "q8": q8, "q9": q9, "q10": q10}


def excludes(profile, book):
    return bool(book_categories(book) & set(profile["exclusions"]))


# --- Plan des lectures --------------------------------------------------------------------

def popular_in(personas, skip=(), strict=True):
    """Livres des recommandations de ces personas : les plus fréquents d'abord, puis les
    mieux classés. strict : sans les livres qu'un de ces personas exclut."""
    stats = {}
    for p in personas:
        for rank, book in enumerate(p["pool"]):
            count, ranks, _ = stats.get(book["id"], (0, 0, book))
            stats[book["id"]] = (count + 1, ranks + rank, book)
    ranked = sorted(stats.values(), key=lambda s: (-s[0], s[1], s[2]["id"]))
    return [b for _, _, b in ranked if b["id"] not in skip
            and not (strict and any(excludes(p["profile"], b) for p in personas))]


def spare(p):
    """Places libres pour un livre en cours imposé (la pile garde au moins 2 livres)."""
    if len(p["moment"]) >= MAX_READING:
        return 0
    return p["total"] - PILE[0] - len(p["shared"]) - len(p["moment"])


def plan_readings(personas, books, rng):
    """Remplit p["finished"], p["reading"] (livres), p["moment"], p["pile"] de chaque persona."""
    for p in personas:
        p.update(shared=[], moment=[], used=set(), pool_ids={b["id"] for b in p["pool"]})

    # (b) Livres terminés en commun dans une famille ; un persona avec peu de lectures
    # n'en prend que ce que sa pile lui laisse.
    reserved = set()
    for family, k in SHARED.items():
        members = [p for p in personas if p["family"] == family]
        common = popular_in(members, reserved)[:k]
        reserved |= {b["id"] for b in common}
        for p in members:
            p["shared"] = rng.sample(common, min(k, p["total"] - PILE[0]))
            p["used"] |= {b["id"] for b in p["shared"]}

    # (a) Livres du moment : les plus recommandés, un par famille, commencés cette semaine.
    families = set()
    for book in popular_in(personas, reserved, strict=False):
        if len(families) == MOMENT_BOOKS:
            break
        family = FAMILY_OF[book["main_category"]]
        if family in families:
            continue
        candidates = [p for p in personas if spare(p) > 0 and not excludes(p["profile"], book)
                      and book["id"] not in p["used"]]
        rng.shuffle(candidates)
        # D'abord ceux qui n'ont pas encore de livre du moment, puis ceux à qui il est recommandé.
        candidates.sort(key=lambda p: (len(p["moment"]), book["id"] not in p["pool_ids"]))
        k = rng.randint(*MOMENT_READERS)
        if len(candidates) < k:
            continue
        for p in candidates[:k]:
            p["moment"].append(book)
            p["used"].add(book["id"])
        families.add(family)
        reserved.add(book["id"])

    for p in personas:
        fixed = len(p["shared"]) + len(p["moment"])
        pile = rng.randint(*PILE) if p["total"] - PILE[1] >= fixed else PILE[0]
        reading = min(rng.randint(len(p["moment"]), MAX_READING),
                      p["total"] - pile - len(p["shared"]))
        finished = p["total"] - pile - reading

        # Reste à choisir : les meilleures recommandations, plus 1 ou 2 livres hors profil.
        free = p["total"] - fixed
        outside = [b for b in books if b["id"] not in p["pool_ids"] and b["id"] not in reserved
                   and not excludes(p["profile"], b)]
        extra = rng.sample(outside, min(1 if p["total"] < 7 else 2, free))
        extra += [b for b in p["pool"] if b["id"] not in reserved | p["used"]][:free - len(extra)]
        rng.shuffle(extra)
        cut = finished - len(p["shared"])
        p["finished"] = p["shared"] + extra[:cut]
        p["reading"] = extra[cut:cut + reading - len(p["moment"])]
        p["pile"] = extra[cut + reading - len(p["moment"]):]


def rating_deck(n, rng):
    """n notes : 20 % sans note ; parmi les notées, 60 % à 4-5, 25 % à 3, 15 % à 1-2."""
    rated = n - round(0.2 * n)
    high, mid = round(0.6 * rated), round(0.25 * rated)
    deck = ([None] * (n - rated) + [rng.choice((4, 5)) for _ in range(high)] + [3] * mid
            + [rng.choice((1, 2)) for _ in range(rated - high - mid)])
    rng.shuffle(deck)
    return deck


def comment_for(rating, rng):
    kind = "high" if rating >= 4 else "mid" if rating == 3 else "low"
    return rng.choice(COMMENTS[kind])


def stamp(day, rng):
    """Date -> horodatage ISO à une heure plausible."""
    return datetime.combine(day, time(rng.randint(8, 22), rng.randint(0, 59))).isoformat()


def days_ago(today, n):
    return today - timedelta(days=n)


# --- Base -----------------------------------------------------------------------------------

def delete_demo(conn):
    demo = "SELECT id FROM users WHERE is_demo = 1"
    conn.execute(f"DELETE FROM readings WHERE user_id IN ({demo})")
    conn.execute(f"DELETE FROM survey_answers WHERE user_id IN ({demo})")
    conn.execute("DELETE FROM users WHERE is_demo = 1")


def write_persona(conn, p, today, rng):
    """Compte, réponses et lectures d'un persona ; renvoie son id."""
    first_day = min([r["start"] for r in p["rows"] if r["start"]] + [today])
    created = stamp(days_ago(first_day, rng.randint(3, 15)), rng)
    user_id = conn.execute(
        "INSERT INTO users (username, email, password_hash, created_at, is_demo)"
        " VALUES (?, ?, ?, ?, 1)",
        (p["pseudo"], f"{p['pseudo']}@{EMAIL_DOMAIN}", generate_password_hash(PASSWORD),
         created)).lastrowid
    for qid, answer in p["answers"].items():
        conn.execute("INSERT INTO survey_answers (user_id, question_id, answer, answered_at)"
                     " VALUES (?, ?, ?, ?)",
                     (user_id, qid, json.dumps(answer, ensure_ascii=False), created))
    for r in p["rows"]:
        last = r["end"] or r["start"] or r["added"]
        conn.execute(
            "INSERT INTO readings (user_id, book_id, rank, start_date, end_date, rating, comment,"
            " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, r["book"]["id"], r["rank"], r["start"] and r["start"].isoformat(),
             r["end"] and r["end"].isoformat(), r["rating"], r["comment"],
             stamp(r["added"], rng), stamp(last, rng)))
    return user_id


def date_rows(p, today, rng):
    """Lectures datées : p["rows"] = [{book, rank, start, end, added, rating, comment}]."""
    rows = []
    for book in p["finished"]:
        start = days_ago(today, rng.randint(*FINISHED_START))
        span = rng.randint(FINISHED_SPAN[0], min(FINISHED_SPAN[1], (today - start).days))
        rows.append({"book": book, "rank": None, "start": start,
                     "end": start + timedelta(days=span)})
    for book in p["moment"]:
        rows.append({"book": book, "rank": None, "end": None,
                     "start": days_ago(today, rng.randint(0, home.WEEK_DAYS - 1))})
    for book in p["reading"]:
        rows.append({"book": book, "rank": None, "end": None,
                     "start": days_ago(today, rng.randint(*READING_START))})
    for rank, book in enumerate(p["pile"], 1):
        rows.append({"book": book, "rank": rank, "start": None, "end": None,
                     "added": days_ago(today, rng.randint(1, 60))})
    for r in rows:
        r.setdefault("added", r["start"])
        r.update(rating=None, comment=None)
    p["rows"] = rows


# --- Script ---------------------------------------------------------------------------------

def run(db_path=DB_PATH, reset=False, today=None, out=print):
    """Crée les comptes démo ; renvoie le rapport (voir report)."""
    today = today or date.today()
    rng = random.Random(SEED)
    db.init_db(db_path)
    pseudos = [row[0] for row in PERSONAS]
    with db.get_connection(db_path) as conn:
        if conn.execute("SELECT 1 FROM users WHERE is_demo = 1").fetchone() and not reset:
            raise SeedError("Des comptes de démonstration existent déjà : relance avec --reset.")
        if reset:
            delete_demo(conn)
        marks = ",".join("?" * len(pseudos))
        taken = conn.execute(
            f"SELECT username FROM users WHERE lower(username) IN ({marks})"
            f" OR lower(email) IN ({marks})",
            pseudos + [f"{s}@{EMAIL_DOMAIN}" for s in pseudos]).fetchall()
        if taken:
            raise SeedError("Pseudo ou e-mail déjà pris par un vrai compte : "
                            + ", ".join(row["username"] for row in taken))

    index = engine.get_index(db_path)
    personas = []
    for row in PERSONAS:
        answers = answers_of(row)
        profile = build_profile(answers)
        pool = [r["book"] for r in recommend(profile, POOL, db_path=db_path)]
        personas.append({"pseudo": row[0], "total": row[-1], "answers": answers,
                         "profile": profile, "family": profile["family"], "pool": pool})
    plan_readings(personas, index.books, rng)

    for p in personas:
        date_rows(p, today, rng)
    finished = [r for p in personas for r in p["rows"] if r["end"]]
    for r, rating in zip(finished, rating_deck(len(finished), rng)):
        r["rating"] = rating
    rated = [r for r in finished if r["rating"]]
    for r in rng.sample(rated, round(len(rated) / 2)):
        r["comment"] = comment_for(r["rating"], rng)

    with db.get_connection(db_path) as conn:
        for p in personas:
            p["id"] = write_persona(conn, p, today, rng)
    for p in personas:
        db.save_profile(p["id"], p["profile"], db_path)
        notes = [(r["book"], r["rating"]) for r in p["rows"] if r["rating"]]
        db.save_profile(p["id"], recompute_learned(p["profile"], notes), db_path)
        db.save_filters(p["id"], from_answers(p["answers"]), db_path)

    result = report(db_path, today)
    print_report(result, out)
    return result


def report(db_path=DB_PATH, today=None):
    """Comptes, lectures par statut, populaires de la semaine, contributeurs par famille,
    et vérification des contraintes de démo (lectures de la semaine, livres en commun)."""
    today = today or date.today()
    week_start = days_ago(today, home.WEEK_DAYS - 1).isoformat()
    with db.get_connection(db_path) as conn:
        users = conn.execute("SELECT id, username, profile_family FROM users"
                             " WHERE is_demo = 1").fetchall()
        readings = conn.execute(
            "SELECT r.* FROM readings r JOIN users u ON u.id = r.user_id"
            " WHERE u.is_demo = 1").fetchall()
        contributors = conn.execute(
            "SELECT u.profile_family AS family, COUNT(DISTINCT r.user_id) AS n"
            " FROM readings r JOIN users u ON u.id = r.user_id WHERE r.end_date IS NOT NULL"
            " GROUP BY u.profile_family ORDER BY n DESC, family").fetchall()
    family_of = {u["id"]: u["profile_family"] for u in users}
    shared = {}
    for family in SHARED:
        counts = Counter(r["book_id"] for r in readings
                         if r["end_date"] and family_of[r["user_id"]] == family)
        shared[family] = {"members": sum(f == family for f in family_of.values()),
                          "books": sorted((n for n in counts.values() if n >= 2), reverse=True)}
    week = [r for r in readings
            if r["start_date"] and week_start <= r["start_date"] <= today.isoformat()]
    populaires = home.populaires_semaine(today, db_path)
    return {
        "accounts": len(users),
        "statuses": Counter(db.reading_status(r) for r in readings),
        "week_readers": len({r["user_id"] for r in week}),
        "popular": [(e["book"]["title"], e["readers"]) for e in populaires["books"]],
        "contributors": [(row["family"], row["n"]) for row in contributors],
        "shared": shared,
    }


def print_report(result, out=print):
    out(f"Comptes de démonstration créés : {result['accounts']}")
    out("Lectures : " + ", ".join(f"{result['statuses'][s]} {s}"
                                  for s in (db.TO_READ, db.READING, db.FINISHED)))
    out(f"Lecteurs ayant commencé un livre ces 7 derniers jours : {result['week_readers']}")
    out("Populaires cette semaine :")
    for title, readers in result["popular"]:
        if readers > 1:
            out(f"  {readers} lecteurs · {title}")
    out("Lecteurs contributeurs (au moins un livre terminé), par famille :")
    for family, n in result["contributors"]:
        out(f"  {family} : {n}")
    for family, data in result["shared"].items():
        out(f"Livres terminés en commun ({family}, {data['members']} lecteurs) : "
            + ", ".join(f"{n} lecteurs" for n in data["books"]))


def main(argv):
    if argv not in ([], ["--reset"]):
        print("Usage : python -m src.seed [--reset]")
        return 1
    try:
        run(reset=argv == ["--reset"])
    except SeedError as error:
        print(error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
