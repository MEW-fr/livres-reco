"""Construction et gestion du profil lecteur.

- build_profile : réponses au questionnaire -> profil (genres, thèmes, ambiances, filtres,
  bonus, confiance, libellé).
- score_book : score S d'un livre selon le barème : S = 0,84 × P + R + D.
- novelty_for : indice de nouveauté N (0-100) de chaque livre.
- recommend : les n meilleurs livres pour un profil, avec explication.
- update_after_rating : le profil évolue avec les notes (±0,05, plafond ±0,30).

Usage : python -m src.profile --demo
"""

import copy
import sys
import time
from datetime import date

from src import engine
from src.db import DB_PATH
from src.engine import book_categories, join_fr
from src.questions import AMBIANCE_LABELS, CATEGORY_LABELS, NEUTRAL, QUESTIONS_BY_ID, THEME_LABELS

P_WEIGHT = 0.84        # S = 0,84 × P + R + D
BONUS_MAX = 8          # R et D valent au plus 8 points
SCORED = ("q1", "q2", "q3", "q5", "q6")  # dimensions de P (q4 non calculée)
TOTAL_WEIGHT = 84      # dénominateur de la confiance : q1..q6 (q4 incluse)

DISCOVERY = {"proche": 0.0, "mixte": 0.5, "surprise": 1.0, "sans_pref": 0.5}

LENGTHS = ("court", "moyen", "long")  # < 250, 250-450, > 450 pages
# (âge maximal pour 100 %, âge maximal pour 50 %) ; au-delà : 0 %
PERIODS = {"nouveautes": (3, 10), "recents": (10, 25)}
CLASSIC_AGE = 25

RATING_STEP = 0.05
RATING_CAP = 0.30
NOVELTY_MENTION = 2.0  # points apportés par N au-delà desquels l'explication le mentionne

# --- Libellés ---------------------------------------------------------------------------

def entry(label, description, tags):
    return {"label": label, "description": description, "tags": tags}


PAIR_LABELS = [
    (("thriller", "policier"), entry(
        "Suspense & tension",
        "Tu aimes les intrigues qui te tiennent en haleine jusqu'à la dernière page.",
        ["Suspense", "Enquêtes", "Rebondissements", "Tension"])),
    (("science-fiction", "dystopie"), entry(
        "Futurs possibles",
        "Tu aimes imaginer demain et questionner le monde à travers d'autres futurs.",
        ["Anticipation", "Sociétés", "Technologies", "Réflexion"])),
    (("fantastique", "horreur"), entry(
        "Mondes de l'ombre",
        "Tu aimes frissonner et basculer dans des univers où l'étrange s'invite.",
        ["Étrange", "Frissons", "Créatures", "Mystère"])),
    (("romance", "littérature générale"), entry(
        "Émotions & liens",
        "Tu aimes les histoires de cœur et les personnages qui te touchent.",
        ["Émotions", "Relations", "Personnages", "Sensibilité"])),
    (("biographie", "essai"), entry(
        "Esprits curieux",
        "Tu aimes comprendre le monde et découvrir des vies et des idées réelles.",
        ["Idées", "Vies réelles", "Savoir", "Réflexion"])),
    (("roman historique", "aventure"), entry(
        "Grandes épopées",
        "Tu aimes les grands récits qui t'emmènent loin, dans le temps ou l'espace.",
        ["Épopées", "Histoire", "Voyages", "Héros"])),
]

