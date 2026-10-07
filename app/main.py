"""Pages principales (accueil provisoire en attendant les recommandations)."""

from flask import Blueprint, redirect, render_template, url_for

from app.auth import profile_required

bp = Blueprint("main", __name__)


@bp.route("/")
@profile_required
def index():
    return redirect(url_for("main.accueil"))


@bp.route("/accueil")
@profile_required
def accueil():
    return render_template("main/accueil.html")
