# _CONTEXT.md — « Et maintenant, je lis quoi ? »

Dernière mise à jour : 7 octobre 2026

## Rôles
- Mathias : pilote, ne code pas. Valide les décisions, copie les prompts dans Claude Code (VSCode), rapporte les résultats.
- Claude (chat) : chef d'orchestre. Cadre, tranche, rédige les prompts, lit les rapports, corrige le cap.
- Claude Code (VSCode) : exécutant. Écrit et teste le code.

## Projet
Application Python (projet MBA) de recommandation de livres francophones. Un lecteur crée un compte, répond à un questionnaire obligatoire de 10 questions, obtient un profil, puis une page d'accueil à 3 sections. Il suit ses lectures, note les livres, et ses notes font évoluer son profil.

Documents de référence (fournis par Mathias) : périmètre initial, cahier des charges v1.0, barème détaillé du questionnaire, 3 maquettes d'interface (questionnaire, profil, accueil).

## Décisions prises
| Sujet | Décision |
|---|---|
| Périmètre | Parcours complet : comptes, questionnaire, profil, home 3 sections, suivi lecture, notes. Les exclusions du document initial sont caduques sur ces points. |
| Architecture | Monolithe Python : collecte Google Books → nettoyage → SQLite → moteur → Flask. Pas de FastAPI, pas d'embeddings, pas de LLM. |
| Interface | **Flask + Jinja2 + CSS maison** (Streamlit abandonné : incapable de reproduire les maquettes). JS vanilla minimal. Tutoiement obligatoire. |
| Auth | Pseudo + e-mail + mot de passe haché (werkzeug). Sessions Flask. Décorateur `@profile_required` sur toute route hors inscription/connexion/questionnaire. |
| Catalogue | Français uniquement, 12 catégories, description ≥ 200 car., pageCount 60-1500. Pas de fusion de catégories à l'écran (les 12 restent distinctes, libellés chaleureux). |
| Q2/Q3/Q4 | Thèmes (Q2) et ambiance (Q3) dérivés par lexiques de mots-clés sur la description. Q4 format : posée et stockée mais non calculée dans le MVP. |
| Q6 classiques | Règle MVP : 100 % si publié il y a > 25 ans, 50 % sinon. |
| Q7 langues | Posée pour le cahier des charges, sans effet (catalogue 100 % français). À documenter. |
| Moteurs | Le barème (score S) classe « À lire ensuite ». TF-IDF + cosinus sert aux livres proches depuis une fiche et à l'indice de nouveauté N (Q10). |
| Sections 2 et 3 | « Lecteurs comme toi » = même profile_label ; « Populaires cette semaine » = readings démarrées sur 7 jours. Repli explicite si données insuffisantes + script de seed pour la démo. |
| Couvertures | Miniature Google si disponible, sinon carte colorée façon maquette. |

## Barème (résumé)
- Q1 genres 24, Q2 thèmes 22, Q3 ambiance 12, Q4 format 12 (non calculé), Q5 longueur 8, Q6 période 6. Q7 langue = filtre, Q8 exclusions = filtre. Q9 bonus priorité ≤ 8, Q10 bonus découverte ≤ 8.
- P = moyenne pondérée des dimensions renseignées ET calculables. S = 0,84 × P + R + D.
- Réponse neutre = valide, retirée du dénominateur, jamais un malus. Donnée manquante = dimension ignorée.
- Confiance = poids renseignés ÷ 84 (« toutes les longueurs / périodes » exclues du dénominateur).
- Après lecture : note 4-5 → +0,05 sur genres/thèmes/ambiance du livre ; 1-2 → −0,05 ; plafond ±0,30. Exclusions manuelles priment.

