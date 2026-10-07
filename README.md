# Et maintenant, je lis quoi ?

Application Flask de recommandation de livres francophones (TF-IDF + similarité cosinus sur `data/books.db`).

## Lancer l'application

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python run.py   # puis http://127.0.0.1:5000
```

Tests : `.venv/bin/python -m pytest`

## Masquer un livre mal classé

```bash
.venv/bin/python -m src.hide "titre partiel ou id"   # masque et ajoute à src/hidden_books.txt
.venv/bin/python -m src.hide --list                  # livres masqués
.venv/bin/python -m src.hide --apply                 # remasque après reconstruction de la base
```

**Relance le serveur après un masquage** : une application déjà lancée garde l'index TF-IDF en mémoire et continue de proposer le livre masqué tant qu'elle n'a pas redémarré.
