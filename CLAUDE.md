# livres-reco

## Objectif
Application Streamlit de recommandation de livres francophones.
Recommandations par TF-IDF + similarité cosinus sur un catalogue local SQLite (`data/books.db`).
Comptes utilisateurs simples, questionnaire obligatoire, profil lecteur et suivi de lecture.

## Catégories (12)
littérature générale, thriller, policier, science-fiction, dystopie, fantastique, horreur, roman historique, romance, aventure, biographie, essai

## Règles
- Python 3.11.
- Code simple et explicable.
- Pas de LLM.
- Pas de framework d'auth externe.
- Pas de FastAPI.
- Pas d'embeddings.
- Réponses concises ; ne pas réécrire des fichiers non demandés.

## Conventions
- Chaque page Streamlit (`pages/`) commence par `require_profile()`.