GENRE_LABELS = {
    "littérature générale": entry(
        "Âme littéraire", "Tu aimes les belles plumes et les histoires qui font réfléchir.",
        ["Style", "Personnages", "Société", "Émotions"]),
    "thriller": entry(
        "Adrénaline", "Tu aimes quand le rythme s'emballe et que tout peut basculer.",
        ["Suspense", "Rythme", "Rebondissements", "Tension"]),
    "policier": entry(
        "Fin limier", "Tu aimes mener l'enquête et démasquer le coupable avant la fin.",
        ["Enquêtes", "Indices", "Crimes", "Déduction"]),
    "science-fiction": entry(
        "Explorateur·rice du futur", "Tu aimes les sciences, l'espace et les mondes de demain.",
        ["Espace", "Sciences", "Futur", "Technologies"]),
    "dystopie": entry(
        "Veilleur·se lucide", "Tu aimes les sociétés imaginaires qui en disent long sur la nôtre.",
        ["Sociétés", "Résistance", "Anticipation", "Réflexion"]),
    "fantastique": entry(
        "Rêveur·se d'ailleurs", "Tu aimes la magie et les mondes qui n'existent nulle part ailleurs.",
        ["Magie", "Mondes imaginaires", "Quêtes", "Merveilleux"]),
    "horreur": entry(
        "Amateur·rice de frissons", "Tu aimes avoir peur, bien installé·e dans ton fauteuil.",
        ["Frissons", "Peur", "Surnaturel", "Ténèbres"]),
    "roman historique": entry(
        "Voyageur·se du temps", "Tu aimes revivre le passé à travers des destins marquants.",
        ["Histoire", "Époques", "Destins", "Mémoire"]),
    "romance": entry(
        "Cœur tendre", "Tu aimes les histoires d'amour qui font battre le cœur.",
        ["Amour", "Émotions", "Relations", "Feel good"]),
    "aventure": entry(
        "Esprit d'aventure", "Tu aimes partir à l'aventure et vivre des péripéties.",
        ["Voyages", "Péripéties", "Exploration", "Héros"]),
    "biographie": entry(
        "Passeur·se de vies", "Tu aimes les vraies histoires et les parcours inspirants.",
        ["Vies réelles", "Témoignages", "Parcours", "Inspiration"]),
    "essai": entry(
        "Esprit critique", "Tu aimes les idées, les débats et apprendre en lisant.",
        ["Idées", "Société", "Savoir", "Débats"]),
}

AMBIANCE_PROFILE_LABELS = {
    "sombre": entry(
        "Âme nocturne", "Tu aimes les récits sombres qui explorent la part d'ombre.",
        ["Noirceur", "Intensité", "Mystère", "Ombres"]),
    "tendue": entry(
        "Cœur battant", "Tu aimes les lectures qui te gardent sous tension.",
        ["Tension", "Rythme", "Suspense", "Adrénaline"]),
    "legere": entry(
        "Bonne humeur", "Tu aimes les lectures légères qui donnent le sourire.",
        ["Humour", "Légèreté", "Feel good", "Détente"]),
    "intimiste": entry(
        "Lecteur·rice sensible", "Tu aimes les récits intimes, au plus près des personnages.",
        ["Intime", "Émotions", "Introspection", "Sensibilité"]),
    "epique": entry(
        "Souffle épique", "Tu aimes les grandes fresques et les destins héroïques.",
        ["Fresques", "Héros", "Grandeur", "Aventure"]),
    "poetique": entry(
        "Âme poétique", "Tu aimes les mots qui chantent et les récits qui font rêver.",
        ["Poésie", "Rêverie", "Style", "Onirisme"]),
}

EXPLORER_LABEL = entry(
    "Lecteur·rice en exploration",
    "Tu es ouvert·e à tout : on va découvrir ensemble ce que tu aimes.",
    ["Découverte", "Curiosité", "Ouverture", "Surprises"])


def choose_label(genres, ambiances):
    """Paire si ses deux genres sont choisis, sinon premier genre, sinon ambiance
    dominante, sinon lecteur·rice en exploration."""
    for pair, label in PAIR_LABELS:
        if all(g in genres for g in pair):
            return label
    if genres:
        return GENRE_LABELS[next(iter(genres))]
    if ambiances:
        return AMBIANCE_PROFILE_LABELS[max(ambiances, key=ambiances.get)]
    return EXPLORER_LABEL


# --- Construction du profil --------------------------------------------------------------

def as_list(answer):
    """Réponse -> liste de codes, sans le code neutre."""
    if answer is None:
        return []
    codes = [answer] if isinstance(answer, str) else list(answer)
    return [c for c in codes if c != NEUTRAL]


def as_code(answer):
    """Réponse unique -> code, ou None si neutre / absente."""
    codes = as_list(answer)
    return codes[0] if codes else None