## Questionnaire (codes)
- Q1 genres : les 12 catégories + « Autre » (texte, sans effet). Multi.
- Q2 thèmes (14) : famille, amour, amitie, guerre, crime, voyage, societe, science, nature, memoire, deuil, secret, initiation, art. Multi.
- Q3 ambiance (6 + varie) : sombre, tendue, legere, intimiste, epique, poetique. Multi.
- Q4 format : lineaire, rapide, choral, saga, court, introspectif, sans_pref. Multi, stocké seulement.
- Q5 longueur : court (< 250), moyen (250-450), long (> 450), toutes. Unique.
- Q6 période : nouveautes (≤ 3 ans), recents (≤ 10), classiques, toutes. Unique.
- Q7 langues : fr, en, autre, plusieurs. Multi, sans effet.
- Q8 à éviter : les 12 catégories + aucun. Multi.
- Q9 priorité : themes, nouveau, profil, temps, varier. Unique.
- Q10 découverte : proche (0×N), mixte (0,5×N), surprise (1×N), sans_pref (0,5×N). Unique.
- Chaque question a l'option neutre « Je ne sais pas / je ne souhaite pas me prononcer ».

## Schéma SQLite (data/books.db)
- books : id, google_id, title, authors (JSON), description, categories_raw (JSON), main_category, categories (JSON, 12 cat. cibles), themes (JSON), ambiance (JSON), published_year, page_count, language, isbn, thumbnail, info_link, avg_rating, ratings_count
- users : id, username, password_hash, created_at, profile_label, profile_vector (JSON) — à ajouter : email, profile_confidence
- survey_answers : user_id, question_id, answer, answered_at
- readings : id, user_id, book_id, start_date, end_date, rating, comment

## Structure du code
```
livres-reco/
  CLAUDE.md  requirements.txt  .env (clé Google, gitignoré)  .env.example
  data/raw/*.json (36+ fichiers, 12 Mo)   data/books.db
  docs/maquettes/{questionnaire,profil,accueil}.png
  src/collect.py  clean.py  tagging.py  db.py  engine.py  profile.py
  app/ (Flask : __init__.py, routes, templates/, static/)  — à créer
  tests/ (conftest.py + test_*.py)
```
Environnement : macOS, Python 3.11 via `/opt/homebrew/bin/python3.11`, `.venv`. Commandes : `.venv/bin/python -m src.collect|clean|tagging`, `.venv/bin/pytest`.

## État d'avancement
- [x] 1. Init, CLAUDE.md, db.py
- [x] 2. collect.py — clé API en place, 36 requêtes, 8 356 items bruts, 7 850 distincts
- [x] 3a. clean.py — 1 241 livres chargés (thriller 215, policier 186, dystopie 152, litt. gén. 117, fantastique 98, biographie 95, horreur 91, aventure 90, rom. historique 80, romance 62, SF 32, essai 23). Médiane 276 pages, 70 % publiés après 2010.
- [ ] 3c. Rééquilibrage SF / essai / romance (8 requêtes ajoutées) — en cours
- [ ] B. Mise à jour CLAUDE.md (Flask) — prompt donné
- [ ] 3b. tagging.py (lexiques thèmes/ambiance) — prompt donné, en cours
- [ ] 4. engine.py — TF-IDF, cosinus, livres proches, nouveauté N
- [ ] 5. profile.py — calcul du profil depuis les réponses, score S, mise à jour par les notes
- [ ] 6. Flask : auth + questionnaire + gating
- [ ] 7. Flask : accueil 3 sections + filtres + fiche livre
- [ ] 8. Flask : suivi lecture, notes, bibliothèque, page profil + seed de démo
- [ ] 9. Évaluation : jeu de test 20 livres, temps de réponse, cohérence (3/5 jugées pertinentes)

## Points ouverts
- Résultat du rééquilibrage : aucune catégorie < 60 livres ?
- Qualité des lexiques : à juger sur les 10 livres tirés au hasard du rapport tagging.
- Libellés d'écran des 12 catégories (ton maquette) à fixer au prompt 6.
- Contenu du profile_label (ex. « Suspense & tension ») : règle de nommage à définir au prompt 5 (2 catégories dominantes → libellé + description + 4 tags).

## Règles de travail
- Un prompt = un module. `/clear` au changement de module, pas pour une correction du module en cours.
- Commit git après chaque étape validée.
- Ne jamais coller la clé API dans un prompt ni dans le chat.
- Claude Code rapporte ; le chat tranche. Les propositions de Claude Code sont validées explicitement avant application.
- Réponses et prompts concis, pas de tokens inutiles.
