"""Questionnaire : une question par page, reprise automatique, création du profil."""

from flask import Blueprint, abort, g, redirect, render_template, request, url_for

from app.auth import db_path, login_required, profile_required
from src import db
from src.profile import build_profile
from src.questions import NEUTRAL, QUESTIONS

bp = Blueprint("survey", __name__)

TOTAL = len(QUESTIONS)
EXCLUSIVE = {NEUTRAL, "aucun"}  # options qui désélectionnent toutes les autres
OTHER_TEXT_ID = "q1_autre"      # texte libre de l'option « Autre » (q1), sans effet sur le profil


def first_unanswered(answers):
    """Numéro (1-10) de la première question sans réponse, ou None si tout est répondu."""
    for n, question in enumerate(QUESTIONS, 1):
        if question["id"] not in answers:
            return n
    return None


def clean_answer(question, values):
    """Codes envoyés -> réponse à enregistrer (liste ou code), ou None si invalide."""
    allowed = {o["code"] for o in question["options"]}
    codes = [v for v in dict.fromkeys(values) if v in allowed]
    for code in EXCLUSIVE:
        if code in codes:
            codes = [code]
    if not codes:
        return None
    if question["type"] == "single":
        return codes[0] if len(codes) == 1 else None
    return codes


@bp.route("/questionnaire")
@login_required
def questionnaire():
    """Point d'entrée : reprend à la première question sans réponse."""
    if g.user["profile_vector"]:
        return redirect(url_for("main.accueil"))
    n = first_unanswered(db.load_answers(g.user["id"], db_path())) or TOTAL
    return redirect(url_for("survey.question", n=n))


@bp.route("/questionnaire/<int:n>", methods=["GET", "POST"])
@login_required
def question(n):
    if g.user["profile_vector"]:
        return redirect(url_for("main.accueil"))
    if not 1 <= n <= TOTAL:
        abort(404)
    user_id = g.user["id"]
    answers = db.load_answers(user_id, db_path())
    # Pas de saut en avant : on ne dépasse pas la première question sans réponse.
    resume = first_unanswered(answers)
    if resume is not None and n > resume:
        return redirect(url_for("survey.question", n=resume))

    q = QUESTIONS[n - 1]
    error = None
    if request.method == "POST":
        answer = clean_answer(q, request.form.getlist("answer"))
        if answer is None:
            error = ("Choisis une réponse pour continuer." if q["type"] == "single"
                     else "Choisis au moins une réponse pour continuer.")
        else:
            db.save_answer(user_id, q["id"], answer, db_path())
            if q["id"] == "q1":
                text = request.form.get("autre", "").strip()[:100] if "autre" in answer else ""
                db.save_answer(user_id, OTHER_TEXT_ID, text, db_path())
            if n < TOTAL:
                return redirect(url_for("survey.question", n=n + 1))
            return finish(user_id)

    saved = answers.get(q["id"])
    selected = [saved] if isinstance(saved, str) else (saved or [])
    return render_template("survey/question.html", q=q, n=n, total=TOTAL, selected=selected,
                           other_text=answers.get(OTHER_TEXT_ID, ""), exclusive=EXCLUSIVE,
                           error=error)


def finish(user_id):
    """Question 10 validée : calcul et enregistrement du profil."""
    answers = db.load_answers(user_id, db_path())
    resume = first_unanswered(answers)
    if resume is not None:
        return redirect(url_for("survey.question", n=resume))
    db.save_profile(user_id, build_profile(answers), db_path())
    return redirect(url_for("survey.profil_cree"))


@bp.route("/profil-cree")
@profile_required
def profil_cree():
    return render_template("survey/profil_cree.html",
                           profile=db.load_profile(g.user["id"], db_path()), created=True)


@bp.route("/profil")
@profile_required
def profil():
    return render_template("survey/profil_cree.html",
                           profile=db.load_profile(g.user["id"], db_path()), created=False)