def build_profile(answers):
    """answers = {qid: liste de codes ou code} -> profil JSON-sérialisable."""
    genres = {c: 1.0 for c in as_list(answers.get("q1")) if c in CATEGORY_LABELS}
    themes = {c: 1.0 for c in as_list(answers.get("q2")) if c in THEME_LABELS}
    ambiances = {c: 1.0 for c in as_list(answers.get("q3")) if c in AMBIANCE_LABELS}
    length = as_code(answers.get("q5"))
    period = as_code(answers.get("q6"))
    discovery = as_code(answers.get("q10"))

    answered = {
        "q1": bool(genres), "q2": bool(themes), "q3": bool(ambiances),
        "q5": length in LENGTHS, "q6": period in (*PERIODS, "classiques"),
    }
    confidence = sum(QUESTIONS_BY_ID[q]["weight"] for q in SCORED if answered[q]) / TOTAL_WEIGHT
    label = choose_label(genres, ambiances)

    return {
        "genres": genres,
        "themes": themes,
        "ambiances": ambiances,
        "formats": as_list(answers.get("q4")),
        "length": length,
        "period": period,
        "languages": as_list(answers.get("q7")),
        "exclusions": [c for c in as_list(answers.get("q8")) if c in CATEGORY_LABELS],
        "priority": as_code(answers.get("q9")),
        "discovery": DISCOVERY.get(discovery, 0.0),
        "answered": answered,  # dimension renseignée au questionnaire (sinon exclue de P)
        "confidence": round(confidence, 4),
        "initial": copy.deepcopy({"genres": genres, "themes": themes, "ambiances": ambiances}),
        "label": label["label"],
        "label_description": label["description"],
        "label_tags": label["tags"],
    }


# --- Score d'un livre ---------------------------------------------------------------------

def length_class(pages):
    if pages is None:
        return None
    if pages < 250:
        return "court"
    return "moyen" if pages <= 450 else "long"


def match_genres(profile, book):
    """q1 : part des catégories du livre couvertes, pondérée par la préférence."""
    if not profile["answered"]["q1"]:
        return None
    cats = book_categories(book)
    common = [c for c in cats if profile["genres"].get(c, 0) > 0]
    value = 100 * sum(profile["genres"].get(c, 0) for c in cats) / len(cats)
    return {"match": min(100.0, value), "common": common}


def match_themes(profile, book):
    """q2 : thèmes communs ÷ thèmes du livre ; ignoré si le livre n'a pas de thème."""
    if not profile["answered"]["q2"] or not book["themes"]:
        return None
    common = [t for t in book["themes"] if profile["themes"].get(t, 0) > 0]
    value = 100 * sum(profile["themes"].get(t, 0) for t in book["themes"]) / len(book["themes"])
    return {"match": min(100.0, value), "common": common}


def match_ambiance(profile, book):
    """q3 : 100 si l'ambiance du livre est choisie, 0 sinon ; ignoré si inconnue."""
    if not profile["answered"]["q3"] or not book["ambiance"]:
        return None
    pref = profile["ambiances"].get(book["ambiance"], 0)
    return {"match": min(100.0, 100 * pref), "common": [book["ambiance"]] if pref > 0 else []}


def match_length(profile, book):
    """q5 : 100 dans la plage visée, 50 dans une plage voisine, 0 à l'opposé."""
    book_class = length_class(book["page_count"])
    if profile["length"] not in LENGTHS or book_class is None:
        return None
    gap = abs(LENGTHS.index(profile["length"]) - LENGTHS.index(book_class))
    return {"match": (100.0, 50.0, 0.0)[gap]}


def match_period(profile, book, year):
    """q6 : selon l'âge du livre (année courante − année de publication)."""
    period = profile["period"]
    if book["published_year"] is None or period not in (*PERIODS, "classiques"):
        return None
    age = year - book["published_year"]
    if period == "classiques":
        return {"match": 100.0 if age > CLASSIC_AGE else 50.0}
    full, half = PERIODS[period]
    return {"match": 100.0 if age <= full else 50.0 if age <= half else 0.0}


