"""Questionnaire lecteur : 10 questions, leurs options et leur poids dans le barème.

Chaque réponse est une liste de codes (type "multi") ou un code (type "single").
Le code "neutre" est toujours accepté : il retire la question du calcul, sans malus.
"""

NEUTRAL = "neutre"
NEUTRAL_OPTION = {"code": NEUTRAL, "label": "Je ne sais pas / je ne souhaite pas me prononcer"}

# Les 12 catégories du catalogue (codes = valeurs de books.main_category) et leur libellé à l'écran.
CATEGORY_LABELS = {
    "littérature générale": "Littérature",
    "thriller": "Thriller",
    "policier": "Polar",
    "science-fiction": "Science-fiction",
    "dystopie": "Dystopie",
    "fantastique": "Fantasy & fantastique",
    "horreur": "Horreur",
    "roman historique": "Roman historique",
    "romance": "Romance",
    "aventure": "Aventure",
    "biographie": "Biographies & récits",
    "essai": "Essais & idées",
}

THEME_LABELS = {
    "famille": "famille", "amour": "amour", "amitie": "amitié", "guerre": "guerre",
    "crime": "crime", "voyage": "voyage", "societe": "société", "science": "science",
    "nature": "nature", "memoire": "mémoire", "deuil": "deuil", "secret": "secret",
    "initiation": "initiation", "art": "art",
}

AMBIANCE_LABELS = {
    "sombre": "sombre", "tendue": "tendue", "legere": "légère", "intimiste": "intimiste",
    "epique": "épique", "poetique": "poétique",
}


def options(pairs):
    """[(code, label), ...] -> options de question, option neutre ajoutée à la fin."""
    return [{"code": code, "label": label} for code, label in pairs] + [NEUTRAL_OPTION]


CATEGORY_OPTIONS = list(CATEGORY_LABELS.items())

QUESTIONS = [
    {
        "id": "q1", "type": "multi", "weight": 24,
        "text": "Qu'est-ce que tu aimes lire, spontanément ?",
        "help": "Choisis autant de genres que tu veux.",
        "options": options(CATEGORY_OPTIONS + [("autre", "Autre chose (précise si tu veux)")]),
    },
    {
        "id": "q2", "type": "multi", "weight": 22,
        "text": "Quels sujets te parlent le plus ?",
        "help": "Les thèmes vers lesquels tu reviens souvent.",
        "options": options([
            ("famille", "Famille"), ("amour", "Amour"), ("amitie", "Amitié"),
            ("guerre", "Guerre"), ("crime", "Crime"), ("voyage", "Voyage"),
            ("societe", "Société"), ("science", "Science"), ("nature", "Nature"),
            ("memoire", "Mémoire & passé"), ("deuil", "Deuil"), ("secret", "Secrets"),
            ("initiation", "Passage à l'âge adulte"), ("art", "Art & création"),
        ]),
    },
    {
        "id": "q3", "type": "multi", "weight": 12,
        "text": "Quelle ambiance te fait du bien ?",
        "help": "L'atmosphère que tu recherches dans un livre.",
        "options": options([
            ("sombre", "Sombre"), ("tendue", "Tendue, haletante"), ("legere", "Légère, drôle"),
            ("intimiste", "Intimiste"), ("epique", "Épique"), ("poetique", "Poétique"),
            ("varie", "Ça dépend des jours"),
        ]),
    },
    {
        "id": "q4", "type": "multi", "weight": 12,  # posée et stockée, non calculée (MVP)
        "text": "Comment aimes-tu qu'une histoire soit racontée ?",
        "help": "Le rythme et la forme qui te conviennent.",
        "options": options([
            ("lineaire", "Une intrigue linéaire"), ("rapide", "Un rythme rapide"),
            ("choral", "Plusieurs voix"), ("saga", "Une saga en plusieurs tomes"),
            ("court", "Des chapitres courts"), ("introspectif", "Introspectif"),
            ("sans_pref", "Pas de préférence"),
        ]),
    },
    {
        "id": "q5", "type": "single", "weight": 8,
        "text": "Tu préfères des livres plutôt…",
        "help": "La longueur qui te donne envie d'ouvrir le livre.",
        "options": options([
            ("court", "Courts (moins de 250 pages)"), ("moyen", "Moyens (250 à 450 pages)"),
            ("long", "Longs (plus de 450 pages)"), ("toutes", "Toutes les longueurs"),
        ]),
    },
    {
        "id": "q6", "type": "single", "weight": 6,
        "text": "Côté époque de publication ?",
        "help": "Plutôt nouveautés ou grands classiques ?",
        "options": options([
            ("nouveautes", "Les nouveautés (3 dernières années)"),
            ("recents", "Les livres récents (10 dernières années)"),
            ("classiques", "Les classiques"), ("toutes", "Toutes les périodes"),
        ]),
    },
    {
        "id": "q7", "type": "multi", "weight": 0,  # filtre sans effet : catalogue 100 % français
        "text": "Dans quelle langue lis-tu ?",
        "help": "Pour l'instant, le catalogue est en français.",
        "options": options([
            ("fr", "Français"), ("en", "Anglais"), ("autre", "Une autre langue"),
            ("plusieurs", "Plusieurs langues"),
        ]),
    },
    {
        "id": "q8", "type": "multi", "weight": 0,  # exclusion
        "text": "Y a-t-il des genres que tu préfères éviter ?",
        "help": "On ne te les proposera pas.",
        "options": options(CATEGORY_OPTIONS + [("aucun", "Aucun, je suis ouvert·e à tout")]),
    },
    {
        "id": "q9", "type": "single", "weight": 8,  # bonus R
        "text": "Qu'est-ce qui compte le plus pour toi dans une recommandation ?",
        "help": "On en tiendra compte en bonus.",
        "options": options([
            ("themes", "Qu'elle parle de mes sujets préférés"),
            ("nouveau", "Qu'elle me fasse découvrir du nouveau"),
            ("profil", "Qu'elle plaise aux lecteurs comme moi"),
            ("temps", "Qu'elle colle au temps que j'ai pour lire"),
            ("varier", "Qu'elle me fasse varier les plaisirs"),
        ]),
    },
    {
        "id": "q10", "type": "single", "weight": 8,  # bonus D
        "text": "Tu as envie d'être surpris·e ?",
        "help": "Rester en terrain connu ou sortir de ta zone de confort.",
        "options": options([
            ("proche", "Reste proche de mes goûts"), ("mixte", "Un peu des deux"),
            ("surprise", "Surprends-moi !"), ("sans_pref", "Pas de préférence"),
        ]),
    },
]

QUESTIONS_BY_ID = {q["id"]: q for q in QUESTIONS}