def score_book(profile, book, N, group_pop=None, year=None):
    """(S, détail) avec S = 0,84 × P + R + D.

    P : moyenne pondérée des dimensions renseignées et calculables pour ce livre
    (None si aucune). R : bonus de priorité (q9). D : bonus de découverte (q10).
    """
    year = year or date.today().year
    detail = {}
    for qid, result in (("q1", match_genres(profile, book)), ("q2", match_themes(profile, book)),
                        ("q3", match_ambiance(profile, book)), ("q5", match_length(profile, book)),
                        ("q6", match_period(profile, book, year))):
        if result is not None:
            detail[qid] = result

    weights = {q: QUESTIONS_BY_ID[q]["weight"] for q in detail}
    P = (sum(detail[q]["match"] * w for q, w in weights.items()) / sum(weights.values())
         if detail else None)

    priority = profile["priority"]
    if priority == "themes":
        r_base = detail["q2"]["match"] if "q2" in detail else 0.0
    elif priority in ("nouveau", "varier"):
        r_base = N
    elif priority == "profil":
        r_base = group_pop or 0.0
    elif priority == "temps":
        r_base = detail["q5"]["match"] if "q5" in detail else 0.0
    else:
        r_base = 0.0
    R = r_base * BONUS_MAX / 100
    D = profile["discovery"] * N * BONUS_MAX / 100

    S = P_WEIGHT * (P or 0.0) + R + D
    detail.update(P=P, R=R, D=D, N=N)
    return S, detail


# --- Nouveauté ------------------------------------------------------------------------------

def novelty_for(profile, books, read_ids=(), db_path=DB_PATH):
    """{id: N}. Avec des lectures : 100 × (1 − cosinus avec leur centroïde TF-IDF).
    Sans lecture : 100 si ni catégorie ni thème commun avec le profil, 50 si l'un des
    deux, 0 si les deux ; 50 partout si q1 et q2 sont neutres."""
    ids = [b["id"] for b in books]
    if read_ids:
        values = engine.novelty(engine.centroid(list(read_ids), db_path=db_path), ids,
                                db_path=db_path)
        if values is not None:
            return {i: values.get(i, 50.0) for i in ids}

    answered = profile["answered"]
    genres = {g for g, v in profile["genres"].items() if v > 0} if answered["q1"] else set()
    themes = {t for t, v in profile["themes"].items() if v > 0} if answered["q2"] else set()
    if not genres and not themes:
        return {i: 50.0 for i in ids}
    result = {}
    for book in books:
        shared = bool(book_categories(book) & genres) + bool(set(book["themes"]) & themes)
        result[book["id"]] = (100.0, 50.0, 0.0)[shared]
    return result


# --- Recommandation -------------------------------------------------------------------------

def explain(profile, book, detail):
    """Phrase « Recommandé pour … » : genres, thèmes, ambiance communs, puis découverte."""
    parts = []
    genres = [CATEGORY_LABELS[c] for c in detail.get("q1", {}).get("common", [])]
    if genres:
        parts.append(("le genre " if len(genres) == 1 else "les genres ") + join_fr(genres))
    themes = [THEME_LABELS[t] for t in detail.get("q2", {}).get("common", [])]
    if themes:
        parts.append(("le thème " if len(themes) == 1 else "les thèmes ") + join_fr(themes))
    ambiance = detail.get("q3", {}).get("common", [])
    if ambiance:
        parts.append(f"son ambiance {AMBIANCE_LABELS[ambiance[0]]}")

    n_points = detail["D"] + (detail["R"] if profile["priority"] in ("nouveau", "varier") else 0)
    discovery = ""
    if n_points >= NOVELTY_MENTION:
        main = book["main_category"]
        if profile["genres"].get(main, 0) > 0:
            discovery = "te faire découvrir un univers un peu différent"
        else:
            discovery = f"te faire découvrir le genre {CATEGORY_LABELS[main]}"

    if parts and discovery:
        return f"Recommandé pour {join_fr(parts)}, et pour {discovery}."
    if parts:
        return f"Recommandé pour {join_fr(parts)}."
    if discovery:
        return f"Recommandé pour {discovery}."
    return "Recommandé pour élargir tes horizons de lecture."


def recommend(profile, n=5, filters=None, read_ids=(), group_pop=None, db_path=DB_PATH):
    """Les n livres de meilleur score S : [{book, score, P, R, D, N, detail, explanation}].

    Écarte les genres à éviter (q8, prioritaires sur q1) et les livres déjà lus.
    group_pop : {id livre: popularité 0-100 chez les lecteurs du même profil} ou None.
    """
    index = engine.get_index(db_path)
    excluded = set(profile["exclusions"])
    read = set(read_ids)
    filters = filters or engine.Filters()
    candidates = [b for b in index.books
                  if not book_categories(b) & excluded and b["id"] not in read
                  and filters.accepts(b)]

    novelties = novelty_for(profile, candidates, read_ids, db_path=db_path)
    year = date.today().year
    scored = []
    for book in candidates:
        pop = (group_pop or {}).get(book["id"])
        S, detail = score_book(profile, book, novelties[book["id"]], pop, year)
        n_dims = sum(q in detail for q in SCORED)
        scored.append((round(S, 6), n_dims, engine.rating_key(book), -book["id"], book, detail))
    # Départage : S, nombre de dimensions calculées, note moyenne (≥ 5 avis), id croissant.
    scored.sort(key=lambda item: item[:4], reverse=True)

    return [{"book": book, "score": S, "P": d["P"], "R": d["R"], "D": d["D"], "N": d["N"],
             "detail": d, "explanation": explain(profile, book, d)}
            for S, _, _, _, book, d in scored[:n]]


# --- Évolution après une note ---------------------------------------------------------------

def adjust(prefs, initial, key, delta):
    """Ajoute delta à prefs[key], borné à [initial − 0,30 ; initial + 0,30] et ≥ 0."""
    if delta < 0 and key not in prefs:
        return
    start = initial.get(key, 0.0)
    value = prefs.get(key, 0.0) + delta
    value = min(start + RATING_CAP, max(start - RATING_CAP, 0.0, value))
    prefs[key] = round(value, 4)


def update_after_rating(profile, book, rating):
    """Note 4-5 : +0,05 sur les genres, thèmes et ambiance du livre ; 1-2 : −0,05 ; 3 : rien.

    Les valeurs apprises sont toujours conservées, mais une dimension neutre au
    questionnaire reste exclue de P (profile["answered"]).
    """
    if rating >= 4:
        delta = RATING_STEP
    elif rating <= 2:
        delta = -RATING_STEP
    else:
        return profile
    initial = profile["initial"]
    for key in book_categories(book):
        adjust(profile["genres"], initial["genres"], key, delta)
    for key in book["themes"]:
        adjust(profile["themes"], initial["themes"], key, delta)
    if book["ambiance"]:
        adjust(profile["ambiances"], initial["ambiances"], book["ambiance"], delta)
    return profile


# --- CLI --------------------------------------------------------------------------------------

DEMO_PROFILES = [
    ("Profil 1", {
        "q1": ["thriller", "policier"], "q2": ["crime", "secret"], "q3": ["tendue"],
        "q4": [NEUTRAL], "q5": "moyen", "q6": "recents", "q7": [NEUTRAL], "q8": ["horreur"],
        "q9": "themes", "q10": "mixte",
    }),
    ("Profil 2", {
        "q1": [NEUTRAL], "q2": ["famille", "deuil"], "q3": ["intimiste"], "q4": [NEUTRAL],
        "q5": NEUTRAL, "q6": NEUTRAL, "q7": [NEUTRAL], "q8": [NEUTRAL], "q9": NEUTRAL,
        "q10": NEUTRAL,
    }),
]


def fmt(value):
    return "-" if value is None else f"{value:.1f}"


def demo():
    engine.get_index()  # chargement de l'index hors chronométrage
    for name, answers in DEMO_PROFILES:
        start = time.perf_counter()
        profile = build_profile(answers)
        results = recommend(profile)
        elapsed = (time.perf_counter() - start) * 1000

        print(f"=== {name} ===")
        print(f"Libellé : {profile['label']}")
        print(f"Description : {profile['label_description']}")
        print(f"Tags : {', '.join(profile['label_tags'])}")
        print(f"Confiance : {profile['confidence'] * 100:.1f} %\n")
        for rank, r in enumerate(results, 1):
            b = r["book"]
            print(f"{rank}. {b['title']} — {', '.join(b['authors'])} "
                  f"[{b['main_category']}, {b['published_year']}, {b['page_count']} p., "
                  f"ambiance {b['ambiance'] or '-'}, thèmes {', '.join(b['themes']) or '-'}]")
            print(f"   S {r['score']:.1f} | P {fmt(r['P'])} | R {r['R']:.1f} | D {r['D']:.1f} "
                  f"| N {r['N']:.0f}")
            print(f"   {r['explanation']}")
        print(f"\nTemps (profil + recommandations) : {elapsed:.0f} ms\n")


def main(argv):
    if argv != ["--demo"]:
        print("Usage : python -m src.profile --demo")
        return 1
    demo()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
